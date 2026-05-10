PYTHON ?= python3.12
VENV ?= .venv

.PHONY: help venv install test clean health

help:
	@echo "venv install test health — MCP HTTP client (calls mortgage API)"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(VENV)/Scripts/pip install -U pip
	$(VENV)/Scripts/pip install -r requirements.txt

test:
	$(VENV)/Scripts/pytest -q

health:
	$(VENV)/Scripts/python -m mcp_client.cli health

clean:
	rm -rf $(VENV) .pytest_cache
