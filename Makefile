.PHONY: help setup build up up-pipeline down restart logs ps test test-local lint lint-local fmt shell clean

COMPOSE = docker-compose -f docker/docker-compose.yml

help:
	@echo "SocialPulse — Development Commands"
	@echo ""
	@echo "  Setup:"
	@echo "    make setup        First-time setup (.env, deps, browsers)"
	@echo ""
	@echo "  Docker:"
	@echo "    make build        Build all Docker images"
	@echo "    make up           Start app + API"
	@echo "    make up-pipeline  Start with workers + gold-builder"
	@echo "    make down         Stop all services"
	@echo "    make restart      Restart app"
	@echo "    make logs         Tail logs from all services"
	@echo "    make ps           Show running services"
	@echo "    make shell        Bash shell in app container"
	@echo "    make clean        Remove volumes and stop services"
	@echo ""
	@echo "  Testing & Quality (Docker):"
	@echo "    make test         Run pytest in Docker"
	@echo "    make lint         Run ruff + mypy in Docker"
	@echo ""
	@echo "  Testing & Quality (local, requires uv):"
	@echo "    make test-local   Run pytest locally"
	@echo "    make lint-local   Run ruff + mypy locally"
	@echo "    make fmt          Auto-format with ruff"

# ---- Setup ----

setup:
	cp -n .env.example .env 2>/dev/null || true
	uv sync --all-extras --dev
	@echo ""
	@echo "Setup complete. Run 'make up' to start."

# ---- Docker ----

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

up-pipeline:
	$(COMPOSE) --profile pipeline up -d

down:
	$(COMPOSE) --profile ci --profile pipeline --profile dbt-docs down

restart:
	$(COMPOSE) restart app

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

shell:
	$(COMPOSE) exec app /bin/bash

clean:
	$(COMPOSE) --profile ci --profile pipeline --profile dbt-docs down -v

# ---- Testing & Quality (Docker) ----

test:
	$(COMPOSE) --profile ci run --rm test uv run pytest tests/ -x -q --tb=short --override-ini="addopts=" --ignore=tests/e2e

lint:
	$(COMPOSE) --profile ci run --rm lint

# ---- Testing & Quality (local) ----

test-local:
	uv run pytest tests/ -x -q --tb=short -m "not e2e" --override-ini="addopts="

lint-local:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/
	uv run mypy src/

fmt:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/
