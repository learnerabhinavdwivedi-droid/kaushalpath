# PHASE 0 — Spec lock, traceability, scaffold

GOAL: Lock requirements from the official PS, create the repo skeleton and tooling so later phases are mechanical.

INPUTS: docs/PS_SPEC.md (official text, already pasted), docs/PS_TRACEABILITY.md (placeholder rows), scaffold tree.

TASKS (in order):
1. Read docs/PS_SPEC.md. Extract every requirement, expected outcome, dataset link and constraint into a numbered list. Quote the PS wording.
2. Rewrite docs/PS_TRACEABILITY.md: replace placeholder rows with real requirements (weight 3 explicit / 2 implied / 1 optional). Add columns Feature, Test, Status.
3. Compare the PS with docs/02_ARCHITECTURE.md. If anything in the PS is missing from the architecture, propose the minimal change in docs/ASSUMPTIONS.md. Do not silently change the stack.
4. Create backend skeleton: backend/app/main.py (FastAPI app, /health, CORS, request-id middleware), core/config.py (pydantic-settings reading .env), core/logging.py.
5. Create backend/requirements.txt (pinned versions) and backend/Dockerfile (python slim, non-root user).
6. Create frontend skeleton with Vite + React + TS + Tailwind, a placeholder home page, react-i18next configured with en and hi JSON files.
7. Create docker-compose.yml (backend, frontend), .env.example (every variable documented), Makefile with targets: install, dev, test, lint, eval, check, seed.
8. Add GitHub Actions workflow: lint + pytest + frontend build.
9. Write one backend test for /health and one frontend smoke test.

ACCEPTANCE (run and paste output): `make install && make check`; `curl localhost:8000/health` returns {"status":"ok"}; frontend builds; docs/PS_TRACEABILITY.md has zero placeholder rows.

DO NOT: add business logic, ML code or UI beyond the placeholder.
