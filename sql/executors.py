"""Bounded read-only executors for PostgreSQL and explicit SQLite compatibility."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Protocol

import psycopg
from psycopg_pool import ConnectionPool

from sql.errors import SqlErrorCode, SqlServiceError
from sql.models import QueryResult, ResolvedQuery, SemanticContext
from sql.settings import SqlBackend, SqlSettings


class SqlExecutor(Protocol):
    def execute(self, query: ResolvedQuery, context: SemanticContext) -> QueryResult: ...

    def close(self) -> None: ...


def _result(
    query: ResolvedQuery,
    context: SemanticContext,
    *,
    columns: list[str],
    rows: list[list[object]],
    backend: str,
) -> QueryResult:
    return QueryResult(
        sql=query.sql,
        parameters=query.parameters,
        columns=columns,
        rows=rows,
        backend=backend,
        dataset_version=context.dataset_version,
        data_as_of=context.data_as_of,
        semantic_schema_version=context.semantic_schema_version,
        policy_version=context.policy_version,
    )


class PostgresExecutor:
    def __init__(self, dsn: str, settings: SqlSettings) -> None:
        self.settings = settings
        self.pool = ConnectionPool(conninfo=dsn, min_size=0, max_size=4, open=False)
        self.pool.open(wait=True)

    def execute(self, query: ResolvedQuery, context: SemanticContext) -> QueryResult:
        try:
            with self.pool.connection() as connection, connection.transaction():
                connection.execute("SET TRANSACTION READ ONLY")
                connection.execute(
                    "SELECT set_config('statement_timeout', %s, true), "
                    "set_config('lock_timeout', %s, true)",
                    (
                        f"{self.settings.statement_timeout_ms}ms",
                        f"{self.settings.lock_timeout_ms}ms",
                    ),
                )
                cursor = connection.execute(query.sql, query.parameters)
                if cursor.description is None:
                    return _result(query, context, columns=[], rows=[], backend="postgres")
                columns = [description.name for description in cursor.description]
                fetched = cursor.fetchmany(query.max_rows + 1)
                if len(fetched) > query.max_rows:
                    raise SqlServiceError(
                        SqlErrorCode.QUERY_LIMIT_EXCEEDED,
                        "Le résultat dépasse la limite de lignes autorisée.",
                    )
                return _result(
                    query,
                    context,
                    columns=columns,
                    rows=[list(row) for row in fetched],
                    backend="postgres",
                )
        except SqlServiceError:
            raise
        except psycopg.Error as exc:
            raise SqlServiceError(
                SqlErrorCode.EXECUTION_ERROR,
                "La requête n’a pas pu être exécutée dans le périmètre autorisé.",
            ) from exc

    def close(self) -> None:
        self.pool.close()


class SqliteCompatibilityExecutor:
    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def _translate_sql(statement: str) -> str:
        translated = re.sub(
            r"\bsorabel_semantic\.([a-z_]+)_(?:support|commercial)\b",
            r"\1",
            statement,
            flags=re.IGNORECASE,
        )
        return re.sub(r"%\((\w+)\)s", r":\1", translated)

    def execute(self, query: ResolvedQuery, context: SemanticContext) -> QueryResult:
        uri = f"file:{self.path.resolve().as_posix()}?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True) as connection:
                connection.execute("PRAGMA query_only=ON")
                cursor = connection.execute(self._translate_sql(query.sql), query.parameters)
                columns = [description[0] for description in cursor.description or ()]
                fetched = cursor.fetchmany(query.max_rows + 1)
                if len(fetched) > query.max_rows:
                    raise SqlServiceError(
                        SqlErrorCode.QUERY_LIMIT_EXCEEDED,
                        "Le résultat dépasse la limite de lignes autorisée.",
                    )
                return _result(
                    query,
                    context,
                    columns=columns,
                    rows=[list(row) for row in fetched],
                    backend="sqlite_compatibility",
                )
        except SqlServiceError:
            raise
        except sqlite3.Error as exc:
            raise SqlServiceError(
                SqlErrorCode.EXECUTION_ERROR,
                "La requête n’a pas pu être exécutée en mode de compatibilité.",
            ) from exc

    def close(self) -> None:
        return None


def build_executor(settings: SqlSettings, profile: str) -> SqlExecutor:
    if profile == "developer":
        raise SqlServiceError(
            SqlErrorCode.NOT_AUTHORIZED,
            "Le profil Developer peut consulter le schéma mais pas exécuter de données métier.",
        )
    if profile not in {"support", "commercial"}:
        raise SqlServiceError(
            SqlErrorCode.NOT_AUTHORIZED,
            "Le profil authentifié ne permet pas cet accès.",
        )

    if settings.effective_backend is SqlBackend.POSTGRES:
        secret_dsn = settings.support_dsn if profile == "support" else settings.commercial_dsn
        if secret_dsn is None or not secret_dsn.get_secret_value().strip():
            raise SqlServiceError(
                SqlErrorCode.EXECUTION_ERROR,
                "La connexion PostgreSQL du profil n’est pas configurée.",
            )
        return PostgresExecutor(secret_dsn.get_secret_value(), settings)
    return SqliteCompatibilityExecutor(Path(settings.sqlite_path))
