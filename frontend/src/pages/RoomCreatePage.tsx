import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'wouter';
import { createRoom } from '../api/client';
import { useAuthStore, useRoomStore } from '../store/useStore';
import { BackgroundDoodles } from '../components/BackgroundDoodles';

export const RoomCreatePage: React.FC = () => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const role = useAuthStore((s) => s.role);
  const setCode = useRoomStore((s) => s.setCode);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      const room = await createRoom();
      setCode(room.code);
      setLocation(`/room/${room.code}`);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="room" />

      <div className="relative z-10 p-4 max-w-md mx-auto">
      <div className="card space-y-4 mt-8">
        <h1 className="text-2xl font-bold text-accent">{t('room.create_title')}</h1>
        <p className="text-textSecondary text-lg">{t('room.create_subtitle')}</p>

        {role !== 'student' && (
          <p className="text-error text-base">{t('room.no_candidates')}</p>
        )}

        {error && <p className="text-error text-base">{error}</p>}

        <button
          onClick={handleCreate}
          disabled={creating || role !== 'student'}
          className="btn-primary w-full"
        >
          {creating ? t('room.creating') : t('room.create_button')}
        </button>

        <button onClick={() => setLocation('/results')} className="btn-secondary w-full">
          {t('common.back')}
        </button>
      </div>
      </div>
    </div>
  );
};
