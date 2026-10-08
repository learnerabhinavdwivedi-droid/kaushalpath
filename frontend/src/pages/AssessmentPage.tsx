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
import { ArrowLeft, Sparkles, Star, Lightbulb, Puzzle, Compass, Target, Rocket } from 'lucide-react';
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
          return finish(sid, attempt + 1);
        }
      } else {
        setRecommendations(mapRecommendations(res.recommendations));
      }
    } catch (e: unknown) {
      if (attempt <= 3 && isRetryable(e)) {
        await sleep(attempt * 1000);
        return finish(sid, attempt + 1);
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
    <div className="relative min-h-screen bg-page overflow-hidden">
      {/* Background Doodles for empty space on large screens */}
      <div className="hidden lg:block absolute inset-0 pointer-events-none">
        <Sparkles className="absolute top-20 left-[12%] w-16 h-16 text-lavender opacity-80 animate-pulse" />
        <Star className="absolute top-[30%] left-[6%] w-12 h-12 text-orange opacity-50 transform -rotate-12" />
        <Lightbulb className="absolute bottom-[25%] left-[10%] w-24 h-24 text-yellow-500 opacity-60" />
        <Target className="absolute top-1/2 left-[5%] w-14 h-14 text-green opacity-40 animate-bounce" style={{ animationDuration: '4s' }} />

        <Rocket className="absolute top-24 right-[10%] w-20 h-20 text-accent opacity-60 transform rotate-45" />
        <Puzzle className="absolute bottom-[30%] right-[8%] w-16 h-16 text-pink-500 opacity-70" />
        <Compass className="absolute top-1/2 right-[12%] w-28 h-28 text-blue-400 opacity-50 animate-[spin_12s_linear_infinite]" />
        <Star className="absolute bottom-16 right-[18%] w-10 h-10 text-orange-deep opacity-60" />
        
        {/* Soft Glassmorphism Color Blobs */}
        <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-lavender/30 rounded-full mix-blend-multiply filter blur-[80px] opacity-70"></div>
        <div className="absolute -top-20 right-0 w-[400px] h-[400px] bg-orange/20 rounded-full mix-blend-multiply filter blur-[80px] opacity-70"></div>
        <div className="absolute -bottom-40 left-1/3 w-[600px] h-[600px] bg-accent-light/40 rounded-full mix-blend-multiply filter blur-[100px] opacity-70"></div>
      </div>

      <div className="relative z-10 flex flex-col p-4 sm:p-6 lg:p-8 max-w-2xl mx-auto min-h-screen">
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
    </div>
  );
};

