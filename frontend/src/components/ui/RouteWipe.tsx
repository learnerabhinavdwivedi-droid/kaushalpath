import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { useLocation } from "wouter";
import { EASE } from "../../lib/motion";

/**
 * Full-screen orange wipe that slides bottom-to-top through the viewport on
 * every route change (~600ms total: 300ms in, 300ms out). Skipped entirely
 * for prefers-reduced-motion users.
 */
export const RouteWipe: React.FC = () => {
  const [location] = useLocation();
  const reduced = useReducedMotion();
  const prev = useRef(location);
  const [wipeKey, setWipeKey] = useState<string | null>(null);

  useEffect(() => {
    if (prev.current === location || reduced) return;
    prev.current = location;
    setWipeKey(location);
    const id = window.setTimeout(() => setWipeKey(null), 650);
    return () => window.clearTimeout(id);
  }, [location, reduced]);

  return (
    <AnimatePresence>
      {wipeKey && (
        <motion.div
          key={wipeKey}
          initial={{ y: "100%" }}
          animate={{ y: 0 }}
          exit={{ y: "-100%" }}
          transition={{ duration: 0.3, ease: EASE }}
          className="pointer-events-none fixed inset-0 z-[90] bg-orange"
          aria-hidden
        />
      )}
    </AnimatePresence>
  );
};

export default RouteWipe;
