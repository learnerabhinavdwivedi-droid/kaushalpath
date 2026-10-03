# KaushalPath dev entrypoints. POSIX shells (Linux/macOS/Git Bash/CI).
# Windows: run the same commands inside Git Bash / WSL, or invoke the underlying
# scripts directly (see README "Run locally").
.PHONY: install dev test lint typecheck eval eval-final check seed data-report \
        migrate demo backup security ps-audit

VENV ?= backend/.venv
# Activate helper differs by OS; CI is Linux.
ACT = . $(VENV)/bin/activate

install:
	python3 -m venv $(VENV)
	$(ACT) && pip install -r backend/requirements.txt
	npm --prefix frontend install

dev:
	$(ACT) && cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Lint the backend package AND the top-level scripts (loaders/demo/backup)
# under the same ruleset, so nothing ships un-linted.
lint:
	$(ACT) && ruff check backend
	$(ACT) && ruff check scripts --config backend/pyproject.toml
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

# Build schema (if needed) + load demo/merged reference data + retrieval index.
# Idempotent, and OFFLINE-safe: onet/esco loaders are no-ops without raw/ and
# the recommender falls back to the transparent scorer when the embedding stack
# is absent (see docs/ASSUMPTIONS.md A5).
seed:
	$(ACT) && python scripts/seed_all.py

data-report:
	$(ACT) && python scripts/data_report.py

# Production migrations (dev seed uses create_all for convenience).
migrate:
	$(ACT) && cd backend && alembic upgrade head

# Consistent SQLite snapshot -> backups/.
backup:
	$(ACT) && python scripts/backup_db.py

# Dependency vulnerability audit (informational; findings recorded in docs/SECURITY.md).
security:
	$(ACT) && (python -m pip_audit -r backend/requirements.txt || echo "pip-audit: advisories found or tool missing (see docs/SECURITY.md)")
	npm --prefix frontend audit --audit-level=high || true

# Final PS alignment audit: weighted score from docs/PS_TRACEABILITY.md.
ps-audit:
	$(ACT) && python scripts/ps_audit.py

# One-command clean-machine demo: migrate + seed (+ index), then serve the API.
# Frontend: `npm --prefix frontend run dev` in a second shell (or `docker
# compose up` for the whole stack). No external API/model download is needed.
demo: migrate seed
	@echo "KaushalPath demo ready: DB migrated + seeded. Serving API on :8000."
	@echo "In another shell: npm --prefix frontend run dev  -> http://localhost:5173"
	$(ACT) && cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
