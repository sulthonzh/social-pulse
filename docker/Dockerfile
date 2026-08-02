# ============================================================
# SocialPulse — Multi-stage Dockerfile (uv-based)
#
# Targets: base, test, lint, runtime, worker, gold-builder, api
# Usage:
#   docker compose build app
#   docker compose build api
#   docker compose --profile ci run --rm test
#   docker compose --profile ci run --rm lint
#   docker compose --profile pipeline up -d
# ============================================================

# ---- Base: Python + uv ----
FROM python:3.14-slim AS base

WORKDIR /app

# Install uv from official image (fast Rust-based package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy source + manifest together — hatchling needs src/ for editable install
COPY pyproject.toml ./
COPY src/ src/

# Install all deps + project itself (production + dev)
RUN uv sync --extra dev

# ---- Test ----
FROM base AS test

COPY tests/ tests/

RUN uv run playwright install chromium --with-deps

# Playwright's sync event loop conflicts with pytest-asyncio when run in the
# same session.  Run unit+integration first, then E2E in a separate invocation.
CMD ["sh", "-c", "uv run pytest --tb=short -v -m \"not e2e\" && uv run pytest --tb=short -v tests/e2e/"]

# ---- Lint ----
FROM base AS lint

COPY tests/ tests/

CMD ["sh", "-c", "uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/"]

# ---- ML Base (adds torch, transformers, keybert, etc.) ----
FROM base AS ml-base

RUN uv sync --all-extras --dev

# ---- Runtime (Streamlit app) ----
FROM base AS runtime

EXPOSE 8501

USER appuser
CMD ["uv", "run", "streamlit", "run", "src/presentation/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ---- Worker (AI enrichment) ----
FROM ml-base AS worker

USER appuser
CMD ["uv", "run", "python", "-m", "src.infrastructure.ai.worker"]

# ---- Crawl Worker ----
FROM base AS crawl-worker

USER appuser
CMD ["uv", "run", "python", "-m", "src.infrastructure.crawling.worker"]

# ---- Gold Builder ----
FROM base AS gold-builder

USER appuser
CMD ["uv", "run", "python", "-m", "src.infrastructure.gold.builder"]

# ---- API Server (FastAPI SSE) — reuses runtime image ----
FROM runtime AS api

EXPOSE 8000

USER appuser
CMD ["uv", "run", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
