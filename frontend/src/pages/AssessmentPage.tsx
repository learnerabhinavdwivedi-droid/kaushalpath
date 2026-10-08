import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAssessmentStore, useAuthStore, useResultsStore } from '../store/useStore';
import { useLocation } from 'wouter';
import {
  AssessmentItem,
  RecommendationOut,
  getRecommendations,
  resumeSession,
  startSession,
  submitAnswer,
} from '../api/client';
import { QuestionCard } from '../components/QuestionCard';
import { ProgressBar } from '../components/ProgressBar';
import { ArrowLeft } from 'lucide-react';
import { mapRecommendations } from '../lib/mapRecommendations';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

function isRetryable(e: unknown): boolean {
  const msg = e instanceof Error ? e.message.toLowerCase() : String(e).toLowerCase();
  return msg.includes('404') || msg.includes('not found');
}

const INTEREST_EMOJI: Record<number, string> = {
  1: '😞',
  2: '🙁',
  3: '😐',
  4: '🙂',
  5: '😍',
};

function toCardOptions(item: AssessmentItem) {
  if (item.section === 'interest') {
    const scale = item.scale && item.scale.length ? item.scale : [1, 2, 3, 4, 5];
    return scale.map((n) => ({ id: String(n), label: `${INTEREST_EMOJI[n] ?? ''} ${n}` }));
  }
  return (item.options ?? []).map((opt) => ({ id: opt, label: opt }));
}

export const AssessmentPage: React.FC = () => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const studentId = useAuthStore((s) => s.studentId);
  const { assessmentId, setAssessmentId, resetAssessment } = useAssessmentStore();
  const setRecommendations = useResultsStore((s) => s.setRecommendations);

  const [items, setItems] = useState<AssessmentItem[]>([]);
  const [index, setIndex] = useState(0);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const finish = async (sid: number, attempt = 1): Promise<void> => {
    try {
      const res = await getRecommendations(sid, 3);
      if (!res.recommendations || res.recommendations.length === 0) {
        if (attempt <= 3) {
          await sleep(attempt * 1000);
          return await finish(sid, attempt + 1);
        }
      } else {
        setRecommendations(mapRecommendations(res.recommendations));
      }
    } catch (e: unknown) {
      if (attempt <= 3 && isRetryable(e)) {
        await sleep(attempt * 1000);
        return await finish(sid, attempt + 1);
      }
    } finally {
      if (attempt === 1 || attempt > 3) {
        resetAssessment();
        setLocation('/results');
      }
    }
  };

  useEffect(() => {
    if (studentId == null) {
      setLocation('/login');
      return;
    }
    const boot = async () => {
      setLoading(true);
      try {
        const first = assessmentId
          ? await resumeSession(assessmentId)
          : await startSession(studentId);
        setAssessmentId(first.assessment_id);
        if (first.done || !first.item) {
          await finish(studentId);
          return;
        }
        setItems([first.item]);
        setIndex(0);
      } catch (e: any) {
        setError(e.message || t('common.error'));
      } finally {
        setLoading(false);
      }
    };
    if (items.length === 0) boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelect = async (optionId: string) => {
    if (studentId == null || assessmentId == null) return;
    const current = items[index];
    const answer = current.section === 'interest' ? Number(optionId) : optionId;
    setSelections((s) => ({ ...s, [current.id]: optionId }));
    setLoading(true);
    try {
      const next = await submitAnswer(assessmentId, answer, current.id);
      setAssessmentId(next.assessment_id);
      if (next.done || !next.item) {
        await finish(studentId);
        return;
      }
      setItems((prev) => [...prev, next.item as AssessmentItem]);
      setIndex((i) => i + 1);
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 gap-4">
        <p className="text-lg text-red-700">{error}</p>
        <button onClick={() => setLocation('/profile')} className="btn-secondary">
          {t('common.back')}
        </button>
      </div>
    );
  }

  const current = items[index];
  const total = Math.max(items.length, 8);

  return (
    <div className="min-h-screen flex flex-col p-4 max-w-md mx-auto">
      <div className="flex items-center gap-4 py-4">
        <button
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
          disabled={index === 0}
          className="p-2 disabled:opacity-30"
          aria-label={t('common.back')}
        >
          <ArrowLeft className="w-8 h-8 text-accent" />
        </button>
        <div className="flex-1">
          <p className="text-center text-sm font-bold text-textSecondary mb-2">
            {t('assessment.progress', { current: index + 1, total })}
          </p>
          <ProgressBar current={index + 1} total={total} />
        </div>
      </div>

      <div className="flex-1 py-8">
        {loading && !current ? (
          <h2 className="text-2xl font-bold animate-pulse text-accent">{t('common.loading')}</h2>
        ) : current ? (
          <QuestionCard
            questionText={current.text}
            options={toCardOptions(current)}
            onSelect={handleSelect}
            selectedId={selections[current.id]}
            locked={!!selections[current.id]}
          />
        ) : null}
      </div>
    </div>
  );
};

