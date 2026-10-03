import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'wouter';
import { joinRoom } from '../api/client';
import { useRoomStore } from '../store/useStore';

export const RoomJoinPage: React.FC = () => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const setCode = useRoomStore((s) => s.setCode);
  const [code, setCodeInput] = useState('');
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState('');

  const handleJoin = async () => {
    const trimmed = code.trim().toUpperCase();
    if (!trimmed) return;
    setJoining(true);
    setError('');
    try {
      await joinRoom(trimmed);
      setCode(trimmed);
      setLocation(`/room/${trimmed}`);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setJoining(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-4 max-w-md mx-auto">
      <div className="card space-y-4 mt-8">
        <h1 className="text-2xl font-bold text-accent">{t('room.join_title')}</h1>
        <label className="block">
          <span className="text-base font-medium">{t('room.join_placeholder')}</span>
          <input
            value={code}
            onChange={(e) => setCodeInput(e.target.value)}
            className="input-field mt-1 uppercase"
            autoComplete="off"
            maxLength={12}
          />
        </label>

        {error && <p className="text-error text-base">{error}</p>}

        <button onClick={handleJoin} disabled={joining || !code.trim()} className="btn-primary w-full">
          {joining ? t('room.joining') : t('room.join_button')}
        </button>

        <button onClick={() => setLocation('/')} className="btn-secondary w-full">
          {t('common.back')}
        </button>
      </div>
    </div>
  );
};
