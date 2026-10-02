# KaushalPath dev entrypoints. POSIX shells (Linux/macOS/Git Bash/CI).
.PHONY: install dev test lint typecheck eval check seed

VENV ?= backend/.venv
# Activate helper differs by OS; CI is Linux.
ACT = . $(VENV)/bin/activate

install:
	python3 -m venv $(VENV)
	$(ACT) && pip install -r backend/requirements.txt
	npm --prefix frontend install

dev:
	$(ACT) && uvicorn app.main:app --reload --app-dir backend

lint:
	$(ACT) && ruff check backend
	npm --prefix frontend run lint

typecheck:
	$(ACT) && mypy backend/app

test:
	$(ACT) && pytest backend
	npm --prefix frontend test

check: lint test

# Eval + seed are wired in later phases (PHASE_1 data, PHASE_4 eval harness).
eval:
	@echo "Phase 4 provides eval/scripts/run_eval.py. Not wired at Phase 0."

seed:
	@echo "Phase 1 provides loaders (scripts/load_*.py). No seed data at Phase 0."
