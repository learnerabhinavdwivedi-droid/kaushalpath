import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'wouter';
import { Bot } from 'lucide-react';

let activeFabCount = 0;

export const HelpFab: React.FC = () => {
  const [location] = useLocation();
  const [isLeader, setIsLeader] = useState(false);

  useEffect(() => {
    activeFabCount++;
    if (activeFabCount === 1) {
      setIsLeader(true);
    }
    return () => {
      activeFabCount--;
    };
  }, []);

  // Only show on room pages (not in assessment, register, login, results, etc.)
  if (!location.startsWith('/room')) {
    return null;
  }

  // Prevent duplicate rendering if mounted both in App.tsx and Layout.tsx
  if (!isLeader && activeFabCount > 1) {
    return null;
  }

  return (
    <Link
      id="help-fab"
      href="/help"
      className="fixed right-5 bottom-5 z-50 flex items-center group cursor-pointer focus:outline-none no-underline"
      aria-label="Help and FAQ"
    >
      <div className="relative flex items-center justify-center">
        {/* Ambient Glow */}
        <div className="absolute inset-0 bg-accent/20 rounded-full blur-lg scale-125 group-hover:bg-accent/30 transition-all duration-300" />

        {/* Speech Bubble */}
        <div className="absolute bottom-full right-0 mb-2 bg-white px-3 py-1.5 rounded-2xl rounded-br-none shadow-md border border-gray-100 whitespace-nowrap animate-float pointer-events-none">
          <p className="font-bold text-accent text-xs sm:text-sm">Have any doubt, ask me! 🤖✨</p>
        </div>

        {/* Bouncing Robot Badge */}
        <div className="relative bg-white border-4 border-accent p-3 sm:p-3.5 rounded-full shadow-xl animate-bounce group-hover:scale-105 transition-transform">
          <Bot size={32} className="text-accent" />
        </div>
      </div>
    </Link>
  );
};
