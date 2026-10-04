import React from "react";
import { site } from "../../content/site";

/**
 * Infinite marquee strip between sections (Phase 8): mono 700 uppercase words
 * separated by orange dots, paused on hover. Pure CSS animation (transform
 * only); disabled under prefers-reduced-motion via the media query in index.css.
 */
const Row: React.FC<{ k: number; words: string[] }> = ({ k, words }) => (
  <div className="flex shrink-0 items-center">
    {words.map((w) => (
      <span
        key={`${k}-${w}`}
        className="flex items-center font-mono text-4xl font-bold uppercase tracking-[0.06em] text-ink md:text-5xl"
      >
        <span className="px-8">{w}</span>
        <span className="text-orange">·</span>
      </span>
    ))}
  </div>
);

export const Marquee: React.FC<{ words?: string[] }> = ({ words = site.marquee }) => (
  <div
    className="marquee-group select-none overflow-hidden border-y-2 border-ink/10 bg-cardwhite py-6"
    aria-hidden
  >
    <div className="marquee-track flex w-max">
      <Row k={0} words={words} />
      <Row k={1} words={words} />
    </div>
  </div>
);

export default Marquee;
