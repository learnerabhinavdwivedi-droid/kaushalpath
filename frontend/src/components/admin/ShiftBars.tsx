import React from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  shift: { softened: number; hardened: number; unchanged: number };
}

/** Phase 16 — improved / unchanged / worsened distribution bars. */
export const ShiftBars: React.FC<Props> = ({ shift }) => {
  const { t } = useTranslation();
  const rows = [
    { label: t('admin_dash.shift_improved'), count: shift.softened, color: 'bg-green' },
    { label: t('admin_dash.shift_unchanged'), count: shift.unchanged, color: 'bg-accent' },
    { label: t('admin_dash.shift_worsened'), count: shift.hardened, color: 'bg-red-500' },
  ];
  const max = Math.max(1, ...rows.map((r) => r.count));

  return (
    <div className="card">
      <h2 className="mb-3 font-bold text-lg">{t('admin_dash.shift_title')}</h2>
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.label} className="flex items-center gap-2 text-sm">
            <span className="w-28 shrink-0">{r.label}</span>
            <span className={`h-4 rounded ${r.color}`} style={{ width: `${(r.count / max) * 60}%` }} />
            <span className="font-bold">{r.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
