import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import { useMotionValue, useSpring, useReducedMotion } from "framer-motion";
import { DURATION, EASE } from "../lib/motion";

/** True on devices with a fine, hovering pointer (desktop). */
export function useCanHover(): boolean {
  const [canHover, setCanHover] = useState(false);
  useEffect(() => {
    setCanHover(window.matchMedia("(hover: hover) and (pointer: fine)").matches);
  }, []);
  return canHover;
}

/** Cursor-follow spotlight: writes normalized --mx/--my CSS vars onto `ref`. */
export function useSpotlight<T extends HTMLElement>(ref: RefObject<T | null>, enabled = true) {
  const onMove = (e: React.MouseEvent) => {
    if (!enabled || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    ref.current.style.setProperty("--mx", `${px * 100}%`);
    ref.current.style.setProperty("--my", `${py * 100}%`);
  };
  return { onMove };
}

/** Subtle 3D tilt driven by cursor position. Returns springed rotate values. */
export function useTilt<T extends HTMLElement>(ref: RefObject<T | null>, max = 6, enabled = true) {
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  const spring = { stiffness: 150, damping: 18 };
  const rotateX = useSpring(rx, spring);
  const rotateY = useSpring(ry, spring);

  const onMove = (e: React.MouseEvent) => {
    if (!enabled || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    ry.set((px - 0.5) * max * 2);
    rx.set((0.5 - py) * max * 2);
  };
  const onLeave = () => {
    rx.set(0);
    ry.set(0);
  };
  return { rotateX, rotateY, onMove, onLeave };
}

/** Magnetic button: nudges the element up to `strength`px toward the cursor. */
export function useMagnetic(strength = 8, enabled = true) {
  const ref = useRef<HTMLElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const spring = { stiffness: 200, damping: 15, mass: 0.3 };
  const sx = useSpring(x, spring);
  const sy = useSpring(y, spring);

  const onMove = (e: React.MouseEvent) => {
    if (!enabled || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const px = e.clientX - (r.left + r.width / 2);
    const py = e.clientY - (r.top + r.height / 2);
    x.set((px / r.width) * strength * 2);
    y.set((py / r.height) * strength * 2);
  };
  const onLeave = () => {
    x.set(0);
    y.set(0);
  };
  return { ref, x: sx, y: sy, onMove, onLeave };
}

/** Scroll-reveal props (fade + rise, once). Lighter (opacity-only, no stagger)
 *  on mobile and for reduced-motion users. Spread onto a motion element. */
export function useReveal(delay = 0) {
  const reduced = useReducedMotion();
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    setIsMobile(window.matchMedia("(max-width: 767px)").matches);
  }, []);
  const light = reduced || isMobile;
  return {
    initial: light ? { opacity: 0 } : { opacity: 0, y: 40 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-60px" },
    transition: light
      ? { duration: DURATION.base }
      : { delay, duration: DURATION.slow, ease: EASE },
  };
}
