import React from 'react';
import { useTranslation } from 'react-i18next';
import { Volume2, VolumeX } from 'lucide-react';

interface ReadAloudToggleProps {
  on: boolean;
  onToggle: () => void;
}

/**
 * Panel-level read-aloud switch. When on, every new assistant reply is
 * spoken (speechSynthesis, the same engine the career cards use). Browsers
 * without the API simply do not get the control.
 */
export const ReadAloudToggle: React.FC<ReadAloudToggleProps> = ({ on, onToggle }) => {
  const { t } = useTranslation();
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return null;

  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={t('chat.read_aloud')}
      onClick={onToggle}
      className={`flex min-h-[44px] items-center gap-2 rounded-full border-2 px-4 text-sm font-bold ${
        on ? 'border-accent bg-accent-light text-accent' : 'border-gray-200 bg-white text-textSecondary'
      }`}
    >
      {on ? <Volume2 className="h-5 w-5" aria-hidden /> : <VolumeX className="h-5 w-5" aria-hidden />}
      {t('chat.read_aloud')}
    </button>
  );
};
