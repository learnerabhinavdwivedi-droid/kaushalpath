import React from 'react';
import { useTranslation } from 'react-i18next';

/** Phase 16 — anonymised top phrases (escalation notes) grouped per concern. */
export const TopPhrases: React.FC<{ phrases: Record<string, string[]> }> = ({ phrases }) => {
  const { t } = useTranslation();
  const entries = Object.entries(phrases).filter(([, list]) => list.length > 0);

  return (
    <div className="card">
      <h2 className="mb-1 font-bold text-lg">{t('admin_dash.phrases_title')}</h2>
      <p className="mb-3 text-xs text-textSecondary">{t('admin_dash.phrases_hint')}</p>
      {entries.length === 0 ? (
        <p className="text-sm text-textSecondary">{t('admin_dash.empty')}</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {entries.map(([con, list]) => (
            <section key={con} aria-labelledby={`phrases-${con}`}>
              <h3 id={`phrases-${con}`} className="mb-1 text-sm font-semibold text-accent">
                {t(`admin_dash.topic_${con}`)}
              </h3>
              <ul className="list-disc space-y-1 pl-5 text-sm text-textSecondary">
                {list.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
};
