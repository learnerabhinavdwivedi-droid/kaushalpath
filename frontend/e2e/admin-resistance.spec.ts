import { test, expect } from '@playwright/test';

const dashboard = {
  filters: { from: '', to: '', state: '', trade: '', lang: '' },
  kpis: {
    families_counselled: 42,
    total_conversations: 300,
    pct_high_resistance: 28.4,
    top_concern: 'safety',
    escalation_rate: 12.0,
    sentiment_improved_pct: 19.3,
  },
  districts: [
    {
      district: 'Lucknow',
      state: 'Uttar Pradesh',
      lat: 26.8467,
      lon: 80.9462,
      n: 60,
      avg_rs: 0.66,
      share_high: 0.55,
      top_topics: ['safety', 'cost'],
      shift: { softened: 12, hardened: 30, unchanged: 18 },
      is_suppressed: false,
    },
  ],
  matrix: {
    concerns: ['safety', 'cost', 'income'],
    trades: ['Electrician', 'Plumber'],
    cells: [
      [20, 12],
      [8, 6],
      [5, 9],
    ],
    suppressed_cells: 0,
  },
  phrases: { safety: ['Night classes unsafe', 'No women trainers'] },
  trend: [
    { date: '2026-09-20', avg_rs: 0.6, n_conversations: 10 },
    { date: '2026-09-21', avg_rs: 0.7, n_conversations: 14 },
  ],
  shift: { softened: 58, hardened: 120, unchanged: 122 },
  suppressed_groups: 2,
  high_threshold: 0.6,
  is_demo: true,
};

async function seed(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'fake-admin-jwt');
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({ state: { token: 'fake-admin-jwt', role: 'scheme_admin', studentId: null }, version: 0 }),
    );
  });
  await page.route('**/auth/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 1,
        email: 'admin@example.com',
        role: 'scheme_admin',
        lang: 'en',
        student_id: null,
      }),
    }),
  );
  await page.route('**/admin/resistance/dashboard**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(dashboard) }),
  );
  await page.route('**/admin/resistance/export.csv', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'text/csv',
      body: 'conversation_id,student_id,district,state,trade,shift_label,avg_rs,high_resistance,created_at\n1,2,Lucknow,Uttar Pradesh,Electrician,unchanged,0.66,Yes,2026-09-21T00:00:00\n',
    }),
  );
}

test('admin resistance dashboard renders, filters and exports', async ({ page }) => {
  await seed(page);
  await page.goto('/admin/resistance');

  // KPI + map + table render from the dashboard payload.
  await expect(page.getByText('42')).toBeVisible();
  await expect(page.getByRole('rowheader', { name: 'Lucknow' })).toBeVisible();
  // Suppression notice is shown for the 2 hidden groups.
  await expect(page.getByRole('status').filter({ hasText: /hidden/i })).toBeVisible();

  // Applying the language filter refetches with lang=hi in the query string.
  const reqPromise = page.waitForRequest((req) =>
    req.url().includes('/admin/resistance/dashboard') && req.url().includes('lang=hi'),
  );
  await page.getByLabel(/Language/i).selectOption('hi');
  await reqPromise;

  // Export CSV button triggers a call to the export endpoint.
  const exportReq = page.waitForRequest((req) => req.url().includes('/admin/resistance/export.csv'));
  await page.getByRole('button', { name: /Export CSV/i }).click();
  await exportReq;
});
