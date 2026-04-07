from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def main() -> None:
    smoke_dir = Path(".smoke-data")
    smoke_dir.mkdir(exist_ok=True)
    settings = Settings(
        app_name="Smoke Check",
        environment="smoke",
        version="smoke",
        data_dir=smoke_dir,
        database_url=f"sqlite:///{(smoke_dir / 'smoke.db').as_posix()}",
        allow_open_registration=True,
    )
    client = TestClient(create_app(settings))
    with client:
        response = client.get("/health/ready")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "ready", response.text
    print("smoke-ok")


if __name__ == "__main__":
    main()
