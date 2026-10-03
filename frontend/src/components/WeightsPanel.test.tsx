import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'en', changeLanguage: () => {} } }),
}));

import { WeightsPanel } from './WeightsPanel';
import type { MemberWeights } from '../api/client';

const weights: MemberWeights[] = [
  { user_id: 1, cost: 0.2, duration: 0.2, salary: 0.2, local_jobs: 0.2, distance: 0.2 },
  { user_id: 2, cost: 0.5, duration: 0.1, salary: 0.2, local_jobs: 0.1, distance: 0.1 },
];

describe('WeightsPanel', () => {
  it('renders a slider per criterion for the current member', () => {
    render(
      <WeightsPanel
        weights={weights}
        currentUserId={1}
        labelFor={(id) => `member-${id}`}
        onSave={vi.fn()}
      />
    );
    // five range inputs (cost, duration, salary, local_jobs, distance)
    expect(screen.getAllByRole('slider').length).toBe(5);
  });

  it('calls onSave with the edited weight vector', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <WeightsPanel
        weights={weights}
        currentUserId={1}
        labelFor={(id) => `member-${id}`}
        onSave={onSave}
      />
    );
    const firstSlider = screen.getAllByRole('slider')[0];
    fireEvent.change(firstSlider, { target: { value: '0.8' } });
    fireEvent.click(screen.getByText('weights.save'));
    await Promise.resolve();
    expect(onSave).toHaveBeenCalledTimes(1);
    const arg = onSave.mock.calls[0][0];
    expect(arg.cost).toBe(0.8);
  });

  it('shows every member weight row side by side', () => {
    render(
      <WeightsPanel
        weights={weights}
        currentUserId={1}
        labelFor={(id) => `member-${id}`}
        onSave={vi.fn()}
      />
    );
    expect(screen.getByText('member-1')).toBeInTheDocument();
    expect(screen.getByText('member-2')).toBeInTheDocument();
  });
});
