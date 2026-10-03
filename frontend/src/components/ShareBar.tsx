import React from 'react';
import { useTranslation } from 'react-i18next';

interface ShareBarProps {
  choiceName: string;
}

// Export via the browser's print-to-PDF (print stylesheet renders the room in
// the chosen language) plus a WhatsApp text link. No server PDF dependency.
export const ShareBar: React.FC<ShareBarProps> = ({ choiceName }) => {
  const { t } = useTranslation();
  const summary = t('share.summary', { choice: choiceName });
  const waHref = `https://wa.me/?text=${encodeURIComponent(summary)}`;

  return (
    <div className="card no-print flex flex-wrap gap-3 items-center">
      <span className="font-bold mr-auto">{t('share.title')}</span>
      <button onClick={() => window.print()} className="btn-secondary">
        {t('share.print')}
      </button>
      <a
        href={waHref}
        target="_blank"
        rel="noopener noreferrer"
        className="btn-primary no-underline"
      >
        {t('share.whatsapp')}
      </a>
    </div>
  );
};
