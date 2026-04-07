# Infrastructure Pass Likelihood Platform

The app is now on a more production-shaped Phase 3 foundation:

- Alembic migrations for schema versioning
- Stronger auth with managed sessions, cookie support, logout, and session revocation
- CI and smoke checks for migrations, tests, and container builds
- A modular frontend foundation under `app/static/js/`

## What changed

### 1. Alembic migrations

- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/20260407_0001_initial_schema.py`

Run migrations manually:

```bash
alembic upgrade head
```

### 2. Stronger auth and session flows

The app now supports:

- cookie-backed auth for the web UI
- bearer token auth for API clients
- `POST /v1/auth/logout`
- `GET /v1/auth/sessions`
- `POST /v1/auth/sessions/revoke`

Protected routes accept either:

```text
Authorization: Bearer <access_token>
```

or the managed session cookie set by login/register.

### 3. CI and production checks

Added:

- `.github/workflows/ci.yml`
- `scripts/smoke_check.py`

CI now:

- installs dependencies
- runs `alembic upgrade head`
- runs the unit suite
- runs an app startup smoke check
- builds the Docker image

### 4. Frontend foundation migration

The dashboard script is now modular:

- `app/static/js/api.js`
- `app/static/js/auth.js`
- `app/static/js/dom.js`
- `app/static/js/main.js`
- `app/static/js/state.js`
- `app/static/js/workspace.js`

That gives us a cleaner base for future UI work without introducing a JS build system yet.

## Local development

```bash
python -m venv .venv && source .venv/Scripts/activate && python -m pip install --upgrade pip && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

## Docker

```bash
docker compose up --build
```

The container entrypoint now runs migrations before starting Uvicorn.

## Config

Key environment variables:

- `APP_DATABASE_URL`
- `APP_AUTH_TOKEN_TTL_HOURS`
- `APP_ALLOW_OPEN_REGISTRATION`
- `APP_SESSION_COOKIE_NAME`
- `APP_SESSION_COOKIE_SECURE`

Example values live in `.env.example`.

## Test and smoke checks

```bash
python -m unittest test_scoring.py
python scripts/smoke_check.py
```

## Current production gaps

This is a much stronger base, but it is not yet “finished enterprise production.” The next meaningful steps would be:

- real migration chaining for future schema changes
- RBAC expansion beyond `admin` vs `analyst`
- password reset and email verification
- audit log APIs and session analytics
- background workers for imports
- a full frontend app build pipeline
- observability and alerting integration
