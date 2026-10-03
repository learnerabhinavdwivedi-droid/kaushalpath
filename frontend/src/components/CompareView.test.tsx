import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Deterministic i18n: keys come back as-is so assertions target real content.
vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'en', changeLanguage: () => {} } }),
}));

import { CompareView } from './CompareView';
import type { CompareResponse, MemberWeights } from '../api/client';

const comparison: CompareResponse = {
  results: [
    {
      occupation_id: 1,
      occupation_name: 'Electrician',
      criteria: { cost: 0.8, duration: 0.6, salary: 0.5, local_jobs: 0.7, distance: 0.9 },
      member_totals: { '1': 0.7, '2': 0.6 },
      family_score: 0.65,
      spread: 0.1,
    },
    {
      occupation_id: 2,
      occupation_name: 'Carpenter',
      criteria: { cost: 0.4, duration: 0.5, salary: 0.3, local_jobs: 0.2, distance: 0.3 },
      member_totals: { '1': 0.4, '2': 0.35 },
      family_score: 0.38,
      spread: 0.05,
    },
  ],
  disagreement: { occupation_id: 1, criterion: 'salary', detail: 'Members disagree most on Electrician.' },
};

const weights: MemberWeights[] = [
  { user_id: 1, cost: 0.2, duration: 0.2, salary: 0.2, local_jobs: 0.2, distance: 0.2 },
  { user_id: 2, cost: 0.1, duration: 0.1, salary: 0.6, local_jobs: 0.1, distance: 0.1 },
];

describe('CompareView', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders both careers side by side with family scores', () => {
    render(<CompareView comparison={comparison} weights={weights} />);
    expect(screen.getByText('Electrician')).toBeInTheDocument();
    expect(screen.getByText('Carpenter')).toBeInTheDocument();
    // family scores are data, not i18n keys
    expect(screen.getAllByText(/0\.65/).length).to.be.greaterThan(0);
    expect(screen.getAllByText(/0\.38/).length).to.be.greaterThan(0);
  });

  it('flags the largest disagreement', () => {
    render(<CompareView comparison={comparison} weights={weights} />);
    expect(screen.getByText(/compare\.disagreement_title/)).toBeInTheDocument();
    expect(screen.getByText(/Members disagree most on/)).toBeInTheDocument();
  });

  it('shows the placeholder when there is nothing to compare', () => {
    render(<CompareView comparison={null} weights={weights} />);
    expect(screen.getByText('room.select_careers')).toBeInTheDocument();
  });
});
