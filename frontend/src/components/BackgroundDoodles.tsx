import React, { useMemo } from 'react';
import { 
  Sparkles, Star, Lightbulb, Puzzle, Compass, Target, Rocket, 
  BookOpen, Brain, Briefcase, GraduationCap, Telescope, Shapes,
  UserPlus, Laptop, Zap, ShieldCheck
} from 'lucide-react';

interface Doodle {
  id: number;
  Icon: React.ElementType;
  top: string;
  left: string;
  size: number;
  color: string;
  delay: string;
  duration: string;
  animation: string;
  rotation: string;
}

const SECTION_ICONS: Record<string, React.ElementType[]> = {
  assessment: [Target, Puzzle, Lightbulb, Sparkles, Brain, Compass, Shapes],
  auth: [ShieldCheck, UserPlus, Zap, Rocket, Star, Telescope],
  results: [GraduationCap, Briefcase, Laptop, BookOpen, Target, Rocket],
  default: [Star, Sparkles, Compass, Shapes, Puzzle]
};

const COLORS = ['text-orange', 'text-lavender', 'text-green', 'text-accent', 'text-pink-400', 'text-yellow-400', 'text-blue-400'];
const ANIMATIONS = ['animate-pulse', 'animate-bounce', 'animate-spin-slow', 'animate-float'];

// Custom float animation will require a quick addition to index.css or tailwind.config,
// but pulse/bounce/spin are built-in. Let's use custom classes where possible or standard ones.
// We'll add custom float keyframes to index.css later.

export const BackgroundDoodles: React.FC<{ section?: 'assessment' | 'auth' | 'results' | 'default' }> = ({ section = 'default' }) => {
  const doodles = useMemo(() => {
    const icons = SECTION_ICONS[section] || SECTION_ICONS.default;
    const items: Doodle[] = [];
    
    // Generate 12-15 random doodles
    const count = 12;
    for (let i = 0; i < count; i++) {
      const Icon = icons[Math.floor(Math.random() * icons.length)];
      // Avoid placing right in the middle center where the main content usually is
      // We push them to the edges (0-20% and 80-100% on X axis, scattered on Y)
      const isLeft = Math.random() > 0.5;
      const left = isLeft ? `${Math.floor(Math.random() * 25)}%` : `${75 + Math.floor(Math.random() * 20)}%`;
      const top = `${Math.floor(Math.random() * 90)}%`;
      
      items.push({
        id: i,
        Icon,
        left,
        top,
        size: Math.floor(Math.random() * 40) + 24, // 24px to 64px
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        delay: `${(Math.random() * 2).toFixed(2)}s`,
        duration: `${3 + Math.random() * 4}s`,
        animation: ANIMATIONS[Math.floor(Math.random() * ANIMATIONS.length)],
        rotation: `rotate-${Math.floor(Math.random() * 45)}`
      });
    }
    return items;
  }, [section]);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      {doodles.map(d => (
        <div 
          key={d.id} 
          className={`absolute ${d.animation} opacity-40`}
          style={{ 
            left: d.left, 
            top: d.top, 
            animationDelay: d.delay,
            animationDuration: d.animation === 'animate-spin-slow' ? '12s' : d.duration
          }}
        >
          <d.Icon 
            style={{ width: d.size, height: d.size, transform: `rotate(${Math.floor(Math.random() * 360)}deg)` }} 
            className={d.color} 
          />
        </div>
      ))}
      
      {/* Soft Glassmorphism Color Blobs to blend background smoothly */}
      <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-lavender/20 rounded-full mix-blend-multiply filter blur-[80px] opacity-60"></div>
      <div className="absolute -bottom-40 right-0 w-[600px] h-[600px] bg-orange/10 rounded-full mix-blend-multiply filter blur-[100px] opacity-60"></div>
    </div>
  );
};
