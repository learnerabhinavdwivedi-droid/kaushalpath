import React from 'react';

interface ProgressBarProps {
  current: number;
  total: number;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ current, total }) => {
  const percentage = Math.max(0, Math.min(100, (current / total) * 100));
  
  return (
    <div className="w-full bg-gray-200 rounded-full h-4 dark:bg-gray-700" aria-label={`Progress: ${current} of ${total}`}>
      <div 
        className="bg-accent h-4 rounded-full transition-all duration-300 ease-in-out" 
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
};
