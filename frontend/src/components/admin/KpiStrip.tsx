import React from 'react';
import { useTranslation } from 'react-i18next';
import type { DashboardKpis } from '../../api/client';

/** Phase 16 — headline KPI strip for the scheme-admin dashboard. */
export const KpiStrip: React.FC<{ kpis: DashboardKpis }> = ({ kpis }) => {
  const { t } = useTranslation();

  const items = [
    { label: t('admin_dash.kpi_families'), value: String(kpis.families_counselled) },
    { label: t('admin_dash.kpi_high'), value: `${kpis.pct_high_resistance}%` },
    {
      label: t('admin_dash.kpi_top_concern'),
      value: kpis.top_concern ? t(`admin_dash.topic_${kpis.top_concern}`) : '—',
    },
    { label: t('admin_dash.kpi_escalation'), value: `${kpis.escalation_rate}%` },
    { label: t('admin_dash.kpi_improved'), value: `${kpis.sentiment_improved_pct}%` },
  ];

  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {items.map((it) => (
        <div key={it.label} className="card text-center">
          <dt className="text-xs text-textSecondary">{it.label}</dt>
          <dd className="mt-1 text-2xl font-bold text-accent">{it.value}</dd>
        </div>
      ))}
    </dl>
  );
};
