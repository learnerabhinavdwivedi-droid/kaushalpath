import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Volume2, Square } from 'lucide-react';

/**
 * Phase 17 — audio-first affordance. A single "Read this screen" control that
 * speaks the visible text of the current page via the Web Speech API. Mounted
 * once in the app shell so every route gets it without duplicating buttons —
 * the core low-literacy feature the PS asks us to make measurable.
 */
export const ReadThisScreen: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [speaking, setSpeaking] = useState(false);

  if (typeof window !== 'undefined' && !('speechSynthesis' in window)) return null;

  const stop = () => {
    window.speechSynthesis.cancel();
    setSpeaking(false);
  };

  const read = () => {
    const main = document.querySelector('main') ?? document.body;
    const text = (main.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 4000);
    if (!text) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = i18n.language === 'hi' ? 'hi-IN' : 'en-US';
    u.rate = 0.95;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  };

  return (
    <button
      type="button"
      onClick={speaking ? stop : read}
      aria-pressed={speaking}
      className="fixed bottom-4 left-4 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-white shadow-lg"
      aria-label={speaking ? t('a11y.read_stop') : t('a11y.read_screen')}
      title={speaking ? t('a11y.read_stop') : t('a11y.read_screen')}
    >
      {speaking ? <Square className="h-5 w-5" aria-hidden="true" /> : <Volume2 className="h-5 w-5" aria-hidden="true" />}
    </button>
  );
};
