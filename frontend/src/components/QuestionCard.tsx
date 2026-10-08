import React from 'react';
import { useTranslation } from 'react-i18next';
import { Volume2 } from 'lucide-react';

interface QuestionCardProps {
  questionText: string;
  options: { id: string; label: string; icon?: React.ReactNode }[];
  onSelect: (optionId: string) => void;
  selectedId?: string;
  locked?: boolean;
}

const OPTION_COLORS = [
  'bg-gradient-to-r from-rose-50 to-pink-100 hover:from-rose-100 hover:to-pink-200 border-rose-200 text-rose-950',
  'bg-gradient-to-r from-blue-50 to-indigo-100 hover:from-blue-100 hover:to-indigo-200 border-blue-200 text-blue-950',
  'bg-gradient-to-r from-emerald-50 to-teal-100 hover:from-emerald-100 hover:to-teal-200 border-emerald-200 text-emerald-950',
  'bg-gradient-to-r from-amber-50 to-orange-100 hover:from-amber-100 hover:to-orange-200 border-amber-200 text-amber-950',
  'bg-gradient-to-r from-purple-50 to-fuchsia-100 hover:from-purple-100 hover:to-fuchsia-200 border-purple-200 text-purple-950'
];

export const QuestionCard: React.FC<QuestionCardProps> = ({ questionText, options, onSelect, selectedId, locked }) => {
  const { i18n } = useTranslation();

  const speakText = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(questionText);
      utterance.lang = i18n.language === 'hi' ? 'hi-IN' : 'en-US';
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="card space-y-6 bg-white/90 backdrop-blur-sm border-2 border-accent/10 shadow-xl rounded-3xl p-8">
      <div className="flex justify-between items-start gap-4">
        <h2 className="text-3xl font-extrabold text-ink leading-tight">{questionText}</h2>
        {typeof window !== 'undefined' && 'speechSynthesis' in window && (
          <button 
            onClick={speakText} 
            className="p-3 bg-accent-light rounded-full hover:bg-accent hover:text-white transition-colors flex-shrink-0"
            aria-label="Read question aloud"
          >
            <Volume2 className="w-6 h-6" />
          </button>
        )}
      </div>
      
      <div className="space-y-4 pt-4">
        {options.map((opt, index) => {
          const colorClass = OPTION_COLORS[index % OPTION_COLORS.length];
          const isSelected = selectedId === opt.id;
          
          return (
            <button
              key={opt.id}
              onClick={() => onSelect(opt.id)}
              disabled={locked}
              className={`w-full p-5 rounded-2xl text-left border-2 flex items-center gap-5 transition-all duration-300 transform ${
                isSelected 
                  ? 'border-accent shadow-lg scale-[1.02] bg-white ring-4 ring-accent/20' 
                  : `${colorClass} ${locked ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-1 hover:shadow-md'}`
              }`}
            >
              {opt.icon && <span className="text-4xl">{opt.icon}</span>}
              <span className={`text-xl font-bold ${isSelected ? 'text-accent' : ''}`}>{opt.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
