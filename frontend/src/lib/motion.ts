import type { Transition } from "framer-motion";

/**
 * Central motion tokens (Phase 7). Keep spring + duration values in one place
 * so every section shares the same feel. Durations are in seconds (Framer).
 */
export const SPRING: Transition = { type: "spring", stiffness: 260, damping: 20 };

export const DURATION = { fast: 0.2, base: 0.35, slow: 0.7 } as const;

export const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];
