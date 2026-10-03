import React from 'react';
import { useTranslation } from 'react-i18next';
import type { CompareResponse, MemberWeights } from '../api/client';
import { RadarChart } from './RadarChart';
import { SourceBadge } from './SourceBadge';
import { CRITERIA, CRITERIA_LABEL, CRITERIA_SOURCE, topDriver } from '../utils/scoring';

const SERIES_COLORS = ['#1D4ED8', '#0f766e', '#DB2777'];

interface CompareViewProps {
  comparison: CompareResponse | null;
  weights: MemberWeights[];
  isDemo?: boolean;
}

export const CompareView: React.FC<CompareViewProps> = ({ comparison, weights, isDemo = true }) => {
  const { t } = useTranslation();

  if (!comparison || comparison.results.length === 0) {
    return <div className="card text-textSecondary">{t('room.select_careers')}</div>;
  }

  const axes = CRITERIA.map((c) => t(CRITERIA_LABEL[c]));
  const series = comparison.results.map((r, idx) => ({
    name: r.occupation_name,
    color: SERIES_COLORS[idx % SERIES_COLORS.length],
    values: CRITERIA.map((c) => r.criteria[c]),
  }));

  const winner = comparison.results[0];
  const driver = topDriver(winner, weights);

  return (
    <div className="space-y-4">
      <div className="card">
        <h3 className="font-bold text-xl mb-1">{t('compare.title')}</h3>
        <p className="text-sm text-textSecondary mb-3">{t('compare.source_note')}</p>
        <RadarChart axes={axes} series={series} label={t('compare.radar_caption')} />
        <p className="text-xs text-textSecondary text-center mt-2">{t('compare.radar_caption')}</p>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-base border-collapse">
          <thead>
            <tr>
              <th className="text-left p-2 border-b">{t('compare.table_criterion')}</th>
              {comparison.results.map((r) => (
                <th key={r.occupation_id} className="text-left p-2 border-b align-top">
                  <div className="font-bold">{r.occupation_name}</div>
                  <div className="text-xs font-normal text-textSecondary flex items-center gap-1">
                    {t('compare.family_score')}: {r.family_score.toFixed(2)}
                    <SourceBadge isDemo={isDemo} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {CRITERIA.map((c) => (
              <tr key={c}>
                <td className="p-2 border-b font-medium" title={CRITERIA_SOURCE[c]}>
                  {t(CRITERIA_LABEL[c])}
                </td>
                {comparison.results.map((r) => (
                  <td key={r.occupation_id} className="p-2 border-b" title={CRITERIA_SOURCE[c]}>
                    {r.criteria[c].toFixed(2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card bg-accent-light">
        <h4 className="font-bold">{t('compare.why_this')}</h4>
        <p className="text-base">{t('compare.why_higher', { best: t(CRITERIA_LABEL[driver]) })}</p>
      </div>

      {comparison.disagreement && comparison.disagreement.criterion && (
        <div className="card border-l-4 border-error">
          <h4 className="font-bold flex items-center gap-2">⚠️ {t('compare.disagreement_title')}</h4>
          <p className="text-base text-textSecondary">{comparison.disagreement.detail}</p>
        </div>
      )}
    </div>
  );
};
