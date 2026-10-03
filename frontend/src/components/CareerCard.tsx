import React from 'react';
import { useTranslation } from 'react-i18next';
import { ReasonChip } from './ReasonChip';
import { SourceBadge } from './SourceBadge';
import { Volume2, ChevronRight } from 'lucide-react';
import { Link } from 'wouter';

interface CareerCardProps {
  career: any; // Ideally typed with Career/Recommendation schema
}

export const CareerCard: React.FC<CareerCardProps> = ({ career }) => {
  const { t, i18n } = useTranslation();
  
  const speakText = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(`${career.occupation.title}. ${career.reasons.map((r:any)=>r.description).join('. ')}`);
      utterance.lang = i18n.language === 'hi' ? 'hi-IN' : 'en-US';
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="card space-y-4 hover:border-accent transition-colors">
      <div className="flex justify-between items-start">
        <h3 className="text-xl font-bold text-accent">{career.occupation.title}</h3>
        <div className="flex gap-2 items-center">
          <SourceBadge isDemo={true} />
          {typeof window !== 'undefined' && 'speechSynthesis' in window && (
            <button 
              onClick={speakText} 
              className="p-2 bg-gray-100 rounded-full hover:bg-gray-200"
              aria-label="Read career aloud"
            >
              <Volume2 className="w-5 h-5 text-accent" />
            </button>
          )}
        </div>
      </div>
      
      <p className="text-textSecondary">{career.occupation.description}</p>
      
      <div className="flex flex-wrap gap-2 mt-4">
        {career.reasons.slice(0,3).map((r: any, idx: number) => (
          <ReasonChip key={idx} reason={r} />
        ))}
      </div>
      
      <div className="pt-4 border-t border-gray-100 mt-4 flex justify-end">
        <Link href={`/career/${career.occupation.id}`} className="text-accent font-bold flex items-center gap-1 hover:underline p-2 -mr-2">
          {t('results.view_details')} <ChevronRight className="w-5 h-5" />
        </Link>
      </div>
    </div>
  );
};
