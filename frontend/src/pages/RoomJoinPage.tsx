import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'wouter';
import { guestJoin, joinRoom } from '../api/client';
import { useAuthStore, useRoomStore } from '../store/useStore';
import { BackgroundDoodles } from '../components/BackgroundDoodles';

export const RoomJoinPage: React.FC = () => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const setCode = useRoomStore((s) => s.setCode);
  const setAuth = useAuthStore((s) => s.setAuth);
  const token = useAuthStore((s) => s.token);
  const [code, setCodeInput] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState('');

  const trimmed = () => code.trim().toUpperCase();

  // Registered family (student / parent with an account): plain membership join.
  const handleJoin = async () => {
    if (!trimmed()) return;
    setJoining(true);
    setError('');
    try {
      await joinRoom(trimmed());
      setCode(trimmed());
      setLocation(`/room/${trimmed()}`);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setJoining(false);
    }
  };

  // Phase 15 guest path: room code + first name (+ optional phone). No email,
  // no password — the backend issues a 24 h room-bound parent token.
  const handleGuestJoin = async () => {
    if (!trimmed() || !name.trim()) return;
    setJoining(true);
    setError('');
    try {
      const guest = await guestJoin(trimmed(), name.trim(), phone.trim() || undefined);
      setAuth(guest.access_token, 'parent', null);
      setCode(guest.room_code);
      setLocation(`/room/${guest.room_code}`);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setJoining(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="room" />

      <div className="relative z-10 p-4 max-w-md mx-auto">
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

        {token ? (
          <>
            {error && <p className="text-error text-base">{error}</p>}
            <button onClick={handleJoin} disabled={joining || !code.trim()} className="btn-primary w-full">
              {joining ? t('room.joining') : t('room.join_button')}
            </button>
          </>
        ) : (
          <>
            <hr className="border-gray-100" />
            <h2 className="text-lg font-bold">{t('room.guest_title')}</h2>
            <label className="block">
              <span className="text-base font-medium">{t('room.guest_name')}</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field mt-1"
                autoComplete="name"
                maxLength={60}
              />
            </label>
            <label className="block">
              <span className="text-base font-medium">{t('room.guest_phone')}</span>
              <input
                type="tel"
                inputMode="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="input-field mt-1"
                autoComplete="tel"
              />
            </label>
            {error && <p className="text-error text-base">{error}</p>}
            <button
              onClick={handleGuestJoin}
              disabled={joining || !code.trim() || !name.trim()}
              className="btn-primary w-full"
            >
              {joining ? t('room.joining') : t('room.join_guest')}
            </button>
            <p className="text-sm text-textSecondary">
              <a href="/login" className="link-underline">
                {t('room.guest_has_account')}
              </a>
            </p>
          </>
        )}

        <button onClick={() => setLocation('/')} className="btn-secondary w-full">
          {t('common.back')}
        </button>
      </div>
      </div>
    </div>
  );
};
