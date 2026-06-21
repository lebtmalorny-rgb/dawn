PYTHON ?= python3.11
BACKEND_VENV := backend/.venv
BACKEND_PY := $(BACKEND_VENV)/bin/python
COMPOSE ?= docker compose

.PHONY: bootstrap format lint typecheck test test-load build up down reset smoke security

bootstrap:
	$(PYTHON) -m venv $(BACKEND_VENV)
	$(BACKEND_PY) -m pip install --upgrade pip
	$(BACKEND_PY) -m pip install -e "backend[dev]"
	cd frontend && npm ci

format:
	cd backend && .venv/bin/python -m ruff format src tests
	cd frontend && npm run format

lint:
	cd backend && .venv/bin/python -m ruff check src tests
	cd frontend && npm run lint
	./scripts/secret-scan.sh

typecheck:
	cd backend && .venv/bin/python -m mypy src
	cd frontend && npm run typecheck

test:
	cd backend && .venv/bin/python -m pytest -q
	cd frontend && npm test

test-load:
	$(BACKEND_PY) scripts/e04_scale_report.py

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v

smoke:
	$(BACKEND_PY) tests/smoke.py

security:
	./scripts/secret-scan.sh
