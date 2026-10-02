# PHASE 9 — Hardening, privacy, deployment, final alignment audit

GOAL: Make it demo-proof, honest and judge-proof.

TASKS:
1. Security pass: dependency audit (pip-audit/npm audit), CORS tightening, security headers, input validation, rate limits, secrets only via env, SQL injection/XSS checks, JWT expiry/rotation.
2. Privacy: consent screen text (plain Hindi/English), data minimisation review, DELETE /students/me tested, retention note in docs/PRIVACY.md (aligned to DPDP-style principles; not legal advice).
3. Reliability: structured logs, health/readiness endpoints, graceful errors, DB backup script, deterministic seeds, offline-capable demo mode (no external API needed).
4. Deployment: production docker-compose (+ optional Nginx), one-command `make demo` that migrates, seeds demo data, builds index, starts everything.
5. Performance: measure /recommend p95, frontend bundle size; fix hot spots.
6. Docs: README (what/why/architecture/run/demo), docs/ARCHITECTURE.md final, docs/EVAL_REPORT.md (from `make eval-final`, honest limitations), docs/DEMO_SCRIPT.md (4-minute walk-through with exact clicks and talking points), docs/QA_ANSWERS.md (20 likely evaluator questions with answers: data sources, accuracy definition, bias, privacy, scalability, what is demo data).
7. FINAL PS AUDIT: re-read docs/PS_SPEC.md line by line. Fill docs/PS_TRACEABILITY.md with real evidence for every row; compute the weighted score. If < 97%, list the exact gaps and implement the smallest changes to close them. Re-run `make check` and `make eval-final`.
8. Release: git tag v1.0, record a screen demo checklist, freeze the test split.

ACCEPTANCE: `make demo` works on a clean machine; `make check` green; `make eval-final` meets gates; traceability >= 0.97 with evidence links; docs complete.
DO NOT: change thresholds to pass; hide limitations; ship unmarked demo data.
