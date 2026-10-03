import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'wouter';
import { AnalyticsResponse, getAnalytics } from '../api/client';
import { BucketChart } from '../components/BucketChart';

export const AnalyticsPage: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getAnalytics().then(setData).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="min-h-screen bg-background p-4 max-w-3xl mx-auto space-y-4">
      <div className="flex justify-between items-center py-2">
        <h1 className="text-2xl font-bold text-accent">{t('analytics.title')}</h1>
        <Link href="/counsellor" className="text-accent hover:underline text-sm">
          {t('analytics.back_cohort')}
        </Link>
      </div>
      {error && <p className="text-red-600">{error}</p>}
      {!data && !error && <p className="text-textSecondary">{t('common.loading')}</p>}

      {data && (
        <>
          <div className="card grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-accent">{data.dropoff.started}</div>
              <div className="text-xs text-textSecondary">{t('analytics.started')}</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-accent">
                {(data.dropoff.dropoff_rate * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-textSecondary">{t('analytics.dropoff')}</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-accent">
                {data.rooms.rooms_created} / {data.rooms.consensus_reached}
              </div>
              <div className="text-xs text-textSecondary">{t('analytics.rooms_consensus')}</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-accent">{data.avg_items.average_items}</div>
              <div className="text-xs text-textSecondary">{t('analytics.avg_items')}</div>
            </div>
          </div>

          <BucketChart
            title={t('analytics.riasec')}
            data={data.riasec.distribution}
            suppressed={data.riasec.suppressed_groups}
          />
          <BucketChart
            title={t('analytics.top_trades')}
            data={data.top_trades.top_trades}
            suppressed={data.top_trades.suppressed_groups}
          />

          <div className="card">
            <h3 className="font-bold text-lg mb-2">{t('analytics.district_mismatch')}</h3>
            {data.district_mismatch.districts.length === 0 ? (
              <p className="text-textSecondary text-sm">{t('analytics.no_data')}</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-textSecondary">
                    <th className="py-1">{t('analytics.district')}</th>
                    <th>{t('analytics.students')}</th>
                    <th>{t('analytics.top_trade')}</th>
                    <th>{t('analytics.recs')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.district_mismatch.districts.map((d) => (
                    <tr key={d.district} className="border-t">
                      <td className="py-2 font-medium">{d.district}</td>
                      <td>{d.n_students}</td>
                      <td>{d.top_trade}</td>
                      <td>{d.recommendations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {data.district_mismatch.suppressed_groups > 0 && (
              <p className="text-xs text-textSecondary mt-2">
                {t('analytics.suppressed', { n: data.district_mismatch.suppressed_groups })}
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
};
