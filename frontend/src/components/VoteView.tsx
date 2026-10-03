import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

export interface VoteOption {
  id: number;
  name: string;
}

interface VoteViewProps {
  occupations: VoteOption[];
  myVotes: Record<number, number>;
  onVote: (occupationId: number, score: number) => Promise<void>;
}

export const VoteView: React.FC<VoteViewProps> = ({ occupations, myVotes, onVote }) => {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<Record<number, number>>({});
  const [busy, setBusy] = useState<number | null>(null);

  const submit = async (id: number) => {
    const score = draft[id];
    if (!score) return;
    setBusy(id);
    try {
      await onVote(id, score);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="card space-y-5">
      <div>
        <h3 className="font-bold text-xl">{t('vote.title')}</h3>
        <p className="text-textSecondary text-base">{t('vote.hint')}</p>
      </div>

      {occupations.map((occ) => {
        const current = draft[occ.id] ?? myVotes[occ.id];
        const alreadyVoted = myVotes[occ.id] !== undefined && draft[occ.id] === undefined;
        return (
          <div key={occ.id} className="border-b pb-4">
            <div className="font-semibold text-lg mb-2">{occ.name}</div>
            <div className="flex gap-2 mb-3">
              {[1, 2, 3, 4, 5].map((score) => (
                <button
                  key={score}
                  onClick={() => setDraft({ ...draft, [occ.id]: score })}
                  aria-pressed={current === score}
                  className={`min-w-touch min-h-touch rounded-lg border-2 text-lg font-bold ${
                    current === score
                      ? 'border-accent bg-accent text-white'
                      : 'border-gray-200 hover:border-accent-light'
                  }`}
                >
                  {score}
                </button>
              ))}
            </div>
            <button
              onClick={() => submit(occ.id)}
              disabled={!draft[occ.id] || busy === occ.id}
              className="btn-secondary"
            >
              {alreadyVoted && !draft[occ.id]
                ? `${t('vote.voted')} (${myVotes[occ.id]})`
                : t('vote.submit')}
            </button>
          </div>
        );
      })}
    </div>
  );
};
