import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAssessmentStore, useProfileStore, useResultsStore } from '../store/useStore';
import { useLocation } from 'wouter';
import { apiRequest } from '../api/client';
import { QuestionCard } from '../components/QuestionCard';
import { ProgressBar } from '../components/ProgressBar';
import { ArrowLeft } from 'lucide-react';

export const AssessmentPage: React.FC = () => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const { answers, currentQuestionIndex, setAnswer, nextQuestion, prevQuestion } = useAssessmentStore();
  const setRecommendations = useResultsStore(state => state.setRecommendations);
  const profile = useProfileStore();

  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<any[]>([]);

  useEffect(() => {
    // Fetch initial questions
    const fetchQuestions = async () => {
      try {
        const res: any = await apiRequest('/assessment/next-question', {
          method: 'POST',
          body: JSON.stringify({ answers })
        });
        if (res.is_complete) {
          submitAssessment();
        } else {
          setQuestions([res.question]);
        }
      } catch (e) {
        console.error(e);
      }
    };
    if (questions.length === 0) fetchQuestions();
  }, []);

  const submitAssessment = async () => {
    setLoading(true);
    try {
      const res: any = await apiRequest('/recommend', {
        method: 'POST',
        body: JSON.stringify({
          student_id: 1, // Mocked until auth provides me
          answers,
          budget_limit: profile.budget,
          max_duration_months: profile.duration
        })
      });
      setRecommendations(res.recommendations);
      setLocation('/results');
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  const handleSelect = async (optId: string) => {
    const qId = questions[currentQuestionIndex].id;
    setAnswer(qId, optId);
    
    // Simulate next question fetch from API
    try {
      const res: any = await apiRequest('/assessment/next-question', {
        method: 'POST',
        body: JSON.stringify({ answers: { ...answers, [qId]: optId } })
      });
      
      if (res.is_complete) {
        submitAssessment();
      } else {
        setQuestions([...questions, res.question]);
        nextQuestion();
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <h2 className="text-2xl font-bold animate-pulse text-accent">{t('common.loading')}</h2>
      </div>
    );
  }

  const currentQ = questions[currentQuestionIndex];
  if (!currentQ) return null;

  return (
    <div className="min-h-screen flex flex-col p-4 max-w-md mx-auto">
      <div className="flex items-center gap-4 py-4">
        <button onClick={prevQuestion} disabled={currentQuestionIndex === 0} className="p-2 disabled:opacity-30">
          <ArrowLeft className="w-8 h-8 text-accent" />
        </button>
        <div className="flex-1">
          <p className="text-center text-sm font-bold text-textSecondary mb-2">
            {t('assessment.progress', { current: currentQuestionIndex + 1, total: Math.max(15, questions.length) })}
          </p>
          <ProgressBar current={currentQuestionIndex + 1} total={15} />
        </div>
      </div>

      <div className="flex-1 py-8">
        <QuestionCard 
          questionText={currentQ.text}
          options={currentQ.options}
          onSelect={handleSelect}
          selectedId={answers[currentQ.id]}
        />
      </div>
    </div>
  );
};
