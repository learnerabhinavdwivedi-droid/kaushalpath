import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { ObjectionSentiment, ObjectionTopic } from '../api/client';

interface AskBoxProps {
  careerTitle: string;
  occupationId?: number | null;
  // When provided (inside a family room), tapping a concern records a
  // topic+sentiment tag for the Phase 8 resistance dashboard.
  onObjection?: (
    topic: ObjectionTopic,
    sentiment: ObjectionSentiment,
    occupationId?: number | null
  ) => void;
}

// Deterministic, template-backed objection answers (PS 26241 conversational
// surface). The LLM is never consulted here — every reply is a fixed localised
// template keyed to the concern (see i18n `ask.*`). Each concern also maps to a
// parental-objection topic (income / safety / security / social perception).
const OBJECTIONS: { q: string; a: string; topic: ObjectionTopic }[] = [
  { q: 'ask.q_cost', a: 'ask.a_cost', topic: 'income' },
  { q: 'ask.q_far', a: 'ask.a_far', topic: 'safety' },
  { q: 'ask.q_jobs', a: 'ask.a_jobs', topic: 'security' },
  { q: 'ask.q_stable', a: 'ask.a_stable', topic: 'social' },
];

export const AskBox: React.FC<AskBoxProps> = ({ careerTitle, occupationId, onObjection }) => {
  const { t } = useTranslation();
  const [active, setActive] = useState<number | null>(null);
  const [recorded, setRecorded] = useState(false);

  const select = (idx: number) => {
    setActive(active === idx ? null : idx);
    if (active !== idx && onObjection) {
      onObjection(OBJECTIONS[idx].topic, 'concern', occupationId);
      setRecorded(true);
    }
  };

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
            onClick={() => select(idx)}
            className={`px-4 py-2 rounded-full border-2 text-base min-h-[44px] transition-colors ${
              active === idx ? 'border-accent bg-accent-light' : 'border-gray-200 hover:border-accent-light'
            }`}
          >
            {t(o.q)}
          </button>
        ))}
      </div>
      {active !== null && (
        <p className="text-textSecondary text-lg bg-gray-50 p-4 rounded-lg">
          {t(OBJECTIONS[active].a, { career: careerTitle })}
        </p>
      )}
      {recorded && onObjection && (
        <p className="text-sm text-brand">{t('ask.recorded')}</p>
      )}
    </div>
  );
};
