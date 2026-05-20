FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir ".[dev]"

FROM base AS test

COPY tests/ tests/
COPY docker/ docker/

CMD ["pytest", "--tb=short", "-v"]

FROM base AS lint

CMD ["ruff", "check", "src/", "&&", "mypy", "src/"]

FROM base AS runtime

EXPOSE 8501

CMD ["streamlit", "run", "src/presentation/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

FROM base AS worker

CMD ["python", "-m", "src.infrastructure.ai.worker"]

FROM base AS gold-builder

CMD ["python", "-m", "src.infrastructure.gold.builder"]
