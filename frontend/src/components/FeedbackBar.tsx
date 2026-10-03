import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ThumbsUp, CheckCircle2 } from 'lucide-react';
import { sendFeedback } from '../api/client';

interface FeedbackBarProps {
  /** Primary key of the stored recommendation being rated (Phase 8). */
  recommendationId: number | null | undefined;
}

const TOPICS = ['none', 'income', 'security', 'social', 'safety'] as const;

/**
 * "Was this helpful / did you choose it?" strip with the PS 26241
 * sentiment-objection tag. Feeds the feedback table -> retraining export
 * and the counsellor resistance dashboard.
 */
export const FeedbackBar: React.FC<FeedbackBarProps> = ({ recommendationId }) => {
  const { t } = useTranslation();
  const [topic, setTopic] = useState<(typeof TOPICS)[number]>('none');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');

  if (recommendationId == null) return null; // demo/localStorage rows carry no stored id

  const send = async (helpful: boolean, chosen: boolean) => {
    setStatus('sending');
    try {
      await sendFeedback({
        recommendation_id: recommendationId,
        helpful,
        chosen,
        topic,
        sentiment: topic === 'none' ? 'none' : 'concern',
      });
      setStatus('sent');
    } catch {
      setStatus('error');
    }
  };

  if (status === 'sent') {
    return <p className="text-sm text-green-700 font-bold">{t('feedback.thanks')}</p>;
  }

  return (
    <div className="pt-3 border-t border-gray-100 flex flex-wrap items-center gap-2 text-sm">
      <span className="text-textSecondary font-medium">{t('feedback.question')}</span>
      <button
        className="btn-secondary !py-1 !px-3 flex items-center gap-1 disabled:opacity-50"
        onClick={() => send(true, false)}
        disabled={status === 'sending'}
      >
        <ThumbsUp className="w-4 h-4" /> {t('feedback.helpful')}
      </button>
      <button
        className="btn-primary !py-1 !px-3 flex items-center gap-1 disabled:opacity-50"
        onClick={() => send(true, true)}
        disabled={status === 'sending'}
      >
        <CheckCircle2 className="w-4 h-4" /> {t('feedback.chosen')}
      </button>
      <label className="flex items-center gap-1 text-textSecondary">
        {t('feedback.concern')}
        <select
          className="border rounded px-1 py-0.5 bg-white"
          value={topic}
          onChange={(e) => setTopic(e.target.value as (typeof TOPICS)[number])}
        >
          {TOPICS.map((tp) => (
            <option key={tp} value={tp}>
              {t(`feedback.topic_${tp}`)}
            </option>
          ))}
        </select>
      </label>
      {status === 'error' && <span className="text-red-600">{t('feedback.error')}</span>}
    </div>
  );
};
