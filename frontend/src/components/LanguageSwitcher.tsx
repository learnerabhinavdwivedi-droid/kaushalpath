import React from 'react';
import { useTranslation } from 'react-i18next';

export const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === 'en' ? 'hi' : 'en');
  };

  return (
    <button 
      onClick={toggleLanguage}
      className="btn-secondary min-h-[44px] min-w-[44px] p-2 text-sm"
      aria-label="Toggle language"
    >
      {i18n.language === 'en' ? 'हिंदी' : 'English'}
    </button>
  );
};
