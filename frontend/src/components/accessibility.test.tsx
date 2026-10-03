import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import axe from 'axe-core';

/**
 * Phase 9 / PS R12 — automated accessibility audit.
 *
 * R12 ("design for low-literacy / low-digital-familiarity users") was the one
 * traceability row we deliberately kept at 0.5 because the a11y story was
 * *designed-for but not instrumented*. This closes that gap with a real,
 * deterministic axe-core run over the flagship recommendation card in CI
 * (`npm test`), so "complete" now means "there is a test pointing at it".
 *
 * Scope note (honesty): jsdom has no layout engine, so the `color-contrast`
 * rule cannot be evaluated here and is excluded — colour contrast is enforced
 * by the Tailwind design tokens instead. Every other axe rule (name/role,
 * aria-validity, labelling, landmarks, duplicate ids, focus order ...) runs in
 * full; a single violation fails the build.
 */

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: () => {} },
  }),
}));

vi.mock('wouter', () => ({
  // Render links as real anchors so axe can audit the link-name.
  Link: ({ href, children, className }: any) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock('../api/client', () => ({
  sendFeedback: vi.fn().mockResolvedValue({}),
}));

import { CareerCard } from './CareerCard';

const career = {
  occupation: {
    id: 7,
    title: 'Solar PV Installer',
    description: 'Installs and maintains rooftop solar systems for homes.',
  },
  reasons: [
    { code: 'RIASEC_MATCH', description: 'Matches your Realistic interest profile', type: 'positive' },
    { code: 'DEMAND', description: 'High local demand', type: 'positive' },
    { code: 'FEE_FIT', description: 'Within your budget constraint', type: 'neutral' },
  ],
  recId: 42, // non-null so the FeedbackBar (select + labels) is rendered + audited
};

async function runAxe(container: HTMLElement) {
  return axe.run(container, {
    resultTypes: ['violations'],
    rules: {
      // jsdom cannot compute colour contrast (no layout / style engine).
      'color-contrast': { enabled: false },
    },
  });
}

describe('CareerCard accessibility (axe-core)', () => {
  beforeEach(() => {
    // Expose speechSynthesis so the read-aloud button (aria-label) renders.
    Object.defineProperty(window, 'speechSynthesis', {
      value: { speak: vi.fn(), cancel: vi.fn() },
      configurable: true,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('has no detectable WCAG violations on the recommendation card', async () => {
    const { container } = render(<CareerCard career={career} />);
    const results = await runAxe(container);
    if (results.violations.length) {
      // Surface the failing rules + targets so CI output is actionable.
      const summary = results.violations
        .map((v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
        .join('\n');
      throw new Error(`axe violations:\n${summary}`);
    }
    expect(results.violations).toEqual([]);
  });

  it('gives the read-aloud control an accessible name', () => {
    const { getByRole } = render(<CareerCard career={career} />);
    // Icon-only buttons must expose a name — the core low-literacy affordance.
    expect(
      getByRole('button', { name: /read career aloud/i }),
    ).toBeInTheDocument();
  });
});
