"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the API, auth, and persistence layers."""

    app_name: str = "Infrastructure Pass Likelihood Platform"
    environment: str = "development"
    version: str = "2.0.0"
    data_dir: Path = field(default_factory=lambda: Path("data"))
    database_url: str = "sqlite:///data/infra_scoring.db"
    default_batch_actor: str = "system-import"
    auth_token_ttl_hours: int = 24
    allow_open_registration: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("APP_DATA_DIR", "data"))
        default_sqlite_url = f"sqlite:///{(data_dir / 'infra_scoring.db').as_posix()}"
        return cls(
            app_name=os.getenv("APP_NAME", cls.app_name),
            environment=os.getenv("APP_ENV", cls.environment),
            version=os.getenv("APP_VERSION", cls.version),
            data_dir=data_dir,
            database_url=os.getenv("APP_DATABASE_URL", default_sqlite_url),
            default_batch_actor=os.getenv("APP_DEFAULT_BATCH_ACTOR", cls.default_batch_actor),
            auth_token_ttl_hours=int(os.getenv("APP_AUTH_TOKEN_TTL_HOURS", str(cls.auth_token_ttl_hours))),
            allow_open_registration=os.getenv("APP_ALLOW_OPEN_REGISTRATION", "true").lower() == "true",
        )

    @property
    def database_backend(self) -> str:
        if self.database_url.startswith("postgresql"):
            return "postgresql"
        return "sqlite"
