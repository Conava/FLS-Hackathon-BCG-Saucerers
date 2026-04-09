# Longevity+ Backend

FastAPI + SQLModel + SQLAlchemy 2.0 async + Postgres 16 + pgvector.

## Prerequisites

- Python 3.12 (pinned in `.python-version`)
- [`uv`](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker (for local Postgres via `docker-compose`)

## Run locally

```bash
# 1. Install dependencies
uv sync

# 2. Start Postgres with pgvector
docker compose up -d db   # from repo root

# 3. Seed the database (after T13 is implemented)
uv run python -m app.cli.ingest --source=csv --data-dir=../data

# 4. Run the development server (after T16 is implemented)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Run tests

```bash
uv run pytest
```

## Lint and type-check

```bash
uv run ruff check app    # lint
uv run ruff format app   # format
uv run mypy app          # type-check (strict)
```

## Project layout

```
app/
  core/        # config, logging, middleware, security
  db/          # async engine, session factory
  models/      # SQLModel table entities
  schemas/     # Pydantic v2 DTOs (response_model)
  repositories/# patient-scoped data access
  adapters/    # pluggable data-source layer (CSV, future FHIR)
  services/    # vitality engine, insights, unified profile
  routers/     # FastAPI routers
  cli/         # ingest CLI
tests/
  unit/        # pure logic, no DB
  integration/ # testcontainers Postgres
```
