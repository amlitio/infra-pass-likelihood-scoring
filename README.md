# Infrastructure Pass Likelihood Platform

Phase 2 turns the scoring platform into a multi-organization application with authentication, PostgreSQL support, and deployment packaging. The original CLI and stateless scoring endpoints still work, but the persistent workflows are now protected by bearer-token auth and scoped to an organization.

## What Phase 2 adds

- Organization registration and user login
- Token-based auth for persistent workflows
- Admin-managed teammate creation
- Organization-scoped projects, imports, and score history
- Database abstraction for SQLite and PostgreSQL
- Docker and Docker Compose packaging for local or hosted deployment
- Updated dashboard with register, login, and org-aware operations

## Architecture

- `app/auth.py`: password hashing, token generation, expiry
- `app/models.py`: SQLAlchemy models for organizations, users, projects, score runs, and imports
- `app/repository.py`: shared persistence layer for SQLite and PostgreSQL
- `app/main.py`: auth, organization, portfolio, and scoring endpoints
- `app/static/`: zero-build dashboard with auth-aware workflow
- `Dockerfile`: production app container
- `docker-compose.yml`: app + PostgreSQL local stack

## Local run

Git Bash one-liner:

```bash
python -m venv .venv && source .venv/Scripts/activate && python -m pip install --upgrade pip && pip install -r requirements.txt && uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

## Docker run

```bash
docker compose up --build
```

This starts:

- API + dashboard on `http://127.0.0.1:8000`
- PostgreSQL on `localhost:5432`

## Configuration

Use `.env.example` as the starting point.

- `APP_NAME`
- `APP_ENV`
- `APP_VERSION`
- `APP_DATA_DIR`
- `APP_DATABASE_URL`
- `APP_AUTH_TOKEN_TTL_HOURS`
- `APP_ALLOW_OPEN_REGISTRATION`

### Database examples

SQLite:

```text
sqlite:///data/infra_scoring.db
```

PostgreSQL:

```text
postgresql+psycopg://postgres:postgres@db:5432/infra_scoring
```

## API overview

### Public endpoints

- `GET /health/live`
- `GET /health/ready`
- `GET /v1/metadata`
- `POST /v1/score`
- `POST /v1/score/batch`

### Auth endpoints

- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `GET /v1/auth/me`

### Organization endpoints

- `GET /v1/organizations/me`
- `GET /v1/organizations/me/users`
- `POST /v1/organizations/me/users`

### Protected portfolio endpoints

- `GET /v1/portfolio`
- `GET /v1/projects`
- `POST /v1/projects`
- `GET /v1/projects/{project_pk}`
- `PUT /v1/projects/{project_pk}`
- `POST /v1/projects/{project_pk}/rescore`
- `POST /v1/imports/csv`

All protected routes require:

```text
Authorization: Bearer <access_token>
```

## Register flow example

```json
{
  "organization_name": "Atlas Infrastructure",
  "organization_slug": "atlas-infrastructure",
  "email": "admin@atlas.example",
  "password": "supersecure",
  "full_name": "Avery Analyst"
}
```

## Tests

```bash
python -m unittest test_scoring.py
```

## Next logical Phase 3

- SSO and external identity providers
- Audit log browsing and revocable sessions
- Background jobs and async imports
- Search, saved views, and reporting exports
- Managed migrations and rollout automation
