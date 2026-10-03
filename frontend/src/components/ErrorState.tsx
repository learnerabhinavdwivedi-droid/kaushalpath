import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ message, onRetry }) => {
  const { t } = useTranslation();
  
  return (
    <div className="flex flex-col items-center justify-center p-8 space-y-4 text-center">
      <AlertTriangle className="w-16 h-16 text-error" />
      <h3 className="text-2xl font-bold text-gray-900">{t('common.error')}</h3>
      <p className="text-lg text-textSecondary">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary mt-4">
          {t('common.retry')}
        </button>
      )}
    </div>
  );
};
