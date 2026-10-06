import React from 'react';
import { useTranslation } from 'react-i18next';

/**
 * The AskBox concern chips, promoted into the chat as one-tap quick replies
 * (PHASE_15: "keep AskBox chips as QuickReplies"). Each chip sends the
 * question itself, so the deterministic engine classifies a real topic and
 * grounds a fact card under the answer.
 */
const TOPICS = ['income', 'security', 'social', 'safety', 'distance', 'cost'] as const;

export const QuickReplies: React.FC<{ onPick: (text: string) => void }> = ({ onPick }) => {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap gap-2">
      {TOPICS.map((topic) => {
        const label = t(`chat.rq_${topic}`);
        return (
          <button
            key={topic}
            type="button"
            onClick={() => onPick(label)}
            className="rounded-full border-2 border-gray-200 px-4 py-2 text-base transition-colors hover:border-accent hover:bg-accent-light min-h-[44px]"
          >
            {label}
          </button>
        );
      })}
    </div>
  );
};
