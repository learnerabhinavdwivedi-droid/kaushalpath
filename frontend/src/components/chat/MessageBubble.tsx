import React from 'react';
import { useTranslation } from 'react-i18next';
import { Volume2 } from 'lucide-react';
import type { TurnOut } from '../../api/client';
import { FactCard } from './FactCard';

export const speak = (text: string, lang: string) => {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    window.speechSynthesis.speak(utterance);
  }
};

const SPEAKER_LABEL: Record<string, string> = {
  learner: 'chat.learner_badge',
  parent: 'chat.parent_badge',
  counsellor: 'chat.counsellor_badge',
  assistant: 'chat.assistant_badge',
};

interface MessageBubbleProps {
  turn: TurnOut;
  /** Auto read-aloud is on: assistant replies render a speaking indicator. */
  readAloud: boolean;
}

/**
 * One chat message. Family turns (learner / parent) align right; the
 * assistant and the live counsellor align left, with grounded fact cards
 * under the assistant bubble. Icon-only controls carry accessible names
 * (R12 low-literacy affordance).
 */
export const MessageBubble: React.FC<MessageBubbleProps> = ({ turn, readAloud }) => {
  const { t, i18n } = useTranslation();
  const own = turn.speaker === 'learner' || turn.speaker === 'parent';
  const counsellor = turn.speaker === 'counsellor';

  return (
    <div className={`flex ${own ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          own
            ? 'bg-accent text-white'
            : counsellor
              ? 'border-2 border-accent bg-amber-50 text-textMain'
              : 'bg-gray-100 text-textMain'
        }`}
      >
        <p className="mb-1 text-xs font-bold uppercase tracking-wide opacity-70">
          {t(SPEAKER_LABEL[turn.speaker] ?? 'chat.assistant_badge')}
        </p>
        <p className="text-base leading-relaxed">{turn.text}</p>

        {turn.speaker === 'assistant' && turn.facts_json && turn.facts_json.length > 0 && (
          <div className="mt-2 grid gap-2">
            {turn.facts_json.map((f) => (
              <FactCard key={`${turn.id}-${f.key}`} fact={f} />
            ))}
          </div>
        )}

        {turn.speaker === 'assistant' && 'speechSynthesis' in window && (
          <button
            type="button"
            aria-label={t('chat.read_aloud')}
            onClick={() => speak(turn.text, turn.lang || i18n.language)}
            className="mt-2 inline-flex min-h-[44px] items-center gap-1 text-sm font-semibold text-accent"
          >
            <Volume2 className="h-4 w-4" aria-hidden />
            {readAloud ? t('chat.read_aloud_on') : t('chat.read_aloud')}
          </button>
        )}
      </div>
    </div>
  );
};
