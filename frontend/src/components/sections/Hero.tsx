import React, { useRef, useState } from "react";
import { motion, useReducedMotion, useScroll, useTransform, type Variants } from "framer-motion";
import { ArrowDown } from "lucide-react";
import { site, type HeroSegment } from "../../content/site";
import {
  InlineDrone,
  InlineBulb,
  GreenDrone,
  OrangeCube,
  PurpleRobot,
  CircuitBoard,
} from "./HeroArt";
import { WaveButton } from "../ui/WaveButton";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

const word: Variants = {
  hidden: { y: 40, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { duration: 0.6, ease: EASE } },
};

const mascotPop: Variants = {
  hidden: { scale: 0, rotate: -12, opacity: 0 },
  show: { scale: 1, rotate: 0, opacity: 1, transition: { type: "spring", stiffness: 260, damping: 18 } },
};

const InlineMascot: React.FC<{ name: NonNullable<HeroSegment["mascot"]> }> = ({ name }) => {
  const Svg = name === "drone" ? InlineDrone : InlineBulb;
  return (
    <motion.span
      variants={mascotPop}
      aria-hidden
      className="mx-[0.12em] inline-block h-[0.9em] w-[0.9em] align-middle"
    >
      <motion.span
        className="block h-full w-full"
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        whileHover={{ scale: 1.15, rotate: [-8, 8, 0] }}
      >
        <Svg className="h-full w-full" />
      </motion.span>
    </motion.span>
  );
};

const ExploreLink: React.FC<{ label: string; href: string }> = ({ label, href }) => (
  <a href={href} className="group inline-flex items-center gap-2 font-mono text-[17px] font-semibold text-ink">
    <span className="relative">
      {label}
      <span className="absolute -bottom-1 left-0 h-[2px] w-full origin-left bg-orange transition-colors duration-300 group-hover:bg-ink" />
    </span>
    <ArrowDown size={18} className="transition-transform duration-300 group-hover:translate-y-1" />
  </a>
);

/** A parallax + idle-float layer for the right-column characters. */
const Layer: React.FC<{
  depth: number;
  px: number;
  py: number;
  floatDelay?: number;
  className?: string;
  children: React.ReactNode;
}> = ({ depth, px, py, floatDelay = 0, className, children }) => (
  <div className={`absolute ${className}`}>
    <motion.div
      animate={{ x: px * depth, y: py * depth }}
      transition={{ type: "spring", stiffness: 120, damping: 20, mass: 0.4 }}
    >
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: floatDelay }}
      >
        {children}
      </motion.div>
    </motion.div>
  </div>
);

export const Hero: React.FC = () => {
  const reduced = useReducedMotion();
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const heroRef = useRef<HTMLElement>(null);
  // Scroll parallax: illustration group drifts down (y 0 -> 80) slower than the
  // headline as the hero leaves the viewport.
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const artY = useTransform(scrollYProgress, [0, 1], [0, 80]);

  const onMove = (e: React.MouseEvent<HTMLElement>) => {
    if (reduced || typeof window === "undefined" || window.innerWidth < 1024) return;
    const r = e.currentTarget.getBoundingClientRect();
    setPointer({
      x: (e.clientX - r.left) / r.width - 0.5,
      y: (e.clientY - r.top) / r.height - 0.5,
    });
  };

  return (
    <section
      ref={heroRef}
      onMouseMove={onMove}
      className="relative mx-auto grid w-full max-w-container grid-cols-1 items-center gap-12 px-5 pb-16 pt-32 md:px-10 lg:grid-cols-[1.2fr_1fr] lg:pt-40"
    >
      {/* LEFT */}
      <div>
        <motion.h1
          variants={container}
          initial="hidden"
          animate="show"
          className="font-sans font-bold text-ink"
          style={{ fontSize: "clamp(2.75rem, 7.2vw, 7.5rem)", lineHeight: 1.1, letterSpacing: "-0.02em" }}
        >
          {site.hero.heading.map((line, li) => (
            <span key={li} className="flex flex-wrap items-center gap-x-[0.28em]">
              {line.map((seg, si) =>
                seg.mascot ? (
                  <InlineMascot key={si} name={seg.mascot} />
                ) : (
                  <motion.span key={si} variants={word} className="inline-block">
                    {seg.text}
                  </motion.span>
                ),
              )}
            </span>
          ))}
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.6, ease: EASE }}
          className="mt-10 max-w-[45ch] text-[22px] leading-[1.7] text-muted"
        >
          {site.hero.paragraph}
        </motion.p>

        <div className="mt-10 flex flex-wrap items-center gap-8">
          <WaveButton label={site.hero.primaryCta.label} href={site.hero.primaryCta.href} />
          <ExploreLink label={site.hero.secondaryCta.label} href={site.hero.secondaryCta.href} />
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className="mt-14 font-mono text-[13px] uppercase tracking-[0.2em] text-[#8A8A7A]"
        >
          {site.hero.meta}
        </motion.p>
      </div>

      {/* RIGHT — parallax character group */}
      <motion.div style={{ y: reduced ? 0 : artY }} className="relative mx-auto h-[440px] w-full max-w-[520px]" aria-hidden>
        <Layer depth={15} px={pointer.x} py={pointer.y} className="bottom-0 left-1/2 w-64 -ml-32">
          <CircuitBoard className="w-full" />
        </Layer>
        <Layer depth={30} px={pointer.x} py={pointer.y} floatDelay={0.4} className="bottom-24 left-0 w-40">
          <GreenDrone className="w-full" />
        </Layer>
        <Layer depth={20} px={pointer.x} py={pointer.y} floatDelay={0.8} className="bottom-16 left-1/2 w-44 -ml-[88px]">
          <OrangeCube className="w-full" />
        </Layer>
        <Layer depth={12} px={pointer.x} py={pointer.y} floatDelay={0.2} className="bottom-28 right-0 w-36">
          <PurpleRobot className="w-full" />
        </Layer>
      </motion.div>
    </section>
  );
};

export default Hero;
