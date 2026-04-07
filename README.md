# Infrastructure Pass Likelihood Platform

Phase 1 turns the original scoring utility into a working product surface: an API, a browser-based portfolio dashboard, persistent project records, score history, and CSV batch intake. The original CLI is still supported for quick local scoring.

## Phase 1 buildout

- Persistent SQLite-backed project registry and score-run audit trail
- Portfolio dashboard at `/` for operators and analysts
- Project create, update, list, detail, and rescore workflows
- CSV import endpoint for batch portfolio creation
- Stateless scoring endpoints preserved for simple integrations
- Liveness, readiness, and metadata endpoints for deployment environments

## Architecture

- `app/domain.py`: validated scoring inputs and score boundaries
- `app/service.py`: scoring, interpretation, and normalization logic
- `app/repository.py`: SQLite persistence for projects, score history, and imports
- `app/schemas.py`: API contracts and persistent record models
- `app/main.py`: app factory, routes, and startup initialization
- `app/static/`: zero-build dashboard UI
- `app/cli.py`: backward-compatible CLI entry point

## One-command Git Bash setup

API server:

```bash
python -m venv .venv && source .venv/Scripts/activate && python -m pip install --upgrade pip && pip install -r requirements.txt && uvicorn app.main:app --reload
```

CLI demo:

```bash
python -m venv .venv && source .venv/Scripts/activate && python -m pip install --upgrade pip && pip install -r requirements.txt && python scoring.py --demo
```

## Run surfaces manually

Install:

```bash
python -m pip install -r requirements.txt
```

CLI:

```bash
python scoring.py --demo
python scoring.py --input-json project.json
```

API and dashboard:

```bash
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## API overview

### Stateless scoring

- `POST /v1/score`
- `POST /v1/score/batch`

### Persistent project workflows

- `GET /v1/portfolio`
- `GET /v1/projects`
- `POST /v1/projects`
- `GET /v1/projects/{project_pk}`
- `PUT /v1/projects/{project_pk}`
- `POST /v1/projects/{project_pk}/rescore`

### Batch intake

- `POST /v1/imports/csv`

Expected CSV headers:

```text
project_id,project_name,sponsor_organization,sector,region,notes,procedural_stage,sponsor_strength,funding_clarity,route_specificity,need_case,row_tractability,local_plan_alignment,opposition_drag,land_monetization_fit
```

### Ops endpoints

- `GET /health/live`
- `GET /health/ready`
- `GET /v1/metadata`

## Configuration

Optional environment variables:

- `APP_NAME`
- `APP_ENV`
- `APP_VERSION`
- `APP_DATA_DIR`
- `APP_DATABASE_PATH`
- `APP_DEFAULT_BATCH_ACTOR`

## Phase 2 candidate backlog

- Organization and user accounts with role-based access
- PostgreSQL migration path for multi-user deployment
- Saved filters, search, and portfolio segmentation
- Rich import/export workflows for Excel and BI tooling
- Model versioning and configurable weights
- CI, Docker, and deployment manifests

## Tests

```bash
python -m unittest test_scoring.py
```
