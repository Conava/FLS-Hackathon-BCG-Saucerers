.PHONY: up down seed test fmt lint openapi help

## up: start db and backend containers in detached mode
up:
	docker compose up -d db backend

## down: stop and remove containers
down:
	docker compose down

## seed: ingest CSV data into the database (local: cd backend && uv run python -m app.cli.ingest --source=csv --data-dir=../data)
seed:
	docker compose exec -T backend python -m app.cli.ingest --source=csv --data-dir=/app/data

## test: run the pytest test suite
test:
	cd backend && uv run pytest

## fmt: format backend source with ruff
fmt:
	cd backend && uv run ruff format

## lint: check backend source with ruff and mypy
lint:
	cd backend && uv run ruff check app
	cd backend && uv run mypy app

## openapi: regenerate backend/openapi.json from the live FastAPI schema
openapi:
	cd backend && uv run python -m app.cli.export_openapi

## help: show this help message
help:
	@grep -E '^## ' Makefile | sed 's/^## //'
