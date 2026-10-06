import React from 'react';
import { useTranslation } from 'react-i18next';
import type { ConcernTradeMatrix as Matrix } from '../../api/client';

/** Phase 16 — concern x trade heat matrix. Suppressed cells (k<5) show a dot. */
export const ConcernTradeMatrix: React.FC<{ matrix: Matrix }> = ({ matrix }) => {
  const { t } = useTranslation();
  const { concerns, trades, cells } = matrix;

  const max = Math.max(1, ...cells.flat().map((c) => c ?? 0));
  const bg = (v: number | null) => {
    if (v == null) return '#F3F4F6';
    const a = 0.15 + 0.7 * (v / max);
    return `rgba(220, 38, 38, ${a.toFixed(2)})`;
  };

  return (
    <div className="card overflow-x-auto">
      <h2 className="mb-1 font-bold text-lg">{t('admin_dash.matrix_title')}</h2>
      <p className="mb-3 text-xs text-textSecondary">{t('admin_dash.matrix_hint')}</p>
      {concerns.length === 0 || trades.length === 0 ? (
        <p className="text-sm text-textSecondary">{t('admin_dash.empty')}</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">{t('admin_dash.matrix_title')}</caption>
          <thead>
            <tr>
              <th scope="col" className="p-1 text-left font-semibold text-textSecondary">
                {t('admin_dash.matrix_concern')}
              </th>
              {trades.map((tr) => (
                <th key={tr} scope="col" className="max-w-20 truncate p-1 text-center font-semibold text-textSecondary">
                  {tr}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {concerns.map((con, r) => (
              <tr key={con}>
                <th scope="row" className="p-1 text-left font-medium">
                  {t(`admin_dash.topic_${con}`)}
                </th>
                {trades.map((tr, c) => {
                  const v = cells[r][c];
                  return (
                    <td
                      key={tr}
                      className="p-1 text-center"
                      style={{ background: bg(v) }}
                      title={v == null ? t('admin_dash.suppressed') : `${con} × ${tr}: ${v}`}
                    >
                      {v == null ? '·' : v}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
