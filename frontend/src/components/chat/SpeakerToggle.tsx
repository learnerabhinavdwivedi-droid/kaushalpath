import React from 'react';
import { useTranslation } from 'react-i18next';
import { GraduationCap, Users } from 'lucide-react';

export type Speaker = 'learner' | 'parent';

interface SpeakerToggleProps {
  value: Speaker;
  onChange: (s: Speaker) => void;
}

/**
 * The big Learner / Parent switch the PS asks for: two 56px icon buttons,
 * every message is tagged by whoever is holding the phone.
 */
export const SpeakerToggle: React.FC<SpeakerToggleProps> = ({ value, onChange }) => {
  const { t } = useTranslation();
  const options: { id: Speaker; label: string; Icon: typeof GraduationCap }[] = [
    { id: 'learner', label: t('chat.speaker_learner'), Icon: GraduationCap },
    { id: 'parent', label: t('chat.speaker_parent'), Icon: Users },
  ];

  return (
    <div role="group" aria-label={t('chat.speaker_label')} className="flex items-center gap-2">
      {options.map(({ id, label, Icon }) => (
        <button
          key={id}
          type="button"
          aria-pressed={value === id}
          onClick={() => onChange(id)}
          className={`flex h-14 w-14 flex-col items-center justify-center rounded-2xl border-2 transition-colors ${
            value === id
              ? 'border-accent bg-accent text-white'
              : 'border-gray-200 bg-white text-textSecondary'
          }`}
        >
          <Icon className="h-6 w-6" aria-hidden />
          <span className="text-[10px] font-bold leading-tight">{label}</span>
        </button>
      ))}
    </div>
  );
};
