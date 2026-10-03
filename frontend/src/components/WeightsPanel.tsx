import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { MemberWeights, WeightsInput } from '../api/client';
import { CRITERIA, CRITERIA_LABEL } from '../utils/scoring';

interface WeightsPanelProps {
  weights: MemberWeights[];
  currentUserId: number | null;
  labelFor: (userId: number) => string;
  onSave: (weights: WeightsInput) => Promise<void>;
}

const DEFAULTS: WeightsInput = {
  cost: 0.2,
  duration: 0.2,
  salary: 0.2,
  local_jobs: 0.2,
  distance: 0.2,
};

export const WeightsPanel: React.FC<WeightsPanelProps> = ({
  weights,
  currentUserId,
  labelFor,
  onSave,
}) => {
  const { t } = useTranslation();
  const mine = weights.find((w) => w.user_id === currentUserId);
  const [draft, setDraft] = useState<WeightsInput>({ ...DEFAULTS, ...(mine || {}) });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (mine) setDraft({ ...DEFAULTS, ...mine });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUserId, weights]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await onSave(draft);
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card space-y-5">
      <div>
        <h3 className="font-bold text-xl">{t('weights.title')}</h3>
        <p className="text-textSecondary text-base">{t('weights.help')}</p>
      </div>

      <div className="space-y-4">
        {CRITERIA.map((c) => (
          <label key={c} className="block">
            <div className="flex justify-between text-base font-medium mb-1">
              <span>{t(CRITERIA_LABEL[c])}</span>
              <span className="text-textSecondary">{draft[c].toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={draft[c]}
              onChange={(e) => setDraft({ ...draft, [c]: Number(e.target.value) })}
              className="w-full accent-accent"
              aria-label={t(CRITERIA_LABEL[c])}
            />
          </label>
        ))}
      </div>

      <button onClick={handleSave} className="btn-primary w-full" disabled={saving}>
        {saving ? t('common.loading') : saved ? t('weights.saved') : t('weights.save')}
      </button>

      <div className="border-t pt-4">
        <p className="text-sm text-textSecondary mb-3">{t('weights.legend')}</p>
        <div className="space-y-3">
          {weights.map((w) => (
            <div key={w.user_id}>
              <div className="text-sm font-semibold mb-1">{labelFor(w.user_id)}</div>
              <div className="flex gap-1 h-6 rounded bg-gray-100 overflow-hidden" title={labelFor(w.user_id)}>
                {CRITERIA.map((c, idx) => (
                  <div
                    key={c}
                    className="h-full"
                    style={{
                      width: `${w[c] * 100}%`,
                      background: ['#1D4ED8', '#0f766e', '#DB2777', '#F59E0B', '#6366F1'][idx],
                    }}
                    title={`${t(CRITERIA_LABEL[c])}: ${w[c].toFixed(2)}`}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
