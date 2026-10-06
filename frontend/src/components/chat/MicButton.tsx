import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Mic, MicOff } from 'lucide-react';

type RecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onresult: ((event: any) => void) | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
};
type RecognitionCtor = new () => RecognitionLike;

const getCtor = (): RecognitionCtor | null => {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as {
    SpeechRecognition?: RecognitionCtor;
    webkitSpeechRecognition?: RecognitionCtor;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
};

/** True when the browser exposes the Web Speech API (jsdom in tests: false). */
export const micSupported = (): boolean => getCtor() !== null;

interface MicButtonProps {
  /** App language ('hi' | 'en'); mapped to the BCP-47 locale for recognition. */
  lang: string;
  onTranscript: (text: string) => void;
}

/**
 * Voice input (R12): tap, speak, tap again. On browsers without
 * SpeechRecognition the button hides itself — the ChatPanel then shows a
 * typing hint so low-literacy users are never stranded (typing always works).
 */
export const MicButton: React.FC<MicButtonProps> = ({ lang, onTranscript }) => {
  const { t } = useTranslation();
  const [listening, setListening] = useState(false);
  const recRef = useRef<RecognitionLike | null>(null);
  const supported = micSupported();

  useEffect(() => () => recRef.current?.stop(), []);

  if (!supported) return null;

  const toggle = () => {
    if (listening) {
      recRef.current?.stop();
      setListening(false);
      return;
    }
    const Ctor = getCtor();
    if (!Ctor) return;
    const rec = new Ctor();
    rec.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (event) => {
      const text = event?.results?.[0]?.[0]?.transcript ?? '';
      if (text.trim()) onTranscript(text.trim());
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  return (
    <button
      type="button"
      aria-label={listening ? t('chat.mic_listening') : t('chat.mic_start')}
      onClick={toggle}
      className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
        listening
          ? 'animate-pulse border-error bg-error text-white'
          : 'border-gray-200 bg-white text-accent'
      }`}
    >
      {listening ? <MicOff className="h-6 w-6" aria-hidden /> : <Mic className="h-6 w-6" aria-hidden />}
    </button>
  );
};
