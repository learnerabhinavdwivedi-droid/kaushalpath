# KaushalPath — Privacy & Data Protection (DPDP-aligned)

How KaushalPath handles personal data, mapped to the principles of India's
**Digital Personal Data Protection Act, 2023** (and its predecessor DPDP Bill).
This is an engineering transparency document for evaluators and operators — it is
**not legal advice** and does not constitute a Data Protection Impact Assessment.

> **Design stance:** we minimise what we collect, we never collect the most
> sensitive categories at all, and every data subject right the app promises is
> backed by a tested endpoint (see the table at the bottom).

## 1. What we do NOT collect (data minimisation by design)

* **No caste, religion, or gender** fields exist anywhere in the schema or the
  ML feature set. This is a hard rule (`RULES.md`): those attributes are never
  an input, a feature, a segmentation key, or a fairness slice. Verified by a
  codebase-wide search (zero references in `backend/app/`).
* **No government identifiers** (Aadhaar, PAN, etc.), no phone, no precise GPS.
* **No biometrics**, no free-text that could smuggle in sensitive attributes —
  assessment items are fixed-choice Likert responses.
* Location is captured only as a **district** (coarse), used solely for
  centre-reachability rules and regional aggregates.

We deliberately do **not** collect gender even though the eval plan mentions a
"gender slice": fairness (G6) is therefore measured on **urban vs rural** — the
only axis we can evaluate without storing a protected attribute. Not collecting
the data *is* the privacy control.

## 2. What we DO collect, and why (purpose limitation)

| Data | Where | Purpose | Necessary? |
|---|---|---|---|
| Email + hashed password (Argon2) | `User` | Authentication | Yes |
| Role (student / parent / counsellor / admin) | `User` | Authorisation | Yes |
| Preferred language (en/hi) | `User` | Vernacular UI | Yes |
| Age, education level, district, income band | `Student` | Hard eligibility rules + family-context explanation | Yes (for the service) |
| RIASEC + aptitude responses & derived profile | `Assessment.state_json`, `Student` | Recommendations | Yes |
| Budget / relocate / reachability constraints | `Student` / request | Eligibility filtering | Yes |
| Recommendations, room votes, feedback sentiment | respective tables | History, family decision support, quality signal | Yes |

`income_band` and household context shape the **family-facing explanation only**,
never the interest/aptitude score.

`Assessment.state_json` holds the aptitude answer key and is **PII-adjacent**: it
is never returned raw in any response (see `ASSUMPTIONS.md` A14).

## 3. Consent

* Registration is **rejected without consent** — `POST /auth/register` requires
  `give_consent=true` and stores a `consent_at` timestamp
  (`backend/app/api/routes/auth.py`). There is no silent/default consent.
* The onboarding **consent screen is in plain Hindi and English** (the two
  shipped languages), written at a low-literacy reading level, and states what
  data is taken and the right to delete it. The consent copy is a first-class UI
  string (`consent.*` in `frontend/src/i18n/locales/{en,hi}.json`, surfaced by
  `components/ConsentBanner.tsx` and the register form), not buried in a ToS link.

## 4. Rights the app implements (each is tested)

| DPDP-style right | Implementation | Test |
|---|---|---|
| **Right to erasure** | `DELETE /auth/students/me` removes the user + their data | `test_phase5` (self-delete) |
| **Right to access** | `GET /auth/me` returns the subject's own record | `test_phase5` |
| **Correct / rectify** | constraint + profile update endpoints | phase tests |
| **Data portability (minimal)** | counsellor CSV export excludes deleted subjects | `test_phase8` |

**Deletion integrity:** erasure writes an **append-only audit row** recording
*that* and *by whom* a deletion happened (`action="data_deletion"`), but stores
**only the entity id and actor — never the deleted payload**
(`ASSUMPTIONS.md` A19). A "delete" that quietly retained the PII in a log would
defeat the right, so the audit trail is deliberately non-retentive.

## 5. Retention & administrative safeguards

* **Retention:** personal data is kept only while the account exists; on request
  it is deleted immediately (no soft-delete grace period that keeps PII).
  Reference/outcome data is non-personal and retained.
* **Access control:** role-based authorisation; counsellors see only their own
  cohort; every aggregate on the admin dashboard enforces **small-group
  suppression** (buckets with < 5 distinct students are hidden — `A17`), so the
  dashboards cannot be used to re-identify individuals.
* **Security:** see [`SECURITY.md`](SECURITY.md) — secrets via env only, JWT
  expiry + refresh rotation, rate limiting, prod fail-fast config guards,
  security headers, TLS/HSTS at Nginx, non-root containers.
* **Backups:** `make backup` produces consistent SQLite snapshots under
  `backups/` (git-ignored). Backups inherit the same access controls and must be
  treated as personal data; a restore is the operator's responsibility.
* **Breach response (policy):** as data fiduciary we commit to notifying affected
  users and the Board promptly on a personal-data breach; the app logs a
  `request_id` per request to support forensic reconstruction *without* storing
  payloads in logs.

## 6. Third parties & LLMs

* No third-party analytics, ads, or trackers are loaded (CSP `connect-src 'self'`
  in `infra/nginx.conf`).
* If an LLM is used it **only verbalises the already-ranked, non-identifying
  output** (reason codes + templated data); no personal data is sent to, or used
  to train, any external model (`RULES.md` non-negotiable #4). The offline demo
  path uses deterministic templates and needs no external API at all.
