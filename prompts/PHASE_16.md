# PHASE 16 — Administrator resistance dashboard v2

**Priority:** P1  
**Effort:** 2 days  
**PS rows fixed:** R10  

## Goal

Show scheme administrators WHERE resistance is concentrated (map and table) and WHY (topics, trades, trend, shift), with exports and a clear action hint.

## Prompt

PHASE 16 — ADMIN DASHBOARD V2. Depends on Phase 13 APIs.

Today ResistancePage.tsx is a small topic/district/trade count view scoped to the counsellor's cohort. Build a scheme-administrator view:

1. Route `/admin/resistance` guarded by RequireRole(scheme_admin|admin). Keep the counsellor cohort pages as they are.
2. Components: KpiStrip, DistrictBubbleMap (inline SVG; project lat/lon to the viewport; radius = families, colour = avg Rs; no external tiles so it works offline), DistrictTable (sortable), ConcernTradeMatrix (heat cells), TrendChart (30 days, reuse BucketChart styles), ShiftBars (improved/unchanged/worsened), TopPhrases.
3. suggestAction(district) in a pure util with unit tests (rules, not ML).
4. Filters: date range, state, trade, language; Export CSV button -> `/admin/resistance/export.csv`.
5. Show suppression notice when a group has fewer than 5 families; show demo-data banner when is_demo rows are present.
6. i18n en + hi; keyboard accessible; axe test.

## Gate (acceptance)

- `vitest`, Playwright admin flow, `npm run build` all pass.
- Dashboard renders from the seeded 300 conversations; empty-state and k<5 suppression messages are shown.
