import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// Phase 17 — real-browser color-contrast audit.
//
// jsdom (vitest) cannot compute painted colors, so its axe runs disable the
// color-contrast rule. This spec uses @axe-core/playwright against a live
// Chromium page, where color-contrast is measurable, to prove the low-literacy
// surfaces (marketing landing + icon-first onboarding) and the scheme-admin
// dashboard meet WCAG AA contrast. We assert the color-contrast rule
// specifically so the failure message is unambiguous.

async function expectNoContrastViolations(page: import('@playwright/test').Page, path: string) {
  // 'load' (not 'networkidle'): the Vite dev HMR websocket keeps the network
  // busy forever, so networkidle never resolves. Wait for fonts to settle so
  // axe measures the final painted text colors.
  await page.goto(path, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const results = await new AxeBuilder({ page })
    .withRules(['color-contrast'])
    .analyze();
  expect(
    results.violations,
    `color-contrast violations on ${path}: ${JSON.stringify(
      results.violations.map((v) => ({ id: v.id, impact: v.impact, targets: v.nodes.map((n) => n.target) })),
    )}`,
  ).toEqual([]);
}

test('landing page meets color-contrast AA', async ({ page }) => {
  await expectNoContrastViolations(page, '/');
});

test('icon-first onboarding (/start) meets color-contrast AA', async ({ page }) => {
  await expectNoContrastViolations(page, '/start');
});

test('high-contrast mode meets color-contrast AA on /start', async ({ page }) => {
  // Simulate a low-vision user who has turned on the persisted high-contrast
  // pref; the same audit must still pass (and ideally pass more easily).
  await page.addInitScript(() => localStorage.setItem('kp-high-contrast', '1'));
  await expectNoContrastViolations(page, '/start');
});
