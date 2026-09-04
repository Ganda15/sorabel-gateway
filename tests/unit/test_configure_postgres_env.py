from pathlib import Path

from scripts.configure_postgres_env import (
    configure_postgres_env,
    configure_postgres_port,
    configure_reader_dsns,
)


def test_configure_postgres_env_replaces_all_password_placeholders(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SORABEL_POSTGRES_PASSWORD=REPLACE_WITH_A_LOCAL_PASSWORD\n"
        'SORABEL_SQL_ADMIN_DSN="host=localhost password=REPLACE_WITH_A_LOCAL_PASSWORD"\n',
        encoding="utf-8",
    )

    changed = configure_postgres_env(env_path, password="safe-local-secret")

    configured = env_path.read_text(encoding="utf-8")
    assert changed is True
    assert configured.count("safe-local-secret") == 2
    assert "REPLACE_WITH_A_LOCAL_PASSWORD" not in configured


def test_configure_postgres_env_is_idempotent(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("SORABEL_POSTGRES_PASSWORD=already-configured\n", encoding="utf-8")

    changed = configure_postgres_env(env_path, password="unused-secret")

    assert changed is False
    assert "already-configured" in env_path.read_text(encoding="utf-8")


def test_configure_postgres_port_preserves_the_secret(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SORABEL_POSTGRES_PORT=5433\n"
        'SORABEL_SQL_ADMIN_DSN="host=localhost port=5433 password=private-secret"\n',
        encoding="utf-8",
    )

    configure_postgres_port(env_path, port=55432)

    configured = env_path.read_text(encoding="utf-8")
    assert "SORABEL_POSTGRES_PORT=55432" in configured
    assert "port=55432" in configured
    assert "private-secret" in configured


def test_configure_reader_dsns_creates_distinct_role_connections(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SORABEL_POSTGRES_PORT=55432\n"
        "SORABEL_POSTGRES_DB=sorabel\n"
        "SORABEL_SQL_SUPPORT_DSN=\n"
        "SORABEL_SQL_COMMERCIAL_DSN=\n",
        encoding="utf-8",
    )

    changed = configure_reader_dsns(
        env_path,
        support_password="support-secret",
        commercial_password="commercial-secret",
    )

    configured = env_path.read_text(encoding="utf-8")
    assert changed is True
    assert "user=sorabel_support_login password=support-secret" in configured
    assert "user=sorabel_commercial_login password=commercial-secret" in configured
