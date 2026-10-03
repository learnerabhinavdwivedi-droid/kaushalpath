import React from 'react';

export const LoadingSkeleton: React.FC = () => {
  return (
    <div className="card space-y-4 animate-pulse">
      <div className="h-8 bg-gray-300 rounded w-3/4"></div>
      <div className="h-4 bg-gray-300 rounded w-full"></div>
      <div className="h-4 bg-gray-300 rounded w-5/6"></div>
      <div className="flex gap-2 pt-4">
        <div className="h-8 bg-gray-300 rounded-full w-24"></div>
        <div className="h-8 bg-gray-300 rounded-full w-24"></div>
      </div>
    </div>
  );
};
