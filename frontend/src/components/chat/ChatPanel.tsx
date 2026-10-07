import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { UserCheck } from 'lucide-react';
import type { ConversationOut, EscalationAck, EscalationPayload } from '../../api/client';
import {
  createConversation,
  escalateConversation,
  getConversation,
  getConversationEscalation,
  sendTurn,
} from '../../api/client';
import { SpeakerToggle, type Speaker } from './SpeakerToggle';
import { MessageBubble, speak } from './MessageBubble';
import { MicButton, micSupported } from './MicButton';
import { ReadAloudToggle } from './ReadAloudToggle';
import { QuickReplies } from './QuickReplies';
import { EscalateSheet } from './EscalateSheet';

interface ChatPanelProps {
  studentId: number;
  /** Bind the shared chat to a family room when opened from one. */
  roomId?: number | null;
  /** Shortlisted trade the objections are about (grounds the fact cards). */
  occupationId?: number | null;
  className?: string;
}

interface QueuedTurn {
  speaker: Speaker;
  text: string;
}

const POLL_MS = 5000;

/**
 * The shared learner + parent chat (PHASE_15). One thread, big speaker
 * switch, voice in / read-aloud out, grounded fact cards, quick replies and
 * an always-visible "Talk to a human" hand-off with live status. Polls every
 * 5 s for counsellor replies and escalation movement; when the network drops
 * turns queue locally and retry on reconnect.
 */
export const ChatPanel: React.FC<ChatPanelProps> = ({ studentId, roomId, occupationId, className }) => {
  const { t, i18n } = useTranslation();
  const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading');
  const [conv, setConv] = useState<ConversationOut | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [speaker, setSpeaker] = useState<Speaker>('learner');
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [queue, setQueue] = useState<QueuedTurn[]>([]);
  const [escalation, setEscalation] = useState<EscalationAck | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [readAloud, setReadAloud] = useState(false);
  const [nudge, setNudge] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const queueRef = useRef<QueuedTurn[]>([]);
  const supportedMic = micSupported();

  useEffect(() => {
    queueRef.current = queue;
  }, [queue]);

  const boot = useCallback(async () => {
    setPhase('loading');
    setError('');
    try {
      const c = await createConversation(studentId, roomId ?? null, i18n.language);
      setConv(c);
      setPhase('ready');
    } catch (e) {
      setError((e as Error).message || t('chat.error_load'));
      setPhase('error');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId, roomId]);

  useEffect(() => {
    boot();
  }, [boot]);

  // Poll the thread (counsellor replies) + the hand-off status.
  useEffect(() => {
    if (!conv) return;
    const id = setInterval(async () => {
      try {
        const fresh = await getConversation(conv.id);
        setConv(fresh);
        if (fresh.status === 'escalated' || escalation) {
          try {
            setEscalation(await getConversationEscalation(conv.id));
          } catch {
            /* not escalated yet — fine */
          }
        }
        // A reachable server is also our cue to drain the offline queue.
        if (queueRef.current.length && navigator.onLine) flushRef.current();
      } catch {
        /* offline: keep the last snapshot, retry on next tick */
      }
    }, POLL_MS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return () => clearInterval(id);
  }, [conv?.id, escalation?.id]);

  const submit = useCallback(
    async (sp: Speaker, text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !conv) return;
      setSending(true);
      setNotice('');
      try {
        const resp = await sendTurn(conv.id, {
          speaker: sp,
          text: trimmed,
          occupation_id: occupationId ?? null,
          lang: i18n.language,
        });
        setDraft('');
        if (resp.escalation_suggested) setNudge(true);
        if (readAloud && resp.reply) speak(resp.reply, resp.lang);
        setConv(await getConversation(conv.id));
        setError('');
      } catch (e) {
        const msg = (e as Error).message || '';
        if (/offline|network|fetch/i.test(msg)) {
          setQueue((q) => [...q, { speaker: sp, text: trimmed }]);
          setDraft('');
          setNotice(t('chat.queued'));
        } else {
          setError(msg || t('common.error'));
        }
      } finally {
        setSending(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [conv, occupationId, readAloud, i18n.language]
  );

  // Replay the offline queue as soon as we are back.
  const flushQueue = useCallback(async () => {
    const pending = queueRef.current;
    if (!pending.length || !conv) return;
    queueRef.current = [];
    setQueue([]);
    for (const item of pending) {
      await submit(item.speaker, item.text);
    }
    setNotice('');
  }, [conv, submit]);

  // The poll interval must call the *latest* flush, not a stale closure.
  const flushRef = useRef(flushQueue);
  useEffect(() => {
    flushRef.current = flushQueue;
  }, [flushQueue]);

  useEffect(() => {
    const onOnline = () => flushRef.current();
    window.addEventListener('online', onOnline);
    return () => window.removeEventListener('online', onOnline);
  }, []);

  useEffect(() => {
    const el = bottomRef.current;
    if (el && typeof el.scrollIntoView === 'function') el.scrollIntoView({ behavior: 'smooth' });
  }, [conv?.turns.length]);

  const handleEscalate = async (payload: EscalationPayload) => {
    if (!conv) return;
    try {
      const ack = await escalateConversation(conv.id, payload);
      setEscalation(ack);
      setSheetOpen(false);
      setConv(await getConversation(conv.id));
    } catch (e) {
      setError((e as Error).message || t('common.error'));
    }
  };

  if (phase === 'loading') {
    return (
      <div className={`card flex items-center justify-center py-10 ${className ?? ''}`}>
        <p role="status" className="text-textSecondary">
          {t('chat.loading')}
        </p>
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div className={`card space-y-3 py-6 text-center ${className ?? ''}`}>
        <p className="text-error">{error || t('chat.error_load')}</p>
        <button type="button" onClick={boot} className="btn-primary">
          {t('chat.retry')}
        </button>
      </div>
    );
  }

  return (
    <div className={`card flex flex-col ${className ?? ''}`} data-testid="chat-panel">
      {/* Header: who is speaking + read-aloud */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 pb-3">
        <h2 className="text-lg font-bold text-accent">{t('chat.title')}</h2>
        <div className="flex items-center gap-2">
          <ReadAloudToggle on={readAloud} onToggle={() => setReadAloud((v) => !v)} />
          <SpeakerToggle value={speaker} onChange={setSpeaker} />
        </div>
      </div>

      {/* Live hand-off status */}
      {escalation && (
        <p
          role="status"
          className="mt-3 rounded-lg bg-green-50 px-3 py-2 text-sm font-semibold text-green-800"
          data-testid="escalation-status"
        >
          <UserCheck className="mr-1 inline h-4 w-4" aria-hidden />
          {t(`chat.status_${escalation.status}`)}
        </p>
      )}
      {notice && (
        <p role="status" className="mt-3 rounded-lg bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
          {notice}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-error">
          {error}
        </p>
      )}

      {/* Messages */}
      <div role="log" aria-live="polite" className="mt-3 max-h-[50vh] min-h-[180px] space-y-3 overflow-y-auto py-2">
        {conv?.turns.map((turn) => (
          <MessageBubble key={turn.id} turn={turn} readAloud={readAloud && turn.speaker === 'assistant'} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Quick replies (the AskBox concerns, in-chat) */}
      <div className="mt-3">
        <QuickReplies onPick={(text) => submit(speaker, text)} />
      </div>

      {/* Voice nudge + always-visible human hand-off */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-textSecondary">
          {nudge ? t('chat.escalate_nudge') : supportedMic ? t('chat.mic_hint') : t('chat.typing_hint')}
        </p>
        <button
          type="button"
          onClick={() => setSheetOpen(true)}
          className="btn-secondary flex min-h-[44px] items-center gap-2 font-bold"
          data-testid="escalate-open"
        >
          <UserCheck className="h-5 w-5" aria-hidden />
          {t('chat.escalate_button')}
        </button>
      </div>

      {/* Composer */}
      <div className="mt-3 flex items-center gap-2">
        <MicButton
          lang={i18n.language}
          onTranscript={(text) => submit(speaker, text)}
        />
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit(speaker, draft);
            }
          }}
          placeholder={t('chat.placeholder')}
          aria-label={t('chat.placeholder')}
          className="input-field flex-1"
        />
        <button
          type="button"
          onClick={() => submit(speaker, draft)}
          disabled={sending || !draft.trim()}
          className="btn-primary min-h-[44px]"
        >
          {t('chat.send')}
        </button>
      </div>

      {sheetOpen && (
        <EscalateSheet
          defaultLang={i18n.language}
          busy={sending}
          onSubmit={handleEscalate}
          onClose={() => setSheetOpen(false)}
        />
      )}
    </div>
  );
};
