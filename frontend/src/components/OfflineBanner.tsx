import React from 'react';
import { useTranslation } from 'react-i18next';
import { useOnline } from '../hooks/useOnline';
import { WifiOff } from 'lucide-react';

/**
 * Phase 17 — a clear, always-visible offline notice. Low-bandwidth families
 * must understand that cached facts and quick replies still work without a
 * connection; this banner tells them so in plain language.
 */
export const OfflineBanner: React.FC = () => {
  const { t } = useTranslation();
  const online = useOnline();
  if (online) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-center text-sm font-medium text-ink"
    >
      <WifiOff className="h-4 w-4" aria-hidden="true" />
      {t('offline.banner')}
    </div>
  );
};
