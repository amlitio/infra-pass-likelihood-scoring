"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the API and CLI surfaces."""

    app_name: str = "Infrastructure Pass Likelihood Platform"
    environment: str = "development"
    version: str = "1.0.0"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", cls.app_name),
            environment=os.getenv("APP_ENV", cls.environment),
            version=os.getenv("APP_VERSION", cls.version),
        )
