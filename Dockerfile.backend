# syntax=docker/dockerfile:1
# Multi-stage uv-based build — Cloud Run ready (port 8080, non-root user)
# Build context: repo root (not backend/)

# ── Stage 1: dependency resolution ──────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS deps

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY backend/pyproject.toml backend/uv.lock ./

# Install production deps into /app/.venv (no dev extras)
RUN uv sync --frozen --no-dev

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 appgroup \
 && adduser --system --uid 1001 --gid 1001 --no-create-home appuser

# Copy the pre-built virtualenv from deps stage
COPY --from=deps /app/.venv /app/.venv

# Copy application source + CSV seed data
COPY backend/app/ ./app/
COPY data/ ./data/

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Drop privileges
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
