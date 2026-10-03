import React from 'react';
import { useTranslation } from 'react-i18next';
import { useResultsStore } from '../store/useStore';
import { CareerCard } from '../components/CareerCard';
import { Link } from 'wouter';
import { Settings as SettingsIcon } from 'lucide-react';

export const ResultsPage: React.FC = () => {
  const { t } = useTranslation();
  const { recommendations } = useResultsStore();

  return (
    <div className="min-h-screen bg-background p-4 max-w-md mx-auto">
      <div className="flex justify-between items-center py-4 mb-4">
        <h2 className="text-2xl font-bold text-accent">{t('results.title')}</h2>
        <Link href="/settings" className="p-2 hover:bg-gray-200 rounded-full" aria-label="Settings">
          <SettingsIcon className="w-6 h-6 text-textSecondary" />
        </Link>
      </div>

      {recommendations.length === 0 ? (
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
