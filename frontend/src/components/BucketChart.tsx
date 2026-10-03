import React from 'react';
import { useTranslation } from 'react-i18next';

interface BucketChartProps {
  title: string;
  data: { label: string; count: number }[];
  /** Count of buckets hidden server-side by small-group suppression. */
  suppressed?: number;
  color?: string;
}

/**
 * Dependency-free horizontal bar chart (see docs/ASSUMPTIONS.md): PHASE_8
 * suggests Recharts, but the project ships no chart library on purpose —
 * Phase 7 hand-rolled the radar to keep the PWA bundle lean, and the
 * dashboard bars stay consistent with that decision.
 */
export const BucketChart: React.FC<BucketChartProps> = ({
  title,
  data,
  suppressed = 0,
  color = 'bg-accent',
}) => {
  const { t } = useTranslation();
  const max = Math.max(1, ...data.map((d) => d.count));

  return (
    <div className="card">
      <h3 className="font-bold text-lg mb-3">{title}</h3>
      {data.length === 0 ? (
        <p className="text-textSecondary text-sm">{t('analytics.no_data')}</p>
      ) : (
        <ul className="space-y-2">
          {data.map((d) => (
            <li key={d.label} className="flex items-center gap-2 text-sm">
              <span className="w-36 shrink-0 truncate" title={d.label}>
                {d.label}
              </span>
              <span className={`h-4 rounded ${color}`} style={{ width: `${(d.count / max) * 60}%` }} />
              <span className="font-bold">{d.count}</span>
            </li>
          ))}
        </ul>
      )}
      {suppressed > 0 && (
        <p className="text-xs text-textSecondary mt-3">{t('analytics.suppressed', { n: suppressed })}</p>
      )}
    </div>
  );
};
