import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getModelVersion } from '../api/client';

/**
 * Small footer strip showing the serving model version (Phase 8 feedback-loop
 * requirement: users must be able to see *which* model produced their list).
 * Renders nothing when the endpoint is unreachable (offline PWA mode).
 */
export const ModelVersionFooter: React.FC = () => {
  const { t } = useTranslation();
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getModelVersion()
      .then((r) => active && setVersion(r.model_version))
      .catch(() => {
        /* footer is decorative — never block the page on it */
      });
    return () => {
      active = false;
    };
  }, []);

  if (!version) return null;
  return (
    <footer className="text-xs text-textSecondary text-center py-3 print:hidden">
      {t('footer.model_version')}: <span className="font-mono">{version}</span>
    </footer>
  );
};
