import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, Link } from 'wouter';
import { getMe, type MeOut } from '../api/client';
import { useAuthStore } from '../store/useStore';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { ChatPanel } from '../components/chat/ChatPanel';

/**
 * /talk — the single shared family chat outside a room (PHASE_15). The
 * learner starts it after their assessment; a parent joins the same thread
 * from the family room. Judges land here from the product CTAs.
 */
export const TalkPage: React.FC = () => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const token = useAuthStore((s) => s.token);
  const [me, setMe] = useState<MeOut | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setLocation('/login');
      return;
    }
    getMe().then(setMe).catch((e) => setError(e.message || t('common.error')));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="min-h-screen bg-background p-4 max-w-2xl mx-auto">
      <div className="flex items-center justify-between py-2 mb-2">
        <h1 className="text-2xl font-bold text-accent">{t('chat.title')}</h1>
        <LanguageSwitcher />
      </div>

      {error && <p className="text-error mb-4">{error}</p>}

      {!me ? (
        !error && (
          <p role="status" className="card py-10 text-center text-textSecondary">
            {t('chat.loading')}
          </p>
        )
      ) : me.student_id ? (
        <ChatPanel studentId={me.student_id} />
      ) : (
        // A parent without a room of their own: point them at the code join.
        <div className="card space-y-3 py-8 text-center">
          <p className="text-lg">{t('chat.parent_no_room')}</p>
          <Link href="/room/join" className="btn-primary inline-block">
            {t('room.join_title')}
          </Link>
        </div>
      )}

      <p className="mt-4 text-center">
        <Link href="/room/join" className="link-underline text-textSecondary">
          {t('chat.join_family_room')}
        </Link>
      </p>
    </div>
  );
};
