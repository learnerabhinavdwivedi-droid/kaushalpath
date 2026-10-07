import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useResultsStore, useAuthStore } from '../store/useStore';
import { CareerCard } from '../components/CareerCard';
import { Link } from 'wouter';
import { Settings as SettingsIcon } from 'lucide-react';
import { getRecommendations } from '../api/client';
import { mapRecommendations } from '../lib/mapRecommendations';

export const ResultsPage: React.FC = () => {
  const { t } = useTranslation();
  const { recommendations, setRecommendations } = useResultsStore();
  const studentId = useAuthStore((s) => s.studentId);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (recommendations.length > 0 || studentId == null) return;
    setFetching(true);
    getRecommendations(studentId, 3)
      .then(res => {
        if (res.recommendations?.length > 0) {
          setRecommendations(mapRecommendations(res.recommendations));
        }
      })
      .catch(() => { /* empty state */ })
      .finally(() => setFetching(false));
  }, [recommendations.length, studentId, setRecommendations]);

  return (
    <div className="min-h-screen bg-background p-4 max-w-md mx-auto">
      <div className="flex justify-between items-center py-4 mb-4">
        <h2 className="text-2xl font-bold text-accent">{t('results.title')}</h2>
        <Link href="/settings" className="p-2 hover:bg-gray-200 rounded-full" aria-label="Settings">
          <SettingsIcon className="w-6 h-6 text-textSecondary" />
        </Link>
      </div>

      {fetching ? (
        <div className="card text-center p-8">
          <p className="text-lg text-accent animate-pulse">{t('results.generating', 'Generating your recommendations...')}</p>
        </div>
      ) : recommendations.length === 0 ? (
        <div className="card text-center p-8">
          <p className="text-lg text-textSecondary">{t('results.no_results')}</p>
          <Link href="/assessment" className="btn-primary mt-4 inline-flex">
            {t('assessment.start')}
          </Link>
        </div>
      ) : (
        <div className="space-y-6 pb-20">
          {recommendations.slice(0, 3).map((rec: any, idx: number) => (
            <CareerCard key={idx} career={rec} />
          ))}
        </div>
      )}

      <div className="card mt-6 flex flex-col gap-3">
        <Link href="/room/new" className="btn-primary">
          {t('room.create_button')}
        </Link>
        <Link href="/room/join" className="btn-secondary">
          {t('room.join_button')}
        </Link>
      </div>
    </div>
  );
};
