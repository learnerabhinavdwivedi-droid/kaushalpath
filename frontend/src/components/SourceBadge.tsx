import React from 'react';
import { useTranslation } from 'react-i18next';
import { Database } from 'lucide-react';

interface SourceBadgeProps {
  isDemo?: boolean;
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({ isDemo }) => {
  const { t } = useTranslation();
  
  if (!isDemo) return null;
  
  return (
    <span className="inline-flex items-center gap-1 px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-semibold">
      <Database className="w-4 h-4" />
      {t('results.demo_badge')}
    </span>
  );
};
