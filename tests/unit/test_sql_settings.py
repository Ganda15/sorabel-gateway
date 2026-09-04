from pydantic import SecretStr

from sql.settings import SqlBackend, SqlSettings


def test_postgres_settings_keep_secrets_out_of_repr() -> None:
    settings = SqlSettings(
        _env_file=None,
        backend=SqlBackend.POSTGRES,
        admin_dsn=SecretStr("postgresql://admin:secret@localhost/sorabel"),
        support_dsn=SecretStr("postgresql://support:secret@localhost/sorabel"),
        commercial_dsn=SecretStr("postgresql://commercial:secret@localhost/sorabel"),
    )

    assert settings.backend is SqlBackend.POSTGRES
    assert "secret" not in repr(settings)
    assert settings.statement_timeout_ms == 3_000
    assert settings.lock_timeout_ms == 1_000
    assert settings.max_rows == 100


def test_auto_backend_uses_postgres_when_reader_dsns_exist() -> None:
    settings = SqlSettings(
        _env_file=None,
        backend=SqlBackend.AUTO,
        support_dsn=SecretStr("postgresql://support:secret@localhost/sorabel"),
        commercial_dsn=SecretStr("postgresql://commercial:secret@localhost/sorabel"),
    )

    assert settings.effective_backend is SqlBackend.POSTGRES


def test_auto_backend_uses_compatibility_without_reader_dsns() -> None:
    settings = SqlSettings(_env_file=None, backend=SqlBackend.AUTO)

    assert settings.effective_backend is SqlBackend.SQLITE
