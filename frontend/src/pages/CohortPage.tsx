import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'wouter';
import { CohortRow, getCohort } from '../api/client';
import { LanguageSwitcher } from '../components/LanguageSwitcher';

interface Filters {
  district: string;
  edu_level: string;
  language: string;
  status: string;
}

const EMPTY: Filters = { district: '', edu_level: '', language: '', status: '' };

export const CohortPage: React.FC = () => {
  const { t } = useTranslation();
  const [rows, setRows] = useState<CohortRow[]>([]);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const cleaned = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v)
      ) as Record<string, string>;
      setRows(await getCohort(cleaned));
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (k: keyof Filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFilters((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="min-h-screen bg-background p-4 max-w-3xl mx-auto">
      <div className="flex justify-between items-center py-4 mb-4">
        <h1 className="text-2xl font-bold text-accent">{t('cohort.title')}</h1>
        <LanguageSwitcher />
      </div>

      <div className="card grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <input className="input-field" placeholder={t('cohort.filter_district')} value={filters.district} onChange={set('district')} />
        <input className="input-field" placeholder={t('cohort.filter_edu')} value={filters.edu_level} onChange={set('edu_level')} />
        <select className="input-field" value={filters.language} onChange={set('language')}>
          <option value="">{t('cohort.filter_language')}</option>
          <option value="en">en</option>
          <option value="hi">hi</option>
        </select>
        <select className="input-field" value={filters.status} onChange={set('status')}>
          <option value="">{t('cohort.filter_status')}</option>
          <option value="assessed">{t('cohort.status_assessed')}</option>
          <option value="pending_assessment">{t('cohort.status_pending')}</option>
        </select>
      </div>

      <nav className="flex gap-3 mb-4 text-sm">
        <Link href="/counsellor/analytics" className="text-accent hover:underline">{t('cohort.nav_analytics')}</Link>
        <Link href="/counsellor/resistance" className="text-accent hover:underline">{t('cohort.nav_resistance')}</Link>
        <Link href="/counsellor/audit" className="text-accent hover:underline">{t('cohort.nav_audit')}</Link>
        <Link href="/counsellor/requests" className="text-accent hover:underline">Requests</Link>
      </nav>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {loading ? (
        <p className="text-textSecondary">{t('common.loading')}</p>
      ) : rows.length === 0 ? (
        <div className="card text-center py-8 text-textSecondary">{t('cohort.empty')}</div>
      ) : (
        <div className="space-y-3">
          {rows.map((r) => (
            <Link key={r.student_id} href={`/counsellor/students/${r.student_id}`} className="card block hover:border-accent transition-colors">
              <div className="flex justify-between items-center">
                <div>
                  <span className="font-bold text-accent">#{r.student_id}</span>
                  <span className="ml-2 text-textSecondary">{r.district} · {r.edu_level} · {r.language}</span>
                </div>
                <span className={r.status === 'assessed' ? 'text-green-600 text-sm font-bold' : 'text-amber-600 text-sm font-bold'}>
                  {r.status === 'assessed' ? t('cohort.status_assessed') : t('cohort.status_pending')}
                </span>
              </div>
              <div className="flex gap-4 mt-2 text-sm text-textSecondary">
                {r.has_room && <span>{t('cohort.has_room')}</span>}
                {r.open_escalations > 0 && <span className="text-red-600">{t('cohort.escalations')}: {r.open_escalations}</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};
