import React from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface ReasonChipProps {
  reason: {
    code: string;
    description: string;
    type?: 'positive' | 'negative' | 'neutral';
    grade?: string;
  };
}

export const ReasonChip: React.FC<ReasonChipProps> = ({ reason }) => {
  const isNegative = reason.type === 'negative' || reason.code === 'APTITUDE_GAP';
  const isPositive = reason.type === 'positive' || (!reason.type && !isNegative);

  return (
    <div
      className={`inline-flex items-start gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
        isNegative
          ? 'bg-amber-100 text-amber-900 border border-amber-200'
          : isPositive
          ? 'bg-green-100 text-green-900 border border-green-200'
          : 'bg-gray-100 text-gray-800 border border-gray-200'
      }`}
    >
      {isPositive ? (
        <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-green-600" />
      ) : (
        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
      )}
      <div className="flex flex-col gap-0.5">
        <span className="leading-snug">{reason.description}</span>
        {reason.grade && (
          <span className="text-[11px] font-semibold text-gray-600 uppercase">
            Evidence Grade {reason.grade}
          </span>
        )}
      </div>
    </div>
  );
};
