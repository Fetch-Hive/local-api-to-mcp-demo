# Local Issue Tracker
#   make install   create .venv and install the app plus pytest
#   make dev       serve http://127.0.0.1:8000
#   make test      run the test suite
#   make reset     delete data/issues.db so the next start loads the seed issues

PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: install dev test reset

install:
	$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else "Python 3.12 or newer is required")'
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[dev]"

dev:
	@test -x $(BIN)/uvicorn || { echo "Run make install first."; exit 1; }
	$(BIN)/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app

test:
	@test -x $(BIN)/pytest || { echo "Run make install first."; exit 1; }
	$(BIN)/pytest

reset:
	rm -f data/issues.db
	@echo "Removed data/issues.db. Stop the app first if it is running, then start it again to load the seed issues."
