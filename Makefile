# KaushalPath dev entrypoints. POSIX shells (Linux/macOS/Git Bash/CI).
.PHONY: install dev test lint typecheck eval check seed data-report

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

# Eval wired in PHASE_4. Seed (PHASE_1 data layer) runs the loaders.
eval:
	$(ACT) && python eval/scripts/run_eval.py val

eval-final:
	$(ACT) && python eval/scripts/run_eval.py test

# Build schema (if needed) + load demo/merged reference data. Idempotent.
seed:
	$(ACT) && python scripts/seed_all.py

data-report:
	$(ACT) && python scripts/data_report.py
