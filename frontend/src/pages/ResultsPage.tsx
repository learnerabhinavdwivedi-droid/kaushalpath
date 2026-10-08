import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useResultsStore, useAuthStore, useRoomStore } from '../store/useStore';
import { CareerCard } from '../components/CareerCard';
import { Link, useLocation } from 'wouter';
import { Settings as SettingsIcon } from 'lucide-react';
import { getRecommendations, createRoom } from '../api/client';
import { mapRecommendations } from '../lib/mapRecommendations';
import { BackgroundDoodles } from '../components/BackgroundDoodles';

export const ResultsPage: React.FC = () => {
  const { t } = useTranslation();
  const { recommendations, setRecommendations } = useResultsStore();
  const studentId = useAuthStore((s) => s.studentId);
  const role = useAuthStore((s) => s.role);
  const setCode = useRoomStore((s) => s.setCode);
  const [, setLocation] = useLocation();
  const [fetching, setFetching] = useState(false);
  const [creatingRoom, setCreatingRoom] = useState(false);

  const handleCreateRoom = async () => {
    if (role !== 'student') return;
    setCreatingRoom(true);
    try {
      const room = await createRoom();
      setCode(room.code);
      setLocation(`/room/${room.code}`);
    } catch (e: any) {
      alert(e.message || t('common.error'));
    } finally {
      setCreatingRoom(false);
    }
  };

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
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="results" />

      <div className="relative z-10 min-h-screen bg-transparent p-4 max-w-xl mx-auto">
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
        {role === 'student' && (
          <button onClick={handleCreateRoom} disabled={creatingRoom} className="btn-primary">
            {creatingRoom ? t('room.creating', 'Creating...') : t('room.create_button')}
          </button>
        )}
        <Link href="/room/join" className="btn-secondary">
          {t('room.join_button')}
        </Link>
      </div>
    </div>
    </div>
  );
};
