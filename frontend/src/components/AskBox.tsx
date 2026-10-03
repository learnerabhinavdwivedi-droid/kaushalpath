import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface AskBoxProps {
  careerTitle: string;
}

// Deterministic, template-backed objection answers (PS 26241 conversational
// surface). The LLM is never consulted here — every reply is a fixed localised
// template keyed to the concern (see i18n `ask.*`).
const OBJECTIONS: { q: string; a: string }[] = [
  { q: 'ask.q_cost', a: 'ask.a_cost' },
  { q: 'ask.q_far', a: 'ask.a_far' },
  { q: 'ask.q_jobs', a: 'ask.a_jobs' },
  { q: 'ask.q_stable', a: 'ask.a_stable' },
];

export const AskBox: React.FC<AskBoxProps> = ({ careerTitle }) => {
  const { t } = useTranslation();
  const [active, setActive] = useState<number | null>(null);

  return (
    <div className="card space-y-3" aria-live="polite">
      <h3 className="font-bold text-lg flex items-center gap-2">
        <span aria-hidden>💬</span>
        {t('ask.title')}
      </h3>
      <div className="flex flex-wrap gap-2">
        {OBJECTIONS.map((o, idx) => (
          <button
            key={o.q}
            onClick={() => setActive(active === idx ? null : idx)}
            className={`px-4 py-2 rounded-full border-2 text-base min-h-[44px] transition-colors ${
              active === idx ? 'border-accent bg-accent-light' : 'border-gray-200 hover:border-accent-light'
            }`}
          >
            {t(o.q)}
          </button>
        ))}
      </div>
      {active !== null && (
        <p className="text-textSecondary text-lg bg-gray-50 p-4 rounded-lg">{t(OBJECTIONS[active].a, { career: careerTitle })}</p>
      )}
    </div>
  );
};
