import React from 'react';
import { useTranslation } from 'react-i18next';

interface Point {
  date: string;
  avg_rs: number;
  n_conversations: number;
}

/**
 * Phase 16 — 30-day resistance trend line. Dependency-free (no chart lib),
 * consistent with BucketChart's hand-rolled approach.
 */
export const TrendChart: React.FC<{ data: Point[] }> = ({ data }) => {
  const { t } = useTranslation();
  const W = 480;
  const H = 160;
  const pad = 8;

  if (data.length === 0) {
    return (
      <div className="card">
        <h2 className="mb-3 font-bold text-lg">{t('admin_dash.trend_title')}</h2>
        <p className="text-sm text-textSecondary">{t('admin_dash.empty')}</p>
      </div>
    );
  }

  const maxRs = Math.max(0.05, ...data.map((d) => d.avg_rs));
  const stepX = data.length > 1 ? (W - pad * 2) / (data.length - 1) : 0;
  const points = data
    .map((d, i) => {
      const x = pad + i * stepX;
      const y = H - pad - (d.avg_rs / maxRs) * (H - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div className="card">
      <h2 className="mb-3 font-bold text-lg">{t('admin_dash.trend_title')}</h2>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label={t('admin_dash.trend_title')}
      >
        <title>{t('admin_dash.trend_title')}</title>
        <line x1={pad} y1={H - pad} x2={W - pad} y2={H - pad} className="stroke-background" strokeWidth={1} />
        <polyline points={points} fill="none" stroke="#DC2626" strokeWidth={2} />
        {data.map((d, i) => {
          const x = pad + i * stepX;
          const y = H - pad - (d.avg_rs / maxRs) * (H - pad * 2);
          return (
            <circle key={d.date} cx={x} cy={y} r={2.5} fill="#DC2626">
              <title>{`${d.date}: ${d.avg_rs} (${d.n_conversations})`}</title>
            </circle>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-textSecondary">
        <span>{data[0].date}</span>
        <span>{data[data.length - 1].date}</span>
      </div>
    </div>
  );
};
