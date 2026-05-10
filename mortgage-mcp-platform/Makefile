SHELL := /bin/sh
PYTHON ?= python3.12
COMPOSE ?= docker compose

.PHONY: help venv install dev server client-test test lint compose-up compose-down db-migrate db-upgrade clean

help:
	@echo "Targets: venv install dev server test lint compose-up compose-down db-migrate db-upgrade clean"

venv:
	$(PYTHON) -m venv .venv

install: venv
	. .venv/bin/activate && pip install -U pip && pip install -r mcp-server/requirements.txt && pip install -r ../mcp-http-client/requirements.txt

dev:
	cd mcp-server && ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

server:
	cd mcp-server && uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	cd mcp-server && pytest -q

client-test:
	cd ../mcp-http-client && pytest -q

lint:
	cd mcp-server && ruff check . 2>/dev/null || true

compose-up:
	$(COMPOSE) up --build -d

compose-down:
	$(COMPOSE) down -v

db-migrate:
	cd mcp-server && alembic revision --autogenerate -m "migration"

db-upgrade:
	cd mcp-server && alembic upgrade head

clean:
	rm -rf .venv mcp-server/.pytest_cache ../mcp-http-client/.pytest_cache
