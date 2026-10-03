import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'wouter';

export const LandingPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center space-y-8 max-w-md mx-auto">
      <div className="space-y-4">
        <h1 className="text-4xl font-bold text-accent">{t('landing.title')}</h1>
        <p className="text-xl text-textSecondary">{t('landing.subtitle')}</p>
      </div>
      
      <div className="w-full space-y-4 pt-8">
        <Link href="/register" className="btn-primary w-full text-center block leading-[3rem] no-underline">
          {t('landing.start_button')}
        </Link>
        <Link href="/login" className="btn-secondary w-full text-center block leading-[3rem] no-underline">
          {t('landing.login_button')}
        </Link>
      </div>
    </div>
  );
};
