"""Create and reconcile the private Sorabel PostgreSQL source layer."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg import Connection, sql
from psycopg.conninfo import conninfo_to_dict

from sql.settings import SqlSettings, load_sql_settings


ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "sql" / "migrations"
DEFAULT_EVIDENCE = ROOT / "docs" / "livrable" / "evidence" / "postgresql-reconciliation.json"
DEFAULT_PRIVILEGE_EVIDENCE = (
    ROOT / "docs" / "livrable" / "evidence" / "postgresql-privileges.json"
)

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "produits": (
        "ref",
        "nom",
        "categorie",
        "fabricant",
        "unite",
        "prix_vente_ht",
        "prix_achat_ht",
        "marge_pct",
        "actif",
    ),
    "clients": ("id", "raison_sociale", "segment", "ville", "email"),
    "commandes": ("id", "client_id", "date_commande", "statut", "montant_ht"),
    "stocks": ("id", "ref", "entrepot", "quantite", "seuil_reappro"),
    "ventes": (
        "id",
        "commande_id",
        "ref",
        "quantite",
        "prix_unitaire_ht",
        "remise_pct",
        "marge_ht",
    ),
}

PRIMARY_KEYS = {
    "produits": "ref",
    "clients": "id",
    "commandes": "id",
    "stocks": "id",
    "ventes": "id",
}

EXPECTED_TYPES: dict[str, dict[str, str]] = {
    "produits": {"ref": "text", "prix_vente_ht": "numeric", "actif": "boolean"},
    "clients": {"id": "text", "email": "text"},
    "commandes": {"id": "text", "date_commande": "date", "montant_ht": "numeric"},
    "stocks": {"id": "bigint", "quantite": "integer"},
    "ventes": {"id": "bigint", "marge_ht": "numeric"},
}


def _open_sqlite_read_only(sqlite_path: Path) -> sqlite3.Connection:
    resolved = sqlite_path.resolve().as_posix()
    connection = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def apply_migrations(connection: Connection[Any]) -> None:
    """Apply every SQL migration in filename order inside the caller transaction."""
    for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        connection.execute(migration_path.read_text(encoding="utf-8"))


def configure_login_roles(connection: Connection[Any], settings: SqlSettings) -> None:
    """Apply local passwords to the predefined profile login roles without logging them."""
    role_dsns = {
        "sorabel_support_login": settings.support_dsn,
        "sorabel_commercial_login": settings.commercial_dsn,
    }
    for expected_role, secret_dsn in role_dsns.items():
        if secret_dsn is None or not secret_dsn.get_secret_value().strip():
            continue
        parameters = conninfo_to_dict(secret_dsn.get_secret_value())
        role = parameters.get("user")
        password = parameters.get("password")
        if role != expected_role or not password:
            raise ValueError(f"DSN must configure the expected PostgreSQL role: {expected_role}")
        statement = sql.SQL("ALTER ROLE {} PASSWORD {}").format(
            sql.Identifier(role), sql.Literal(password)
        )
        connection.execute(statement)


def _normalized_rows(table: str, rows: list[sqlite3.Row]) -> list[tuple[Any, ...]]:
    columns = TABLE_COLUMNS[table]
    normalized: list[tuple[Any, ...]] = []
    for row in rows:
        values: list[Any] = [row[column] for column in columns]
        if table == "produits":
            values[columns.index("actif")] = bool(values[columns.index("actif")])
        if table == "commandes":
            date_index = columns.index("date_commande")
            values[date_index] = date.fromisoformat(values[date_index])
        normalized.append(tuple(values))
    return normalized


def _upsert_statement(table: str) -> sql.Composed:
    columns = TABLE_COLUMNS[table]
    primary_key = PRIMARY_KEYS[table]
    assignments = [
        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column))
        for column in columns
        if column != primary_key
    ]
    return sql.SQL(
        "INSERT INTO sorabel_source.{} ({}) VALUES ({}) "
        "ON CONFLICT ({}) DO UPDATE SET {}"
    ).format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        sql.Identifier(primary_key),
        sql.SQL(", ").join(assignments),
    )


def import_sqlite(connection: Connection[Any], sqlite_path: Path) -> dict[str, int]:
    """Upsert the five received SQLite tables into the private PostgreSQL schema."""
    imported: dict[str, int] = {}
    with _open_sqlite_read_only(sqlite_path) as source, connection.cursor() as cursor:
        for table in TABLE_COLUMNS:
            rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
            normalized = _normalized_rows(table, rows)
            if normalized:
                cursor.executemany(_upsert_statement(table), normalized)
            imported[table] = len(normalized)
    return imported


def _source_counts(sqlite_path: Path) -> dict[str, int]:
    with _open_sqlite_read_only(sqlite_path) as source:
        return {
            table: int(source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in TABLE_COLUMNS
        }


def _required_count(row: tuple[Any, ...] | None, *, check: str) -> int:
    if row is None:
        raise RuntimeError(f"PostgreSQL returned no row for count check: {check}")
    return int(row[0])


def _target_counts(connection: Connection[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in TABLE_COLUMNS:
        query = sql.SQL("SELECT COUNT(*) FROM sorabel_source.{}").format(sql.Identifier(table))
        counts[table] = _required_count(connection.execute(query).fetchone(), check=table)
    return counts


def _append_integrity_checks(connection: Connection[Any], checks: list[dict[str, Any]]) -> None:
    for table, columns in TABLE_COLUMNS.items():
        null_predicates = sql.SQL(" OR ").join(
            sql.SQL("{} IS NULL").format(sql.Identifier(column)) for column in columns
        )
        query = sql.SQL("SELECT COUNT(*) FROM sorabel_source.{} WHERE {}").format(
            sql.Identifier(table), null_predicates
        )
        null_count = _required_count(
            connection.execute(query).fetchone(), check=f"{table}.required_values"
        )
        checks.append(
            {"name": f"{table}.required_values", "invalid_rows": null_count, "passed": null_count == 0}
        )

        primary_key = PRIMARY_KEYS[table]
        duplicate_query = sql.SQL(
            "SELECT COUNT(*) FROM (SELECT {} FROM sorabel_source.{} "
            "GROUP BY {} HAVING COUNT(*) > 1) duplicates"
        ).format(
            sql.Identifier(primary_key),
            sql.Identifier(table),
            sql.Identifier(primary_key),
        )
        duplicate_count = _required_count(
            connection.execute(duplicate_query).fetchone(), check=f"{table}.primary_key"
        )
        checks.append(
            {"name": f"{table}.primary_key", "duplicates": duplicate_count, "passed": duplicate_count == 0}
        )

    relation_queries = {
        "stocks.product_reference": """
            SELECT COUNT(*) FROM sorabel_source.stocks child
            LEFT JOIN sorabel_source.produits parent ON parent.ref = child.ref
            WHERE parent.ref IS NULL
        """,
        "commandes.client_reference": """
            SELECT COUNT(*) FROM sorabel_source.commandes child
            LEFT JOIN sorabel_source.clients parent ON parent.id = child.client_id
            WHERE parent.id IS NULL
        """,
        "ventes.order_reference": """
            SELECT COUNT(*) FROM sorabel_source.ventes child
            LEFT JOIN sorabel_source.commandes parent ON parent.id = child.commande_id
            WHERE parent.id IS NULL
        """,
        "ventes.product_reference": """
            SELECT COUNT(*) FROM sorabel_source.ventes child
            LEFT JOIN sorabel_source.produits parent ON parent.ref = child.ref
            WHERE parent.ref IS NULL
        """,
    }
    for name, statement in relation_queries.items():
        orphan_count = _required_count(connection.execute(statement).fetchone(), check=name)
        checks.append(
            {"name": name, "orphans": orphan_count, "passed": orphan_count == 0}
        )


def _append_type_checks(connection: Connection[Any], checks: list[dict[str, Any]]) -> None:
    rows = connection.execute(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'sorabel_source'
        """
    ).fetchall()
    actual = {(table, column): data_type for table, column, data_type in rows}
    for table, columns in EXPECTED_TYPES.items():
        for column, expected in columns.items():
            observed = actual.get((table, column))
            checks.append(
                {
                    "name": f"{table}.{column}.type",
                    "expected": expected,
                    "actual": observed,
                    "passed": observed == expected,
                }
            )


def reconcile(connection: Connection[Any], sqlite_path: Path) -> dict[str, Any]:
    """Compare source and target counts, types, keys, required data and relations."""
    source_counts = _source_counts(sqlite_path)
    target_counts = _target_counts(connection)
    counts = {
        table: {
            "source": source_counts[table],
            "target": target_counts[table],
            "passed": source_counts[table] == target_counts[table],
        }
        for table in TABLE_COLUMNS
    }
    checks: list[dict[str, Any]] = [
        {"name": "all_table_counts", "passed": all(item["passed"] for item in counts.values())}
    ]
    _append_integrity_checks(connection, checks)
    _append_type_checks(connection, checks)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "data/sorabel.db",
        "target": "PostgreSQL:sorabel_source",
        "counts": counts,
        "checks": checks,
        "passed": all(item["passed"] for item in counts.values())
        and all(check["passed"] for check in checks),
    }


def _has_table_privilege(
    connection: Connection[Any], role: str, relation: str, privilege: str
) -> bool:
    row = connection.execute(
        "SELECT has_table_privilege(%s, %s, %s)", (role, relation, privilege)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"No result while checking {role} {privilege} on {relation}")
    return bool(row[0])


def _has_column_privilege(
    connection: Connection[Any], role: str, relation: str, column: str
) -> bool:
    row = connection.execute(
        "SELECT has_column_privilege(%s, %s, %s, 'SELECT')",
        (role, relation, column),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"No result while checking {role} SELECT on {relation}.{column}")
    return bool(row[0])


def check_privileges(connection: Connection[Any]) -> dict[str, Any]:
    """Return sanitized RBAC evidence from PostgreSQL's privilege functions."""
    checks: list[dict[str, Any]] = []
    expected_table_privileges = [
        ("sorabel_support", "sorabel_semantic.produits_support", "SELECT", True),
        ("sorabel_support", "sorabel_semantic.stocks_support", "SELECT", True),
        ("sorabel_support", "sorabel_semantic.commandes_support", "SELECT", True),
        ("sorabel_support", "sorabel_semantic.ventes_commercial", "SELECT", False),
        ("sorabel_support", "sorabel_source.produits", "SELECT", False),
        ("sorabel_commercial", "sorabel_semantic.ventes_commercial", "SELECT", True),
        ("sorabel_commercial", "sorabel_source.ventes", "SELECT", False),
        ("sorabel_schema_reader", "sorabel_semantic.clients_commercial", "SELECT", False),
    ]
    for role, relation, privilege, expected in expected_table_privileges:
        actual = _has_table_privilege(connection, role, relation, privilege)
        checks.append(
            {
                "kind": "table_privilege",
                "role": role,
                "object": relation,
                "privilege": privilege,
                "expected": expected,
                "actual": actual,
                "passed": actual is expected,
            }
        )

    for role in ("sorabel_support", "sorabel_commercial", "sorabel_schema_reader"):
        for relation in (
            "sorabel_source.clients",
            "sorabel_source.commandes",
            "sorabel_source.produits",
            "sorabel_source.stocks",
            "sorabel_source.ventes",
        ):
            for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                actual = _has_table_privilege(connection, role, relation, privilege)
                checks.append(
                    {
                        "kind": "table_privilege",
                        "role": role,
                        "object": relation,
                        "privilege": privilege,
                        "expected": False,
                        "actual": actual,
                        "passed": actual is False,
                    }
                )

    expected_column_privileges = [
        (
            "sorabel_support",
            "sorabel_semantic.produits_support",
            "prix_vente_ht",
            True,
        ),
        ("sorabel_support", "sorabel_source.produits", "prix_achat_ht", False),
        ("sorabel_support", "sorabel_source.produits", "marge_pct", False),
        ("sorabel_support", "sorabel_source.ventes", "marge_ht", False),
    ]
    for role, relation, column, expected in expected_column_privileges:
        actual = _has_column_privilege(connection, role, relation, column)
        checks.append(
            {
                "kind": "column_privilege",
                "role": role,
                "object": f"{relation}.{column}",
                "privilege": "SELECT",
                "expected": expected,
                "actual": actual,
                "passed": actual is expected,
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": "PostgreSQL:sorabel_semantic",
        "policy_version": "policy-v1",
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
    }


def _write_evidence(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--import", dest="do_import", action="store_true")
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--check-privileges", action="store_true")
    parser.add_argument("--sqlite", type=Path, default=ROOT / "data" / "sorabel.db")
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument(
        "--privilege-evidence", type=Path, default=DEFAULT_PRIVILEGE_EVIDENCE
    )
    args = parser.parse_args()

    if not (args.migrate or args.do_import or args.reconcile or args.check_privileges):
        parser.error(
            "select at least one of --migrate, --import, --reconcile or --check-privileges"
        )

    settings = load_sql_settings()
    if settings.admin_dsn is None:
        parser.error("SORABEL_SQL_ADMIN_DSN is required")

    exit_code = 0
    with psycopg.connect(settings.admin_dsn.get_secret_value()) as connection:
        if args.migrate:
            apply_migrations(connection)
            configure_login_roles(connection, settings)
        if args.do_import:
            import_sqlite(connection, args.sqlite)
        if args.reconcile:
            report = reconcile(connection, args.sqlite)
            _write_evidence(report, args.evidence)
            print(json.dumps({"passed": report["passed"], "counts": report["counts"]}, indent=2))
            if not report["passed"]:
                exit_code = 1
        if args.check_privileges:
            privilege_report = check_privileges(connection)
            _write_evidence(privilege_report, args.privilege_evidence)
            print(
                json.dumps(
                    {
                        "privileges_passed": privilege_report["passed"],
                        "checks": len(privilege_report["checks"]),
                    },
                    indent=2,
                )
            )
            if not privilege_report["passed"]:
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
