# PHASE 6 — Student frontend + multilingual + accessibility

GOAL: A student on a cheap phone and slow network can register, take the assessment and see recommendations in Hindi or English.

TASKS:
1. Design tokens in Tailwind config (one accent colour, large touch targets >= 44px, high contrast, font sizes readable for low literacy). Mobile-first.
2. Pages (one file each): Landing, Consent, Register/Login, ProfileForm (constraints), Assessment (one question per screen, big buttons/emoji/icons, progress bar, back button, resume), Results (top-3 cards), CareerDetail (reasons with source badges, "Demo data" badge when is_demo), Settings (language, delete my data).
3. Components (one per file): LanguageSwitcher, QuestionCard, ProgressBar, CareerCard, ReasonChip, SourceBadge, ConsentBanner, ErrorState, LoadingSkeleton.
4. State with Zustand (auth, profile, assessment session, results); API client in src/api with typed responses and retry/backoff; handle offline gracefully.
5. i18n: en + hi complete, no hard-coded strings; locale-aware numbers/currency (INR). Provide a script that checks missing keys.
6. Read-aloud button on question and result cards via Web Speech API when available (progressive enhancement); optional mic input hook behind a flag for later Whisper integration.
7. PWA: manifest, service worker caching shell + last results, installable.
8. Accessibility: semantic HTML, aria labels, keyboard navigation, focus order, colour contrast; Lighthouse accessibility >= 90.
9. Tests: Vitest for stores and components, Playwright (or Cypress) e2e: register -> assessment -> results.

ACCEPTANCE: `npm run build` ok; e2e passes against docker-compose; Lighthouse a11y >= 90 and PWA installable (paste scores); missing-i18n-keys script reports 0.
DO NOT: add heavy UI libraries; ship English-only strings.
