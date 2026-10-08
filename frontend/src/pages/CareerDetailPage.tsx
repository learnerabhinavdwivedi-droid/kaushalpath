import React from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useRoute } from 'wouter';
import { useResultsStore } from '../store/useStore';
import { ReasonChip } from '../components/ReasonChip';
import { SourceBadge } from '../components/SourceBadge';
import { AskBox } from '../components/AskBox';
import { ArrowLeft, Volume2 } from 'lucide-react';
import { BackgroundDoodles } from '../components/BackgroundDoodles';

export const CareerDetailPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [, setLocation] = useLocation();
  const [match, params] = useRoute('/career/:id');
  const recommendations = useResultsStore(state => state.recommendations);
  
  if (!match) return null;

  const careerId = params?.id;
  const career = recommendations.find((r: any) => String(r.occupation.id) === String(careerId));

  if (!career) {
    return (
      <div className="p-8 text-center">
        <p className="text-xl">{t('common.error')}</p>
        <button onClick={() => setLocation('/results')} className="btn-secondary mt-4">
          {t('common.back')}
        </button>
      </div>
    );
  }

  const speakText = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(`${career.occupation.title}. ${career.reasons.map((r:any)=>r.description).join('. ')}`);
      utterance.lang = i18n.language === 'hi' ? 'hi-IN' : 'en-US';
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="career" />

      <div className="relative z-10 p-4 max-w-md mx-auto pb-20">
      <div className="flex items-center gap-4 py-4 mb-6">
        <button onClick={() => setLocation('/results')} className="p-2" aria-label="Back">
          <ArrowLeft className="w-8 h-8 text-accent" />
        </button>
      </div>

      <div className="card space-y-6">
        <div className="flex justify-between items-start">
          <h2 className="text-3xl font-bold text-accent">{career.occupation.title}</h2>
          <div className="flex gap-2">
            <SourceBadge isDemo={career.is_demo ?? true} />
            {typeof window !== 'undefined' && 'speechSynthesis' in window && (
              <button 
                onClick={speakText} 
                className="p-2 bg-gray-100 rounded-full hover:bg-gray-200"
                aria-label="Read career aloud"
              >
                <Volume2 className="w-6 h-6 text-accent" />
              </button>
            )}
          </div>
        </div>

        <p className="text-lg text-textSecondary">{career.occupation.description}</p>
        
        <div className="bg-gray-50 p-4 rounded-lg flex justify-between">
          <div>
            <p className="text-sm text-gray-500 font-bold uppercase">{t('profile.duration')}</p>
            <p className="font-semibold text-lg">
              {career.occupation.typical_duration_months
                ? t('career.duration', { months: career.occupation.typical_duration_months })
                : '—'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 font-bold uppercase">{t('career.salary').split('/')[0]}</p>
            <p className="font-semibold text-lg text-green-700">{t('career.salary', { salary: '25,000' })}</p>
          </div>
        </div>

        <div>
          <h3 className="font-bold text-xl mb-4">{t('career.reasons')}</h3>
          <div className="flex flex-col gap-3">
            {career.reasons.map((r: any, idx: number) => (
              <ReasonChip key={idx} reason={r} />
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <AskBox careerTitle={career.occupation.title} />
      </div>
      </div>
    </div>
  );
};
