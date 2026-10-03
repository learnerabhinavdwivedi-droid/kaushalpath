import React from 'react';
import { useTranslation } from 'react-i18next';

interface ConsentBannerProps {
  onAgree: () => void;
  onDisagree: () => void;
}

export const ConsentBanner: React.FC<ConsentBannerProps> = ({ onAgree, onDisagree }) => {
  const { t } = useTranslation();
  
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-surface border-t-4 border-accent p-6 shadow-2xl z-50 animate-slide-up">
      <div className="max-w-md mx-auto space-y-4">
        <h3 className="text-xl font-bold">{t('consent.title')}</h3>
        <p className="text-textSecondary text-lg">{t('consent.description')}</p>
        <div className="flex gap-4 pt-2">
          <button onClick={onAgree} className="btn-primary flex-1">
            {t('consent.agree')}
          </button>
          <button onClick={onDisagree} className="btn-secondary flex-1">
            {t('consent.disagree')}
          </button>
        </div>
      </div>
    </div>
  );
};
