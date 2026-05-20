.PHONY: help up down restart logs ps test lint shell clean

COMPOSE = docker compose -f docker/docker-compose.yml

help:
	@echo "SocialPulse — Docker Commands"
	@echo ""
	@echo "  make up          Start app"
	@echo "  make up-pipeline Start with worker + gold-builder"
	@echo "  make down        Stop all services"
	@echo "  make restart     Restart app"
	@echo "  make logs        Tail logs from all services"
	@echo "  make ps          Show running services"
	@echo "  make test        Run pytest in Docker"
	@echo "  make lint        Run ruff + mypy in Docker"
	@echo "  make shell       Bash shell in app container"
	@echo "  make clean       Remove volumes and stop services"

up:
	$(COMPOSE) up -d

up-pipeline:
	$(COMPOSE) --profile pipeline up -d

down:
	$(COMPOSE) --profile ci --profile pipeline down

restart:
	$(COMPOSE) restart app

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

test:
	$(COMPOSE) run --rm test

lint:
	$(COMPOSE) run --rm lint

shell:
	$(COMPOSE) exec app /bin/bash

clean:
	$(COMPOSE) --profile ci --profile pipeline down -v
