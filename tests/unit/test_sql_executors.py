import sqlite3
from pathlib import Path

import pytest

from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode, SqlServiceError
from sql.executors import SqliteCompatibilityExecutor
from sql.models import ResolvedQuery


def test_sqlite_compatibility_executor_is_read_only(tmp_path: Path) -> None:
    database = tmp_path / "compatibility.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE commandes(id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO commandes VALUES ('CMD-1')")

    context = SemanticCatalog.load(Path("sql/semantic_catalog.json")).for_profile("support")
    executor = SqliteCompatibilityExecutor(database)
    result = executor.execute(
        ResolvedQuery(
            sql="SELECT id FROM sorabel_semantic.commandes_support LIMIT 10",
            views=("commandes_support",),
            columns=("id",),
            max_rows=10,
        ),
        context,
    )

    assert result.rows == [["CMD-1"]]
    assert result.backend == "sqlite_compatibility"

    with pytest.raises(SqlServiceError) as captured:
        executor.execute(
            ResolvedQuery(
                sql="DELETE FROM sorabel_semantic.commandes_support",
                views=("commandes_support",),
                columns=(),
                max_rows=10,
            ),
            context,
        )
    assert captured.value.code is SqlErrorCode.EXECUTION_ERROR
