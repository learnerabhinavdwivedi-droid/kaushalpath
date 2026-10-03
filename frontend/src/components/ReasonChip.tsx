import React from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface ReasonChipProps {
  reason: {
    code: string;
    description: string;
    type: 'positive' | 'negative' | 'neutral';
  };
}

export const ReasonChip: React.FC<ReasonChipProps> = ({ reason }) => {
  const isPositive = reason.type === 'positive';
  
  return (
    <div className={`inline-flex items-start gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
      isPositive ? 'bg-green-100 text-green-900' : 
      reason.type === 'negative' ? 'bg-red-100 text-red-900' : 'bg-gray-100 text-gray-800'
    }`}>
      {isPositive ? (
        <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5 text-green-600" />
      ) : (
        <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-red-600" />
      )}
      <span>{reason.description}</span>
    </div>
  );
};
