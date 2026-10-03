import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'en', changeLanguage: () => {} } }),
}));

import { OverrideDialog } from './OverrideDialog';
import type { RecommendationRow } from '../api/client';

const recs: RecommendationRow[] = [
  { occupation_id: 10, occupation_name: 'Electrician', rank: 1, score: 0.9, reasons: [], is_demo: false },
  { occupation_id: 20, occupation_name: 'Carpenter', rank: 2, score: 0.7, reasons: [], is_demo: true },
];

const renderDialog = (onSubmit = vi.fn(), onClose = vi.fn()) => {
  render(
    <OverrideDialog recommendations={recs} submitting={false} onClose={onClose} onSubmit={onSubmit} />
  );
  return {
    submit: screen.getByText('override.submit').closest('button') as HTMLButtonElement,
    occupation: screen.getByLabelText('override.occupation') as HTMLSelectElement,
    note: screen.getByLabelText(/override\.reason/) as HTMLTextAreaElement,
    onSubmit,
  };
};

describe('OverrideDialog', () => {
  it('disables submit until both occupation and a non-empty reason are provided', () => {
    const { submit, occupation } = renderDialog();
    expect(submit).toBeDisabled();
    fireEvent.change(occupation, { target: { value: '10' } });
    // still disabled: the reason note is REQUIRED for the audit trail
    expect(submit).toBeDisabled();
  });

  it('calls onSubmit with the chosen occupation id and a trimmed note', () => {
    const { submit, occupation, note, onSubmit } = renderDialog();
    fireEvent.change(occupation, { target: { value: '10' } });
    fireEvent.change(note, { target: { value: '  family prefers local  ' } });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);
    expect(onSubmit).toHaveBeenCalledWith(10, 'family prefers local');
  });
});
