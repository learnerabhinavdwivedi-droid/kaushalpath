import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'wouter';
import { AuditEntry, getAuditLog } from '../api/client';
import { BackgroundDoodles } from '../components/BackgroundDoodles';

export const AuditPage: React.FC = () => {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAuditLog()
      .then(setEntries)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="staff" />

      <div className="relative z-10 p-4 max-w-3xl mx-auto space-y-4 min-h-screen">
      <div className="flex justify-between items-center py-2">
        <h1 className="text-2xl font-bold text-accent">{t('audit.title')}</h1>
        <Link href="/counsellor" className="text-accent hover:underline text-sm">
          {t('audit.back_cohort')}
        </Link>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      {loading && <p className="text-textSecondary">{t('common.loading')}</p>}

      {!loading && !error && (
        <div className="card">
          {entries.length === 0 ? (
            <p className="text-textSecondary text-sm">{t('audit.empty')}</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {entries.map((e) => (
                <li key={e.id} className="border-b border-gray-100 pb-2">
                  <div className="flex justify-between">
                    <span className="font-bold text-accent">{t(`audit.action_${e.action}`)}</span>
                    <span className="text-textSecondary">{e.created_at}</span>
                  </div>
                  <div className="text-textSecondary">
                    {e.entity_type}
                    {e.entity_id ? ` #${e.entity_id}` : ''}
                    {e.actor_user_id != null ? ` · ${t('audit.actor')} #${e.actor_user_id}` : ''}
                  </div>
                  {e.detail && (
                    <pre className="mt-1 bg-gray-50 rounded p-2 text-xs overflow-x-auto">
                      {JSON.stringify(e.detail, null, 2)}
                    </pre>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      </div>
    </div>
  );
};
