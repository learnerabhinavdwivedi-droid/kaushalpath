# PHASE 17 — Low-literacy and low-bandwidth evidence

**Priority:** P1  
**Effort:** 1-2 days  
**PS rows fixed:** R12  

## Goal

Turn "designed for low literacy" from a claim into measurable evidence the PS asks for.

## Prompt

PHASE 17 — LOW-LITERACY + LOW-BANDWIDTH EVIDENCE.

1. `vite.config.ts` VitePWA manifest: add icons 192x192 and 512x512 PNG + maskable; generate them from public/favicon.svg with a script (`scripts/make_icons.mjs`).
2. Workbox runtime caching: cache GET /outcomes and /roadmap responses (StaleWhileRevalidate, 7 days) and the quick-reply chips; show OfflineBanner.
3. Onboarding: replace the long landing path for parents with a 3-screen icon flow (language -> who is speaking -> pick a concern). Add "Read this screen" button (speechSynthesis) on every page via a layout hook.
4. Settings: font size (A- / A / A+), high-contrast toggle persisted in localStorage.
5. Hindi copy audit script `scripts/check-copy.js`: warn on sentences longer than 14 words in hi.json and en.json.
6. Playwright + `@axe-core/playwright` real-browser test including color-contrast on `/talk`, `/results` and the admin dashboard.
7. Run Lighthouse (mobile, throttled) and save HTML/JSON under `docs/evidence/`.
8. Write `docs/ACCESSIBILITY_EVIDENCE.md`: methods, scores, what was NOT tested.

## Gate (acceptance)

- Lighthouse a11y >= 90.
- Installable PWA on Android Chrome.
- All tests green.
