# Infrastructure Pass Likelihood Platform

This project is now structured as an enterprise-ready scoring service for infrastructure proposal evaluation. It keeps the original CLI workflow, while adding a production-oriented application package, HTTP API, health probes, configuration, and batch scoring support.

## What is included

- Reusable domain and service layers in `app/`
- Backward-compatible CLI entry point in `scoring.py`
- FastAPI service with OpenAPI docs
- Single-project and batch scoring endpoints
- Liveness and readiness endpoints for deployment environments
- Expanded automated tests for CLI and API behavior

## Architecture

- `app/domain.py`: validated scoring inputs and domain constants
- `app/service.py`: scoring, interpretation, and utilization logic
- `app/schemas.py`: request and response contracts
- `app/main.py`: FastAPI app and endpoints
- `app/config.py`: environment-driven runtime settings
- `app/cli.py`: command-line experience

## Install

```bash
python -m pip install -r requirements.txt
```

## Run the CLI

```bash
python scoring.py --demo
```

```bash
python scoring.py --procedural-stage 20 --sponsor-strength 9 --funding-clarity 12 --route-specificity 10 --need-case 10 --row-tractability 7 --local-plan-alignment 6 --opposition-drag 2 --land-monetization-fit 14
```

```bash
python scoring.py --input-json project.json
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## API endpoints

### `POST /v1/score`

Scores a single project.

Example payload:

```json
{
  "project_id": "P-100",
  "project_name": "North Corridor Expansion",
  "procedural_stage": 20,
  "sponsor_strength": 8,
  "funding_clarity": 10,
  "route_specificity": 8,
  "need_case": 10,
  "row_tractability": 7,
  "local_plan_alignment": 6,
  "opposition_drag": 2,
  "land_monetization_fit": 12
}
```

### `POST /v1/score/batch`

Scores up to 500 projects in one request and returns summary statistics.

### `GET /health/live`

Basic liveness probe.

### `GET /health/ready`

Readiness probe with environment and version details.

### `GET /v1/metadata`

Service metadata and capabilities.

## Configuration

The service reads these optional environment variables:

- `APP_NAME`
- `APP_ENV`
- `APP_VERSION`

## Tests

```bash
python -m unittest test_scoring.py
```
