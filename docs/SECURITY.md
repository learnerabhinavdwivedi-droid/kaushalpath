# KaushalPath — Security Review & Hardening (Phase 9)

Owner-facing summary of the security pass for SIH 2026 PSID 26241. Written to be
read by an evaluator **and** re-verifiable with the commands at the bottom.
Not a substitute for a professional penetration test; scoped to a hackathon
demo deployment.

## 1. Code-level review (what we checked and what we changed)

| Area | Finding | Action |
|---|---|---|
| **SQL injection** | All queries use the SQLAlchemy 2 expression language (`select()`, `session.get`, `filter_by`); no string SQL interpolation anywhere in `app/` or `scripts/`. | Verified — nothing to fix. |
| **XSS** | No `dangerouslySetInnerHTML` / `innerHTML` in the SPA; React escapes by default; user/LLM text renders as text nodes. | Verified — nothing to fix. |
| **Error info-leak** | `recommend.py` had `except Exception: HTTPException(str(e))` — leaked internal exception text to clients. | Removed; unexpected errors now hit the global handler (`app/core/errors.py`) which logs the trace server-side and returns a generic, `request_id`-tagged 500. |
| **Security headers** | API responses had none. | Added `SecurityHeadersMiddleware` (`app/core/middleware.py`): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cache-Control: no-store`. Nginx adds CSP + HSTS for served HTML (`infra/nginx.conf`). |
| **CORS** | Was `allow_origins=*` style with credentials on. | Tightened to explicit methods/headers in `main.py`; prod guard rejects `*`. |
| **Secrets / misconfig** | Classic demo-to-prod foot-guns. | `config.py::_prod_hardening` **refuses to boot** in `APP_ENV=prod` with the dev `SECRET_KEY`, wildcard CORS, or `DEBUG=true`. Secrets only via env (`.env`, git-ignored). |
| **API docs exposure** | Swagger always on. | Docs/OpenAPI off in prod by default (`settings.docs_enabled`); opt-in via `API_DOCS_ENABLED`. |
| **Auth / JWT** | — | Argon2 password hashing; access (30 min) + refresh (7 d) tokens; `jwt.decode(..., algorithms=["HS256"])` pins the algorithm, so the `none`/algorithm-confusion class (e.g. CVE-2024-33663) is not reachable; refresh tokens carry a `refresh` claim checked at the rotate endpoint. |
| **Rate limiting** | — | `slowapi` limits on register (10/5 min), login (5/min), refresh (20/min). |
| **Least privilege** | — | Backend container runs as a non-root user; prod compose sets `no-new-privileges`, `init`, and does not publish the API port (only Nginx:80 is exposed). |

## 2. Dependency audit (real output, 2026-10-03)

Reproduce with `make security` (`pip-audit` on `backend/requirements.txt`,
`npm audit` in `frontend/`).

### 2.1 Frontend — `npm audit`: 10 vulnerabilities (1 critical, 7 high, 2 moderate)

Affected packages: `@vitest/mocker`, `braces`, `chokidar`, `esbuild`, `fast-glob`,
`micromatch`, `postcss`, `tailwindcss`, `vite`, `vitest`.

**Every one is a dev/build-time tool.** None appears in the browser bundle: the
runtime dependencies (`react`, `react-dom`, `i18next`, `react-i18next`, `zustand`,
`wouter`, `lucide-react`) have zero advisories, and the production artifact is the
static `dist/` served by Nginx — it contains no vite/tailwind/node server code. The
advisories are build-time path/glob/dev-server issues that do not exist in a served
static bundle. Fixing them requires a vite-6 / toolchain major migration, deliberately
**deferred** rather than undertaken at the release freeze (it changes no shipped
byte). Re-run `npm audit` to confirm the current list.

### 2.2 Backend — `pip-audit`

**Bumped this phase (safe, direct security fixes; full test suite still green):**
- `python-multipart` 0.0.12 → **0.0.31** (PYSEC-2026-3036 / -3039 / -3040)
- `python-jose[cryptography]` 3.3.0 → **3.4.0** (PYSEC-2024-232 / -233)

**Remaining advisories (8 packages) — transitive or dev-only, with threat-model notes:**

| Package | How it enters | Relevance to our deployment |
|---|---|---|
| `starlette` | transitive (FastAPI 0.115.5) | The available fixes are starlette ≥0.47 / 1.x, which need a FastAPI major migration; deferred at freeze. Served behind Nginx; the flagged paths (staticfiles / multipart edge handling) are not exercised with untrusted input in this app. |
| `ecdsa`, `pyasn1` | transitive (`python-jose`) | We sign/verify **HS256 only**. The ECDSA/ASN.1 parsing code paths these advisories concern are never executed → outside our attack surface. |
| `transformers` | transitive (`sentence-transformers`) | Loads only local, trusted model weights from a pinned HF snapshot; no remote/pickle loading of untrusted input. |
| `sentence-transformers`, `lightgbm`, `scikit-learn` | direct ML pins | Advisories concern deserializing **untrusted** pickle/model files and DoS on crafted input. We only load models we trained ourselves (`backend/data/processed/`), never user uploads. Frozen at eval-validated pins to keep `make eval` reproducible. |
| `pytest` | dev-only | Test runner; not installed in the production runtime image path used for serving. |

**Policy:** we do not chase a zero-advisory `pip-audit` on a pinned ML stack at
release freeze — bumping `starlette`/`transformers`/`scikit-learn` is a coordinated
major upgrade that must be re-validated against the eval gates, not slipped in at the
last phase. What we **did**: fix the two direct, low-risk, high-value security pins;
keep the exploitable-by-design surfaces (JWT alg confusion, untrusted deserialization)
out of reach; and document the rest honestly instead of hiding it.

## 3. Reproduce

```bash
make security          # pip-audit (backend) + npm audit (frontend)
# after a clean install:
python -m pip install pip-audit -t .venv && <run as in Makefile>
npm --prefix frontend audit
```
