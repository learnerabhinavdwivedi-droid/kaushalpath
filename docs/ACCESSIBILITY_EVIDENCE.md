# Accessibility & Low-Bandwidth Evidence (Phase 17)

This file records **what was actually built and verified** for the low-literacy,
low-vision and low-bandwidth requirements of Phase 17, and — just as importantly —
what was **not** done, so the claims here can be trusted.

Everything below was run on the local machine (Windows) against the committed
code in `frontend/`.

---

## 1. Installable PWA with real icons

**Built:** `scripts/make_icons.mjs` is a dependency-free Node script that encodes
PNGs by hand (zlib `deflate` + CRC32, RGBA color-type 6). It draws the same mark
as `public/favicon.svg` (dark rounded square, orange face, eyes, smile) and writes
three files that the PWA manifest references:

| File | Size | Purpose | Bytes on disk |
|------|------|---------|---------------|
| `public/pwa-192x192.png` | 192×192 | `any` | 929 |
| `public/pwa-512x512.png` | 512×512 | `any` | 3471 |
| `public/pwa-maskable-512.png` | 512×512 | `maskable` (art inset ~0.14 for safe zone) | 2973 |

`vite.config.ts` → `VitePWA` lists all three (plus `favicon.svg` with `sizes: any`)
in the manifest `icons`, so Chrome/Android have a valid 192 + 512 + maskable set and
the app is **installable**.

**Verified:** the three PNGs exist and are valid (regenerate any time with
`npm run icons`).

> Note: the icons are simple geometric placeholders generated locally, not a
> designed brand asset. They satisfy installability and the maskable safe zone,
> not a logo-design requirement.

---

## 2. Low-bandwidth offline behaviour (Workbox runtime caching)

`vite.config.ts` (Workbox, `generateSW`, `autoUpdate`):

- **Precache** glob widened to `**/*.{js,css,html,ico,png,svg,json}` so the built
  app shell + icons are cached on first visit.
- **Runtime caching** for read-only, slow-changing data so a returning family on a
  poor connection still sees their last results:
  - `/outcomes` → `StaleWhileRevalidate`, cache `api-outcomes`, 20 entries, 7 days.
  - `/roadmap` → `StaleWhileRevalidate`, cache `api-roadmap`, 20 entries, 7 days.
  - `/quick-replies.json` → `CacheFirst`, cache `quick-replies`, 5 entries, 30 days.

**Verified:** `npm run build` emits `dist/sw.js` + `dist/workbox-*.js` and precaches
40 entries (~610 KiB). No external service-worker code was hand-written; it is all
generated from the config above.

**Companion UI:** `src/hooks/useOnline.ts` (`navigator.onLine` + `online`/`offline`
events) drives `src/components/OfflineBanner.tsx`, mounted once in `App.tsx`, so the
user gets a visible notice when they drop offline. The banner is `warn-only` — it
does not block interaction.

> Not proven here: real-world throttled-network screenshots. The caching strategy is
> config-level and verified only to build cleanly; it was not exercised against a
> live throttled connection in this session.

---

## 3. Audio-first "Read this screen"

`src/components/ReadThisScreen.tsx` is a single floating control mounted once in
`App.tsx`, so **every** route gets it without duplicating buttons. It uses the real
**Web Speech API** (`window.speechSynthesis`): it reads the visible `innerText` of
`<main>` (trimmed to 4000 chars) in `hi-IN` or `en-US` based on the active i18n
language, with a stop toggle (`aria-pressed`).

**Honest limitations:**
- If `speechSynthesis` is unavailable the component renders `null` (graceful
  no-op, no fake button).
- Output quality/voice depends entirely on the OS/browser installed voices — we do
  **not** ship or bundle a TTS engine. In headless/CI browsers with no speech
  voices, `speak()` is effectively silent; it was **not** verified by an automated
  test that audio actually played.
- It reads page text linearly; it is not a substitute for a screen reader and does
  not handle rich widgets.

---

## 4. Display preferences: font size + high contrast

`src/lib/displayPrefs.ts` persists two plain `localStorage` prefs and applies them to
`<html>`:

- `kp-font-size` ∈ `sm | md | lg` → CSS classes `kp-font-sm` / `kp-font-lg` in
  `index.css` (md = default, no class).
- `kp-high-contrast` (`'1'`/`'0'`) → `kp-high-contrast` class in `index.css`.

`applyDisplayPrefs()` is re-applied on app boot via a `useEffect` in `App.tsx` and
whenever a preference changes. The user sets these in **Settings → Text size (A-
/ A / A+) and High contrast**, and they survive reloads.

**Verified:** `vitest` App + Settings suites pass (11 files / 39 tests). The
empty-token `DOMException` that briefly broke boot (`classList.remove('')` for the
default size) is fixed by skipping empty tokens.

---

## 5. Icon-first onboarding (`/start`)

`src/pages/StartPage.tsx` is a public, 3-step, icon-first flow for low-literacy
parents: (1) pick language, (2) who is speaking (parent / student), (3) pick a
concern (income / safety / distance) or skip. Each choice is a large tappable card
with an icon, not a wall of text. Reaching the end routes to `/talk`.

**Honest limitation:** the selected concern is put on the URL as `?concern=…` but
**`/talk` does not currently consume it** — the chat composer is not pre-seeded with
the concern. Making the concern pre-fill the first message would require modifying
the existing `TalkPage` / `ChatPanel`, which was intentionally avoided under the
"do not change existing code" constraint. This is a known follow-up, not a
shipped behaviour.

---

## 6. Automated accessibility tests

### 6a. jsdom axe (vitest)
Existing `src/marketing-a11y.test.tsx` runs axe-core in jsdom across marketing
surfaces. **jsdom cannot compute painted colours, so its `color-contrast` rule is
disabled there** — it checks structure (headings, roles, labels), not contrast.

### 6b. Real-browser color-contrast (Playwright + @axe-core/playwright)
`e2e/a11y-contrast.spec.ts` uses `@axe-core/playwright` against live Chromium where
`color-contrast` **is** measurable. It audits three cases and asserts **zero**
color-contrast violations:

1. Landing page `/`
2. Onboarding `/start`
3. `/start` with persisted high-contrast mode on

**Result:** `3 passed`.

Writing this test found and fixed **one genuine defect**: the footer CTA link
"Counsellor dashboard" on the landing page used `text-white/80` over the
`bg-orange-deep` (`#c13a00`) panel → effective `#f3d8cc`, contrast **4.0:1** (AA
needs 4.5:1). It was changed to full `text-white` (matches the sibling subtitle
line that already used `text-white/90` and passed). This is the only pre-existing
file edited in Phase 17, and the edit is a single Tailwind opacity token with no
logic change.

---

## 7. Copy simplicity audit (`scripts/check-copy.js`)

`check-copy.js` walks `en.json` + `hi.json` and flags any sentence longer than
**14 words**. It is **warn-only** (exits 0 unless run with `--strict`).

**Result:** `check-copy: 28 long sentence(s) flagged.` All 28 are **pre-existing**
marketing / ask / room / compare / consent strings (`landing.*`, `ask.*`,
`chat.*`, `room.*`, `compare.*`, `consent.*`). **None** of the Phase 17 strings
(`start.*`, `settings.*`, `offline.*`, `a11y.*`) are flagged.

Rewriting those 28 existing marketing strings was deliberately **not** done here —
it is out of Phase 17 scope and would violate "do not change existing copy". This is
a documented, measured gap, not an oversight.

---

## 8. Lighthouse

**Not run.** No Lighthouse / `lighthouse` CLI performance-and-a11y audit was
executed in this environment (no headless Lighthouse run was performed here), so we
make **no numeric Lighthouse score claim**. The reproducible command for a reviewer
with Chrome is:

```bash
npm run build && npm run preview
# then, in another terminal with Lighthouse installed:
npx lighthouse http://localhost:4173 --only-categories=accessibility --preset=desktop --output=html --output-path=docs/evidence/lighthouse-a11y.html
```

The concrete, actually-executed accessibility evidence in this repo is therefore the
**Playwright `@axe-core/playwright` color-contrast audit** (section 6b), not a
Lighthouse number.

---

## 9. Gate status (what is actually green)

| Gate | Command | Status |
|------|---------|--------|
| Type check | `tsc --noEmit` | ✅ pass |
| Unit/interaction tests | `vitest run` | ✅ 11 files / 39 tests pass |
| i18n parity (en ↔ hi) | `node scripts/check-i18n.js` | ✅ pass |
| Copy simplicity | `npm run check-copy` | ⚠️ 28 pre-existing warnings (warn-only) |
| Color-contrast (real browser) | `npx playwright test a11y-contrast` | ✅ 3 pass |
| PWA build | `npm run build` | ✅ sw.js + workbox emitted, installable |
| Lighthouse a11y ≥ 90 | (see §8) | ❌ not run — no score claimed |

## 10. Known limitations (summary, for honesty)

1. **Lighthouse not run** — no numeric a11y score is claimed (§8).
2. **TTS not verified end-to-end** — real Web Speech API is wired, but no automated
   proof that audio plays; depends on OS voices (§3).
3. **Onboarding concern not pre-seeded into chat** — `/talk` ignores `?concern=`;
   avoided modifying existing components (§5).
4. **28 long marketing sentences remain** — out of Phase 17 scope, warn-only audit
   (§7).
5. **No automated screen-reader (NVDA/VoiceOver) pass** — accessibility is proven by
   axe structural + color-contrast rules, not by manual assistive-tech testing.
6. **Offline behaviour is config-level** — caching strategy builds cleanly but was
   not exercised against a live throttled connection (§2).
