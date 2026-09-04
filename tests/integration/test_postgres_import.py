from pathlib import Path

import psycopg
import pytest

from scripts.setup_postgres import apply_migrations, import_sqlite, reconcile
from sql.settings import load_sql_settings


EXPECTED_COUNTS = {
    "clients": 60,
    "commandes": 340,
    "produits": 120,
    "stocks": 312,
    "ventes": 993,
}


def _admin_dsn() -> str:
    settings = load_sql_settings()
    if settings.admin_dsn is None:
        pytest.skip("SORABEL_SQL_ADMIN_DSN is not configured")
    return settings.admin_dsn.get_secret_value()


@pytest.mark.postgres
def test_sqlite_import_is_reconciled_and_idempotent() -> None:
    sqlite_path = Path("data/sorabel.db")
    with psycopg.connect(_admin_dsn()) as connection:
        apply_migrations(connection)
        import_sqlite(connection, sqlite_path)
        first_report = reconcile(connection, sqlite_path)

        import_sqlite(connection, sqlite_path)
        second_report = reconcile(connection, sqlite_path)

    assert first_report["counts"] == {
        table: {"source": expected, "target": expected, "passed": True}
        for table, expected in EXPECTED_COUNTS.items()
    }
    assert second_report["counts"] == first_report["counts"]
    assert all(check["passed"] for check in second_report["checks"])
