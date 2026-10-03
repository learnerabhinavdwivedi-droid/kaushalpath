import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'wouter';
import { ResistanceResponse, getResistance } from '../api/client';
import { BucketChart } from '../components/BucketChart';

export const ResistancePage: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<ResistanceResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getResistance().then(setData).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="min-h-screen bg-background p-4 max-w-3xl mx-auto space-y-4">
      <div className="flex justify-between items-center py-2">
        <h1 className="text-2xl font-bold text-accent">{t('resistance.title')}</h1>
        <Link href="/counsellor" className="text-accent hover:underline text-sm">
          {t('resistance.back_cohort')}
        </Link>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      {!data && !error && <p className="text-textSecondary">{t('common.loading')}</p>}

      {data && (
        <>
          <div className="card text-center">
            <div className="text-2xl font-bold text-accent">{data.total_objections}</div>
            <div className="text-xs text-textSecondary">{t('resistance.total')}</div>
          </div>

          <BucketChart title={t('resistance.by_topic')} data={data.by_topic} color="bg-amber-500" />
          <BucketChart title={t('resistance.concern_by_topic')} data={data.concern_by_topic} color="bg-red-500" />
          <BucketChart title={t('resistance.by_district')} data={data.by_district} />
          <BucketChart title={t('resistance.by_trade')} data={data.by_trade} />

          {data.suppressed_groups > 0 && (
            <p className="text-xs text-textSecondary">{t('analytics.suppressed', { n: data.suppressed_groups })}</p>
          )}
        </>
      )}
    </div>
  );
};
