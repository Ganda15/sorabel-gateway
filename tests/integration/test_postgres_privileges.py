from typing import Any

import psycopg
import pytest
from psycopg import Connection

from scripts.setup_postgres import apply_migrations, check_privileges, configure_login_roles
from sql.settings import load_sql_settings


def _admin_dsn() -> str:
    settings = load_sql_settings()
    if settings.admin_dsn is None:
        pytest.skip("SORABEL_SQL_ADMIN_DSN is not configured")
    return settings.admin_dsn.get_secret_value()


def _privilege(
    connection: Connection[Any], role: str, relation: str, privilege: str
) -> bool:
    row = connection.execute(
        "SELECT has_table_privilege(%s, %s, %s)", (role, relation, privilege)
    ).fetchone()
    assert row is not None
    return bool(row[0])


@pytest.mark.postgres
def test_profile_roles_receive_only_their_semantic_views() -> None:
    with psycopg.connect(_admin_dsn()) as connection:
        apply_migrations(connection)

        assert _privilege(
            connection, "sorabel_support", "sorabel_semantic.produits_support", "SELECT"
        )
        assert _privilege(
            connection, "sorabel_support", "sorabel_semantic.commandes_support", "SELECT"
        )
        assert not _privilege(
            connection, "sorabel_support", "sorabel_source.produits", "SELECT"
        )
        assert not _privilege(
            connection, "sorabel_support", "sorabel_semantic.ventes_commercial", "SELECT"
        )

        assert _privilege(
            connection,
            "sorabel_commercial",
            "sorabel_semantic.ventes_commercial",
            "SELECT",
        )
        assert not _privilege(
            connection, "sorabel_commercial", "sorabel_source.ventes", "SELECT"
        )
        assert not _privilege(
            connection, "sorabel_schema_reader", "sorabel_semantic.clients_commercial", "SELECT"
        )


@pytest.mark.postgres
def test_reader_roles_have_no_write_privileges() -> None:
    relations = [
        "sorabel_source.clients",
        "sorabel_source.commandes",
        "sorabel_source.produits",
        "sorabel_source.stocks",
        "sorabel_source.ventes",
    ]
    privileges = ["INSERT", "UPDATE", "DELETE", "TRUNCATE"]

    with psycopg.connect(_admin_dsn()) as connection:
        apply_migrations(connection)
        for role in ("sorabel_support", "sorabel_commercial", "sorabel_schema_reader"):
            for relation in relations:
                for privilege in privileges:
                    assert not _privilege(connection, role, relation, privilege)


@pytest.mark.postgres
def test_support_views_do_not_expose_sensitive_columns() -> None:
    with psycopg.connect(_admin_dsn()) as connection:
        apply_migrations(connection)
        rows = connection.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'sorabel_semantic'
              AND table_name LIKE '%%_support'
            """
        ).fetchall()

    visible = {(table, column) for table, column in rows}
    assert ("produits_support", "prix_achat_ht") not in visible
    assert ("produits_support", "marge_pct") not in visible
    assert all(column != "marge_ht" for _, column in visible)


@pytest.mark.postgres
def test_profile_logins_enforce_database_permissions() -> None:
    settings = load_sql_settings()
    if settings.support_dsn is None or settings.commercial_dsn is None:
        pytest.skip("profile PostgreSQL DSNs are not configured")

    with psycopg.connect(_admin_dsn()) as admin_connection:
        apply_migrations(admin_connection)
        configure_login_roles(admin_connection, settings)

    with psycopg.connect(settings.support_dsn.get_secret_value()) as support_connection:
        support_connection.execute(
            "SELECT ref, prix_vente_ht FROM sorabel_semantic.produits_support LIMIT 1"
        ).fetchone()
        read_only = support_connection.execute(
            "SELECT current_setting('transaction_read_only')"
        ).fetchone()
        assert read_only == ("on",)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            support_connection.execute("SELECT prix_achat_ht FROM sorabel_source.produits LIMIT 1")

    with psycopg.connect(settings.commercial_dsn.get_secret_value()) as commercial_connection:
        row = commercial_connection.execute(
            "SELECT marge_ht FROM sorabel_semantic.ventes_commercial LIMIT 1"
        ).fetchone()
        assert row is not None


@pytest.mark.postgres
def test_privilege_report_proves_expected_access_and_refusals() -> None:
    with psycopg.connect(_admin_dsn()) as connection:
        apply_migrations(connection)
        report = check_privileges(connection)

    assert report["passed"] is True
    assert report["checks"]
    assert all(check["passed"] for check in report["checks"])
    assert "password" not in str(report).lower()
