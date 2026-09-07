from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


#: Le .env vit a la racine du depot, pas dans le dossier courant.
#:
#: Pourquoi c'est absolu : `env_file=".env"` est resolu depuis le CWD. Un
#: serveur lance depuis un autre dossier ne trouvait donc pas le fichier,
#: retombait sur backend AUTO sans DSN, donc sur SQLite, donc sur une base
#: absente -- et repondait EXECUTION_ERROR << mode de compatibilite >>. Le
#: code etait bon, la configuration introuvable. Constate le 2026-09-07.
FICHIER_ENV = Path(__file__).resolve().parents[1] / ".env"


class SqlBackend(str, Enum):
    AUTO = "auto"
    POSTGRES = "postgres"
    SQLITE = "sqlite"


class SqlGeneratorMode(str, Enum):
    DETERMINISTIC = "deterministic"
    OPENAI_COMPATIBLE = "openai_compatible"


class SqlSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SORABEL_SQL_",
        env_file=FICHIER_ENV,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend: SqlBackend = SqlBackend.AUTO
    admin_dsn: SecretStr | None = None
    support_dsn: SecretStr | None = None
    commercial_dsn: SecretStr | None = None
    database: str = "sorabel"
    sqlite_path: str = "data/sorabel.db"
    statement_timeout_ms: int = 3_000
    lock_timeout_ms: int = 1_000
    max_rows: int = 100
    generator: SqlGeneratorMode = SqlGeneratorMode.DETERMINISTIC
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    #: Un modèle distant met plusieurs secondes ; le timeout SQL, lui, reste à 3 s.
    llm_timeout_seconds: float = 60.0
    #: "auto" (déduit de l'URL), "openai" (OpenAI, Groq, Ollama…) ou "azure".
    llm_api_style: str = "auto"
    #: Azure uniquement : version d'API exigée dans l'URL.
    llm_api_version: str = "2024-10-21"

    @property
    def effective_backend(self) -> SqlBackend:
        if self.backend is not SqlBackend.AUTO:
            return self.backend
        if self.support_dsn is not None and self.commercial_dsn is not None:
            return SqlBackend.POSTGRES
        return SqlBackend.SQLITE


@lru_cache(maxsize=1)
def load_sql_settings() -> SqlSettings:
    return SqlSettings()
