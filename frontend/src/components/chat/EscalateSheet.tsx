import React, { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { EscalationPayload } from '../../api/client';

interface EscalateSheetProps {
  defaultLang: string;
  busy: boolean;
  onSubmit: (payload: EscalationPayload) => void;
  onClose: () => void;
}

/**
 * Bottom sheet for the always-visible "Talk to a human" button (PS R8):
 * phone, best time, language — one tap to send. The reason is the shared
 * conversation itself; the counsellor receives the full Phase 14 case pack.
 */
export const EscalateSheet: React.FC<EscalateSheetProps> = ({
  defaultLang,
  busy,
  onSubmit,
  onClose,
}) => {
  const { t } = useTranslation();
  const [phone, setPhone] = useState('');
  const [slot, setSlot] = useState('morning');
  const [lang, setLang] = useState(defaultLang === 'hi' ? 'hi' : 'en');
  const titleRef = useRef<HTMLHeadingElement>(null);

  React.useEffect(() => titleRef.current?.focus(), []);

  const send = () => {
    onSubmit({
      reason: t('chat.escalate_reason'),
      contact_phone: phone.trim() || null,
      preferred_slot: slot,
      preferred_language: lang,
      channel: 'callback',
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="escalate-sheet-title"
    >
      <div
        className="w-full max-w-lg rounded-t-3xl bg-white p-6 pb-8"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="escalate-sheet-title"
          ref={titleRef}
          tabIndex={-1}
          className="text-xl font-bold text-accent outline-none"
        >
          {t('chat.escalate_title')}
        </h2>

        <label className="mt-4 block">
          <span className="text-base font-medium">{t('chat.phone_label')}</span>
          <input
            type="tel"
            inputMode="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="input-field mt-1"
            autoComplete="tel"
          />
        </label>

        <label className="mt-4 block">
          <span className="text-base font-medium">{t('chat.slot_label')}</span>
          <select value={slot} onChange={(e) => setSlot(e.target.value)} className="input-field mt-1">
            <option value="morning">{t('chat.slot_morning')}</option>
            <option value="afternoon">{t('chat.slot_afternoon')}</option>
            <option value="evening">{t('chat.slot_evening')}</option>
          </select>
        </label>

        <label className="mt-4 block">
          <span className="text-base font-medium">{t('chat.lang_label')}</span>
          <select value={lang} onChange={(e) => setLang(e.target.value)} className="input-field mt-1">
            <option value="hi">{t('chat.lang_hi')}</option>
            <option value="en">{t('chat.lang_en')}</option>
          </select>
        </label>

        <div className="mt-6 flex gap-3">
          <button type="button" onClick={onClose} className="btn-secondary flex-1">
            {t('chat.escalate_cancel')}
          </button>
          <button
            type="button"
            onClick={send}
            disabled={busy}
            data-testid="escalate-send"
            className="btn-primary flex-1"
          >
            {t('chat.escalate_send')}
          </button>
        </div>
      </div>
    </div>
  );
};
