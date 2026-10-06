import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { DistrictRow } from '../../api/client';
import { suggestAction } from '../../lib/resistance';

type SortKey = 'district' | 'n' | 'avg_rs' | 'share_high';

/** Phase 16 — sortable district table with the rule-based suggested action. */
export const DistrictTable: React.FC<{ districts: DistrictRow[] }> = ({ districts }) => {
  const { t } = useTranslation();
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: 'avg_rs', dir: -1 });

  const rows = useMemo(() => {
    const copy = [...districts];
    copy.sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (typeof av === 'string' && typeof bv === 'string') {
        return sort.dir * av.localeCompare(bv);
      }
      const an = (av as number | null) ?? -1;
      const bn = (bv as number | null) ?? -1;
      return sort.dir * (an - bn);
    });
    return copy;
  }, [districts, sort]);

  const toggle = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 1 ? -1 : 1 } : { key, dir: -1 }));

  const header = (key: SortKey, label: string) => (
    <th scope="col" className="text-left">
      <button
        type="button"
        onClick={() => toggle(key)}
        className="font-semibold text-textSecondary hover:text-accent"
        aria-label={`${label} (${t('admin_dash.sort')})`}
      >
        {label}
        {sort.key === key ? (sort.dir === 1 ? ' ▲' : ' ▼') : ''}
      </button>
    </th>
  );

  const fmt = (v: number | null) => (v == null ? '—' : v.toFixed(2));

  return (
    <div className="card overflow-x-auto">
      <h2 className="mb-3 font-bold text-lg">{t('admin_dash.table_title')}</h2>
      {rows.length === 0 ? (
        <p className="text-sm text-textSecondary">{t('admin_dash.empty')}</p>
      ) : (
        <table className="w-full text-sm">
          <caption className="sr-only">{t('admin_dash.table_title')}</caption>
          <thead>
            <tr className="border-b">
              {header('district', t('admin_dash.col_district'))}
              <th scope="col" className="text-left font-semibold text-textSecondary">{t('admin_dash.col_state')}</th>
              {header('n', t('admin_dash.col_families'))}
              {header('avg_rs', t('admin_dash.col_avg_rs'))}
              {header('share_high', t('admin_dash.col_high'))}
              <th scope="col" className="text-left font-semibold text-textSecondary">{t('admin_dash.col_action')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.district} className="border-b last:border-0">
                <th scope="row" className="py-1.5 text-left font-medium">
                  {d.district}
                  {d.is_suppressed && (
                    <span className="ml-2 rounded bg-gray-200 px-1.5 py-0.5 text-xs text-textSecondary">
                      {t('admin_dash.suppressed')}
                    </span>
                  )}
                </th>
                <td className="py-1.5">{d.state ?? '—'}</td>
                <td className="py-1.5">{d.n}</td>
                <td className="py-1.5">{fmt(d.avg_rs)}</td>
                <td className="py-1.5">{d.share_high == null ? '—' : `${Math.round(d.share_high * 100)}%`}</td>
                <td className="py-1.5 text-textSecondary">{t(suggestAction(d))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
