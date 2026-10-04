import React from "react";

/**
 * Placeholder SVG characters (rounded blobs with eyes) — see master rule #2.
 * These stand in for the reference mascots and are meant to be swapped later.
 * Each is a self-contained, transparent-background SVG so it can be animated
 * independently (inline in the H1 or as a parallax layer in the hero art).
 */

const eye = (cx: number, cy: number, r = 3) => (
  <>
    <circle cx={cx} cy={cy} r={r + 2} fill="#fff" />
    <circle cx={cx} cy={cy} r={r} fill="#0A0A0A" />
  </>
);

/* ---------- Inline H1 mascots (sized to ~0.9em by the caller) ---------- */

export const InlineDrone: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 64 64" className={className} role="img" aria-label="drone mascot">
    <line x1="12" y1="16" x2="52" y2="16" stroke="#0A0A0A" strokeWidth="3" />
    <ellipse cx="14" cy="14" rx="10" ry="3" fill="#0F7B3F" />
    <ellipse cx="50" cy="14" rx="10" ry="3" fill="#0F7B3F" />
    <rect x="22" y="20" width="20" height="18" rx="7" fill="#FF4F00" />
    {eye(28, 29, 2.4)}
    {eye(36, 29, 2.4)}
    <path d="M28 34 Q32 37 36 34" stroke="#0A0A0A" strokeWidth="2" fill="none" strokeLinecap="round" />
  </svg>
);

export const InlineBulb: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 64 64" className={className} role="img" aria-label="idea mascot">
    <circle cx="32" cy="26" r="16" fill="#0F7B3F" />
    <rect x="26" y="40" width="12" height="8" rx="2" fill="#55554A" />
    {eye(27, 24, 2.6)}
    {eye(37, 24, 2.6)}
    <path d="M27 31 Q32 35 37 31" stroke="#0A0A0A" strokeWidth="2" fill="none" strokeLinecap="round" />
  </svg>
);

/* ---------- Right-column hero group (separate layers for parallax) ---------- */

export const GreenDrone: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 160 160" className={className} role="img" aria-label="green drone character">
    <line x1="24" y1="44" x2="136" y2="44" stroke="#0A0A0A" strokeWidth="5" />
    <ellipse cx="26" cy="40" rx="22" ry="6" fill="#0F7B3F" />
    <ellipse cx="134" cy="40" rx="22" ry="6" fill="#0F7B3F" />
    <circle cx="80" cy="92" r="40" fill="#22A85B" />
    {eye(66, 86, 5)}
    {eye(94, 86, 5)}
    <path d="M64 104 Q80 118 96 104" stroke="#0A0A0A" strokeWidth="4" fill="none" strokeLinecap="round" />
  </svg>
);

export const OrangeCube: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 160 220" className={className} role="img" aria-label="robot with idea tree">
    {/* tree canopy */}
    <circle cx="80" cy="46" r="40" fill="#0F7B3F" />
    <rect x="74" y="76" width="12" height="24" fill="#55554A" />
    {/* bulb */}
    <circle cx="80" cy="70" r="14" fill="#F5D400" />
    {/* body */}
    <rect x="40" y="96" width="80" height="86" rx="18" fill="#FF4F00" />
    {eye(64, 130, 5)}
    {eye(96, 130, 5)}
    <path d="M64 150 Q80 162 96 150" stroke="#0A0A0A" strokeWidth="4" fill="none" strokeLinecap="round" />
    {/* legs */}
    <rect x="54" y="182" width="14" height="20" rx="6" fill="#0A0A0A" />
    <rect x="92" y="182" width="14" height="20" rx="6" fill="#0A0A0A" />
  </svg>
);

export const PurpleRobot: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 160 180" className={className} role="img" aria-label="waving robot">
    <line x1="80" y1="18" x2="80" y2="40" stroke="#0A0A0A" strokeWidth="4" />
    <circle cx="80" cy="14" r="6" fill="#DDB9FB" />
    <rect x="36" y="40" width="88" height="96" rx="22" fill="#8B5CF6" />
    {eye(62, 78, 5)}
    {eye(98, 78, 5)}
    <path d="M62 98 Q80 110 98 98" stroke="#0A0A0A" strokeWidth="4" fill="none" strokeLinecap="round" />
    {/* waving arm */}
    <rect x="120" y="48" width="16" height="44" rx="8" fill="#8B5CF6" transform="rotate(28 128 70)" />
    <circle cx="140" cy="40" r="10" fill="#fff" />
    {/* legs */}
    <rect x="52" y="136" width="16" height="26" rx="7" fill="#0A0A0A" />
    <rect x="92" y="136" width="16" height="26" rx="7" fill="#0A0A0A" />
  </svg>
);

export const CircuitBoard: React.FC<{ className?: string }> = ({ className }) => (
  <svg viewBox="0 0 220 90" className={className} role="img" aria-label="circuit board">
    <rect x="4" y="4" width="212" height="82" rx="10" fill="#0F7B3F" />
    <g stroke="#B7F0C6" strokeWidth="3" fill="none">
      <path d="M28 24 H96 V60 H170" />
      <path d="M40 70 H120 V40 H196" />
    </g>
    <g fill="#F5D400">
      <circle cx="28" cy="24" r="5" />
      <circle cx="170" cy="60" r="5" />
      <circle cx="196" cy="40" r="5" />
    </g>
  </svg>
);
