import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'wouter';
import {
  DashboardFilters,
  ResistanceDashboard,
  exportResistanceCsv,
  getResistanceDashboard,
} from '../api/client';
import { KpiStrip } from '../components/admin/KpiStrip';
import { DistrictBubbleMap } from '../components/admin/DistrictBubbleMap';
import { DistrictTable } from '../components/admin/DistrictTable';
import { ConcernTradeMatrix } from '../components/admin/ConcernTradeMatrix';
import { TrendChart } from '../components/admin/TrendChart';
import { ShiftBars } from '../components/admin/ShiftBars';
import { TopPhrases } from '../components/admin/TopPhrases';
import { BackgroundDoodles } from '../components/BackgroundDoodles';

/**
 * Phase 16 — scheme-administrator resistance dashboard. Shows WHERE resistance
 * concentrates (map + table) and WHY (concern x trade matrix, trend, shift,
 * phrases) with filters, a rule-based action hint, CSV export and the privacy
 * suppression / demo-data notices. The counsellor cohort view (ResistancePage)
 * is untouched.
 */
export const AdminResistancePage: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<ResistanceDashboard | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<DashboardFilters>({});

  const load = useCallback((f: DashboardFilters) => {
    setLoading(true);
    setError('');
    getResistanceDashboard(f)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const states = useMemo(
    () => Array.from(new Set((data?.districts ?? []).map((d) => d.state).filter(Boolean))) as string[],
    [data],
  );
  const trades = data?.matrix.trades ?? [];

  const setFilter = (key: keyof DashboardFilters, value: string) =>
    setFilters((f) => ({ ...f, [key]: value || undefined }));

  const onExport = async () => {
    try {
      const url = await exportResistanceCsv();
      const a = document.createElement('a');
      a.href = url;
      a.download = 'resistance_export.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const suppressed = data && data.suppressed_groups > 0;

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="staff" />

      <div className="relative z-10 mx-auto max-w-5xl space-y-4 p-4 min-h-screen">
      <div className="flex flex-wrap items-center justify-between gap-2 py-2">
        <h1 className="text-2xl font-bold text-accent">{t('admin_dash.title')}</h1>
        <div className="flex items-center gap-3">
          <button type="button" className="btn-secondary text-sm" onClick={onExport}>
            {t('admin_dash.export_csv')}
          </button>
          <Link href="/counsellor" className="text-accent hover:underline text-sm">
            {t('admin_dash.back')}
          </Link>
        </div>
      </div>

      {data?.is_demo && (
        <p role="status" className="rounded bg-amber-100 px-3 py-2 text-sm text-amber-900">
          {t('admin_dash.demo_banner')}
        </p>
      )}

      {/* Filters */}
      <fieldset className="card grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <legend className="sr-only">{t('admin_dash.filters')}</legend>
        <label className="text-sm">
          <span className="text-textSecondary">{t('admin_dash.f_from')}</span>
          <input type="date" className="mt-1 w-full rounded border p-1" value={filters.from ?? ''} onChange={(e) => setFilter('from', e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="text-textSecondary">{t('admin_dash.f_to')}</span>
          <input type="date" className="mt-1 w-full rounded border p-1" value={filters.to ?? ''} onChange={(e) => setFilter('to', e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="text-textSecondary">{t('admin_dash.f_state')}</span>
          <select className="mt-1 w-full rounded border p-1" value={filters.state ?? ''} onChange={(e) => setFilter('state', e.target.value)}>
            <option value="">{t('admin_dash.f_all')}</option>
            {states.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="text-textSecondary">{t('admin_dash.f_trade')}</span>
          <select className="mt-1 w-full rounded border p-1" value={filters.trade ?? ''} onChange={(e) => setFilter('trade', e.target.value)}>
            <option value="">{t('admin_dash.f_all')}</option>
            {trades.map((tr) => (
              <option key={tr} value={tr}>{tr}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="text-textSecondary">{t('admin_dash.f_lang')}</span>
          <select className="mt-1 w-full rounded border p-1" value={filters.lang ?? ''} onChange={(e) => setFilter('lang', e.target.value)}>
            <option value="">{t('admin_dash.f_all')}</option>
            <option value="hi">{t('admin_dash.lang_hi')}</option>
            <option value="en">{t('admin_dash.lang_en')}</option>
          </select>
        </label>
      </fieldset>

      {error && <p role="alert" className="text-red-600">{error}</p>}
      {loading && !data && <p className="text-textSecondary">{t('common.loading')}</p>}

      {data && (
        <>
          <KpiStrip kpis={data.kpis} />
          {suppressed && (
            <p role="status" className="rounded bg-gray-100 px-3 py-2 text-xs text-textSecondary">
              {t('admin_dash.suppressed_notice', { n: data.suppressed_groups })}
            </p>
          )}
          <div className="grid gap-4 lg:grid-cols-2">
            <DistrictBubbleMap districts={data.districts} />
            <TrendChart data={data.trend} />
          </div>
          <DistrictTable districts={data.districts} />
          <ConcernTradeMatrix matrix={data.matrix} />
          <ShiftBars shift={data.shift} />
          <TopPhrases phrases={data.phrases} />
        </>
      )}
      </div>
    </div>
  );
};
