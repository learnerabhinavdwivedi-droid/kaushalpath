import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import axe from 'axe-core';

/**
 * Phase 16 — the scheme-admin dashboard must render and pass an automated
 * accessibility audit. As in the shared a11y suite, jsdom has no layout engine
 * so colour-contrast is disabled (it is enforced via the Tailwind tokens);
 * every other axe rule runs.
 */
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: () => {} },
  }),
}));

vi.mock('wouter', () => ({
  Link: ({ href, children, className }: any) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

const { sample } = vi.hoisted(() => ({
  sample: {
    filters: { from: '', to: '', state: '', trade: '', lang: '' },
    kpis: {
      families_counselled: 12,
      total_conversations: 30,
      pct_high_resistance: 33.3,
      top_concern: 'safety',
      escalation_rate: 10,
      sentiment_improved_pct: 20,
    },
    districts: [
      {
        district: 'Lucknow',
        state: 'UP',
        lat: 26.8467,
        lon: 80.9462,
        n: 10,
        avg_rs: 0.72,
        share_high: 0.6,
        top_topics: ['safety'],
        shift: { softened: 2, hardened: 5, unchanged: 3 },
        is_suppressed: false,
      },
      {
        district: 'SmallDistrict',
        state: 'UP',
        lat: 25.3,
        lon: 83.0,
        n: 2,
        avg_rs: null,
        share_high: null,
        top_topics: [],
        shift: { softened: 0, hardened: 1, unchanged: 1 },
        is_suppressed: true,
      },
    ],
    matrix: {
      concerns: ['safety', 'cost'],
      trades: ['Electrician', 'Plumber'],
      cells: [
        [8, 2],
        [0, 6],
      ],
      suppressed_cells: 1,
    },
    phrases: { safety: ['Parents worried about night classes'] },
    trend: [
      { date: '2026-10-01', avg_rs: 0.6, n_conversations: 4 },
      { date: '2026-10-02', avg_rs: 0.7, n_conversations: 6 },
    ],
    shift: { softened: 6, hardened: 12, unchanged: 12 },
    suppressed_groups: 1,
    high_threshold: 0.6,
    is_demo: true,
  },
}));

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>();
  return {
    ...actual,
    getResistanceDashboard: vi.fn().mockResolvedValue(sample),
    exportResistanceCsv: vi.fn().mockResolvedValue('blob:http://localhost/x'),
  };
});

import { AdminResistancePage } from './AdminResistancePage';

describe('AdminResistancePage (Phase 16)', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders the dashboard from the API and flags suppression + demo', async () => {
    const { getByText, findByText } = render(<AdminResistancePage />);
    // Demo banner + suppression notice surface for the fixture.
    await findByText('admin_dash.demo_banner');
    await findByText(/admin_dash.suppressed_notice/);
    // A district row and its suggested action render.
    expect(getByText('Lucknow')).toBeInTheDocument();
  });

  it('has no detectable WCAG violations on the dashboard', async () => {
    const { container, findByText } = render(<AdminResistancePage />);
    await findByText('admin_dash.demo_banner');
    const results = await axe.run(container, {
      resultTypes: ['violations'],
      rules: { 'color-contrast': { enabled: false } },
    });
    if (results.violations.length) {
      const summary = results.violations
        .map((v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
        .join('\n');
      throw new Error(`axe violations:\n${summary}`);
    }
    expect(results.violations).toEqual([]);
  });
});
