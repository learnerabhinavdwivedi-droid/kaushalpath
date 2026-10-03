import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'wouter';
import { useAuthStore } from '../store/useStore';
import { getMe } from '../api/client';

interface RequireRoleProps {
  roles: string[];
  children: React.ReactNode;
}

/**
 * Role-based route guard (Phase 8). The backend enforces these same rules —
 * this only prevents rendering an authorised-looking screen for the wrong role.
 * On a hard reload the persisted role may be stale, so a missing role is
 * resolved once via /auth/me before deciding.
 */
export const RequireRole: React.FC<RequireRoleProps> = ({ roles, children }) => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const token = useAuthStore((s) => s.token);
  const storedRole = useAuthStore((s) => s.role);
  const setAuth = useAuthStore((s) => s.setAuth);
  const [resolved, setResolved] = useState<string | null>(storedRole);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    if (!token) {
      setLocation('/login');
      return;
    }
    if (storedRole) {
      setResolved(storedRole);
      return;
    }
    let active = true;
    setChecking(true);
    getMe()
      .then((me) => {
        if (!active) return;
        setAuth(token, me.role, me.student_id);
        setResolved(me.role);
      })
      .catch(() => active && setLocation('/login'))
      .finally(() => active && setChecking(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, storedRole]);

  if (checking) return <div className="p-8 text-center text-textSecondary">{t('common.loading')}</div>;

  if (!token || !resolved || !roles.includes(resolved)) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-6 text-center">
        <h1 className="text-2xl font-bold text-accent">{t('guard.denied_title')}</h1>
        <p className="text-textSecondary">{t('guard.denied_body')}</p>
        <button className="btn-secondary" onClick={() => setLocation('/')}>
          {t('guard.back_home')}
        </button>
      </div>
    );
  }

  return <>{children}</>;
};
