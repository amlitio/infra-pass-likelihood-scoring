"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the API, UI, and persistence layers."""

    app_name: str = "Infrastructure Pass Likelihood Platform"
    environment: str = "development"
    version: str = "1.1.0"
    data_dir: Path = field(default_factory=lambda: Path("data"))
    database_path: Path = field(default_factory=lambda: Path("data") / "infra_scoring.db")
    default_batch_actor: str = "system-import"

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("APP_DATA_DIR", "data"))
        database_path = Path(os.getenv("APP_DATABASE_PATH", str(data_dir / "infra_scoring.db")))
        return cls(
            app_name=os.getenv("APP_NAME", cls.app_name),
            environment=os.getenv("APP_ENV", cls.environment),
            version=os.getenv("APP_VERSION", cls.version),
            data_dir=data_dir,
            database_path=database_path,
            default_batch_actor=os.getenv("APP_DEFAULT_BATCH_ACTOR", cls.default_batch_actor),
        )
