import React from "react";
import { Link } from "wouter";
import { cn } from "../../lib/cn";

const WAVE_BG =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='16' viewBox='0 0 120 16'%3E%3Cpath d='M0,8 Q15,0 30,8 T60,8 T90,8 T120,8 L120,16 L0,16 Z' fill='%23FF4F00'/%3E%3C/svg%3E\")";

const BASE =
  "group relative inline-flex h-[60px] min-w-[265px] items-center justify-center overflow-hidden rounded-full bg-ink px-8 " +
  "focus:outline-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-orange-deep focus-visible:ring-offset-[3px]";

/**
 * Primary marketing CTA: black pill with an orange crest that rises to fill on
 * hover (CSS transform only, crest animation disabled under reduced motion).
 * Anchor hrefs stay plain `<a>` (in-page scroll); app routes use wouter `<Link>`
 * so navigation does not reload the SPA.
 */
export const WaveButton: React.FC<{
  label: string;
  href: string;
  className?: string;
}> = ({ label, href, className }) => {
  const content = (
    <>
      <span className="absolute inset-x-0 bottom-0 h-full translate-y-[44px] transition-transform duration-[400ms] ease-out group-hover:translate-y-0">
        <span
          className="hero-wave-crest absolute inset-x-0 bottom-full h-4"
          style={{
            backgroundImage: WAVE_BG,
            backgroundRepeat: "repeat-x",
            backgroundSize: "120px 16px",
            animation: "wave-scroll 6s linear infinite",
          }}
        />
        <span className="absolute inset-0 bg-orange" />
      </span>
      <span className="relative z-10 font-mono text-lg font-bold text-white transition-colors duration-[400ms] group-hover:text-ink">
        {label}
      </span>
    </>
  );

  return href.startsWith("#") ? (
    <a href={href} className={cn(BASE, className)}>
      {content}
    </a>
  ) : (
    <Link href={href} className={cn(BASE, className)}>
      {content}
    </Link>
  );
};

export default WaveButton;
