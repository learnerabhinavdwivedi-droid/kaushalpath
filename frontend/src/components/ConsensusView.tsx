import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { CompareResponse, ConsensusResult, MemberWeights } from '../api/client';
import { CRITERIA, CRITERIA_LABEL, familyRanking } from '../utils/scoring';

interface ConsensusViewProps {
  consensus: ConsensusResult | null;
  comparison: CompareResponse | null;
  weights: MemberWeights[];
  currentUserId: number | null;
}

export const ConsensusView: React.FC<ConsensusViewProps> = ({
  consensus,
  comparison,
  weights,
  currentUserId,
}) => {
  const { t } = useTranslation();
  const [factor, setFactor] = useState<(typeof CRITERIA)[number]>('cost');
  const [value, setValue] = useState(0.5);

  const preview = useMemo(() => {
    if (!comparison || comparison.results.length === 0 || currentUserId == null) return null;
    return familyRanking(comparison.results, weights, { user_id: currentUserId, [factor]: value });
  }, [comparison, weights, currentUserId, factor, value]);

  const agreement = consensus ? Math.round(consensus.agreement_index * 100) : 0;

  return (
    <div className="space-y-4">
      <div className="card">
        <h3 className="font-bold text-xl mb-3">{t('consensus.title')}</h3>

        {consensus && consensus.ranking.length > 0 ? (
          <>
            <div className="mb-4">
              <div className="flex justify-between text-base font-medium mb-1">
                <span>{t('consensus.agreement')}</span>
                <span>{agreement}%</span>
              </div>
              <div
                className="h-4 rounded-full bg-gray-200 overflow-hidden"
                role="progressbar"
                aria-valuenow={agreement}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full bg-accent transition-all"
                  style={{ width: `${agreement}%` }}
                />
              </div>
            </div>

            <p className="text-lg">
              {t('consensus.top_choice')}: <strong>{consensus.ranking[0]?.avg_score}</strong>
            </p>
            <ol className="mt-2 space-y-1">
              {consensus.ranking.map((r, idx) => (
                <li key={r.occupation_id} className="text-base">
                  #{idx + 1} · occupation #{r.occupation_id} — avg {r.avg_score}
                </li>
              ))}
            </ol>
            <p className="mt-3 text-textSecondary">{t('consensus.next_step', { step: consensus.next_step })}</p>
          </>
        ) : (
          <p className="text-textSecondary">{t('consensus.no_votes')}</p>
        )}
      </div>

      {comparison && comparison.results.length > 0 && currentUserId != null && (
        <div className="card">
          <h4 className="font-bold text-lg">{t('consensus.whatif_title')}</h4>
          <p className="text-sm text-textSecondary mb-3">{t('consensus.whatif_hint')}</p>

          <label className="block mb-3">
            <span className="text-base font-medium">{t('compare.table_criterion')}</span>
            <select
              value={factor}
              onChange={(e) => setFactor(e.target.value as (typeof CRITERIA)[number])}
              className="input-field mt-1"
            >
              {CRITERIA.map((c) => (
                <option key={c} value={c}>
                  {t(CRITERIA_LABEL[c])}
                </option>
              ))}
            </select>
          </label>

          <label className="block mb-4">
            <div className="flex justify-between text-base mb-1">
              <span>{t(CRITERIA_LABEL[factor])}</span>
              <span className="text-textSecondary">{value.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={value}
              onChange={(e) => setValue(Number(e.target.value))}
              className="w-full accent-accent"
            />
          </label>

          <ol className="space-y-1">
            {(preview ?? []).map((r, idx) => (
              <li key={r.occupation_id} className="text-base flex justify-between">
                <span>
                  {t('consensus.rank')} {idx + 1} · {r.occupation_name}
                </span>
                <span className="text-textSecondary">{r.family_score.toFixed(2)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
};
