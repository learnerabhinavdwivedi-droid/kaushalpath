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
    <div className="card space-y-6">
      <div className="flex justify-between items-start">
        <h2 className="text-2xl font-bold">{questionText}</h2>
        {typeof window !== 'undefined' && 'speechSynthesis' in window && (
          <button 
            onClick={speakText} 
            className="p-3 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors"
            aria-label="Read question aloud"
          >
            <Volume2 className="w-6 h-6 text-accent" />
          </button>
        )}
      </div>
      
      <div className="space-y-4">
        {options.map((opt) => (
          <button
            key={opt.id}
            onClick={() => onSelect(opt.id)}
            disabled={locked}
            className={`w-full p-4 rounded-xl text-left border-2 flex items-center gap-4 transition-colors ${
              selectedId === opt.id 
                ? 'border-accent bg-accent-light' 
                : 'border-gray-200 hover:border-accent-light hover:bg-gray-50'
            } ${locked ? 'opacity-60 cursor-not-allowed' : ''}`}
          >
            {opt.icon && <span className="text-3xl">{opt.icon}</span>}
            <span className="text-xl font-medium">{opt.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
