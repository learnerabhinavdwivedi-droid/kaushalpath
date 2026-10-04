import React from "react";
import { motion, useScroll } from "framer-motion";

/**
 * Fixed 3px orange scroll-progress bar across the top.
 * scaleX = document scrollYProgress, origin left (transform-only, per rule #7).
 */
export const ScrollProgress: React.FC = () => {
  const { scrollYProgress } = useScroll();
  return (
    <motion.div
      style={{ scaleX: scrollYProgress }}
      className="fixed left-0 right-0 top-0 z-[70] h-[3px] origin-left bg-orange"
      aria-hidden
    />
  );
};

export default ScrollProgress;
