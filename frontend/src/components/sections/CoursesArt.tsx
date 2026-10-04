import React from "react";

/**
 * Placeholder mascot SVGs for the "What We Teach" cards (master rule #2).
 * Rounded blob characters with eyes — swap for real illustrations later.
 */

const eyes = (cx1: number, cx2: number, cy: number, r = 5) => (
  <>
    <circle cx={cx1} cy={cy} r={r + 2} fill="#fff" />
    <circle cx={cx1} cy={cy} r={r} fill="#0A0A0A" />
    <circle cx={cx2} cy={cy} r={r + 2} fill="#fff" />
    <circle cx={cx2} cy={cy} r={r} fill="#0A0A0A" />
  </>
);

const smile = (cx: number, cy: number, w = 22) => (
  <path
    d={`M${cx - w / 2} ${cy} Q${cx} ${cy + 14} ${cx + w / 2} ${cy}`}
    stroke="#0A0A0A"
    strokeWidth="4"
    fill="none"
    strokeLinecap="round"
  />
);

export const BrainBulb: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 200 200" className={className} role="img" aria-label="AI and machine learning mascot">
    <circle cx="100" cy="86" r="58" fill="#0F7B3F" />
    <path d="M74 70 Q86 58 98 70 T122 70 M74 92 Q86 80 98 92 T122 92" stroke="#B7F0C6" strokeWidth="4" fill="none" strokeLinecap="round" />
    {eyes(84, 116, 84)}
    {smile(100, 100)}
    <rect x="86" y="140" width="28" height="18" rx="4" fill="#55554A" />
    <rect x="90" y="158" width="20" height="8" rx="3" fill="#2A2A2A" />
  </svg>
);

export const CourseDrone: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 200 200" className={className} role="img" aria-label="drone mascot">
    <line x1="40" y1="54" x2="160" y2="54" stroke="#0A0A0A" strokeWidth="6" />
    <ellipse cx="42" cy="48" rx="30" ry="8" fill="#0F7B3F" />
    <ellipse cx="158" cy="48" rx="30" ry="8" fill="#0F7B3F" />
    <rect x="64" y="66" width="72" height="58" rx="20" fill="#E23A0C" />
    {eyes(85, 115, 92)}
    {smile(100, 108)}
    <rect x="72" y="124" width="12" height="26" rx="5" fill="#0A0A0A" />
    <rect x="116" y="124" width="12" height="26" rx="5" fill="#0A0A0A" />
  </svg>
);

export const PrintCube: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 200 220" className={className} role="img" aria-label="3D printing mascot">
    {/* rocket */}
    <path d="M100 12 C112 30 112 46 100 60 C88 46 88 30 100 12 Z" fill="#FF4F00" />
    <circle cx="100" cy="42" r="6" fill="#DDB9FB" />
    {/* cube body */}
    <rect x="52" y="70" width="96" height="86" rx="16" fill="#8B5CF6" />
    {eyes(80, 120, 104)}
    {smile(100, 122)}
    {/* printer tray */}
    <rect x="66" y="156" width="68" height="14" rx="4" fill="#2A2A2A" />
    <rect x="72" y="170" width="10" height="24" rx="4" fill="#0A0A0A" />
    <rect x="118" y="170" width="10" height="24" rx="4" fill="#0A0A0A" />
  </svg>
);

export const SkateRobot: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 200 200" className={className} role="img" aria-label="robot mascot">
    <rect x="56" y="46" width="88" height="72" rx="14" fill="#0F7B3F" />
    <rect x="72" y="62" width="56" height="40" rx="8" fill="#B7F0C6" />
    {eyes(90, 110, 82, 4)}
    {smile(100, 94, 18)}
    <rect x="66" y="118" width="68" height="14" rx="4" fill="#2A2A2A" />
    {/* skateboard */}
    <rect x="52" y="150" width="96" height="12" rx="6" fill="#FF4F00" />
    <circle cx="72" cy="170" r="9" fill="#0A0A0A" />
    <circle cx="128" cy="170" r="9" fill="#0A0A0A" />
  </svg>
);

export const MakerBench: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 220 200" className={className} role="img" aria-label="maker camp mascot">
    {/* gears */}
    <circle cx="180" cy="40" r="16" fill="#FF4F00" />
    <circle cx="180" cy="40" r="6" fill="#F1F5E0" />
    <circle cx="40" cy="52" r="12" fill="#FF4F00" />
    <circle cx="40" cy="52" r="5" fill="#F1F5E0" />
    {/* rocket */}
    <path d="M120 24 C130 40 130 54 120 66 C110 54 110 40 120 24 Z" fill="#E23A0C" />
    {/* two little builders */}
    <rect x="52" y="86" width="44" height="46" rx="12" fill="#0F7B3F" />
    {eyes(66, 82, 104, 4)}
    <rect x="120" y="86" width="44" height="46" rx="12" fill="#22A85B" />
    {eyes(134, 150, 104, 4)}
    {/* workbench */}
    <rect x="36" y="132" width="150" height="16" rx="4" fill="#55554A" />
    <rect x="48" y="148" width="12" height="34" fill="#2A2A2A" />
    <rect x="162" y="148" width="12" height="34" fill="#2A2A2A" />
  </svg>
);

export const COURSE_MASCOTS = {
  "brain-bulb": BrainBulb,
  drone: CourseDrone,
  "print-cube": PrintCube,
  "skate-robot": SkateRobot,
  "maker-bench": MakerBench,
} as const;
