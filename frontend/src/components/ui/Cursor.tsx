import React, { createContext, useContext, useEffect, useState } from "react";
import { motion, useMotionValue, useSpring, useReducedMotion } from "framer-motion";
import { useCanHover } from "../../hooks/interactions";
import { SPRING } from "../../lib/motion";
import { cn } from "../../lib/cn";

type Variant = "default" | "grow" | "view";

type CursorCtx = {
  enter: (label?: string) => void;
  leave: () => void;
};

const noop = () => {};
const CursorContext = createContext<CursorCtx>({ enter: noop, leave: noop });

/** Attach to any interactive element to grow the cursor (optionally with a label). */
export const useCursor = () => {
  const { enter, leave } = useContext(CursorContext);
  return {
    enter,
    leave,
    bind: (label?: string) => ({
      onMouseEnter: () => enter(label),
      onMouseLeave: leave,
    }),
  };
};

const CustomCursor: React.FC<{ variant: Variant; label: string }> = ({ variant, label }) => {
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const spring = { stiffness: 500, damping: 40, mass: 0.3 };
  const sx = useSpring(x, spring);
  const sy = useSpring(y, spring);

  useEffect(() => {
    const move = (e: MouseEvent) => {
      x.set(e.clientX);
      y.set(e.clientY);
    };
    window.addEventListener("mousemove", move);
    return () => window.removeEventListener("mousemove", move);
  }, [x, y]);

  const size = variant === "default" ? 14 : 56;
  return (
    <motion.div style={{ x: sx, y: sy }} className="pointer-events-none fixed left-0 top-0 z-[100]" aria-hidden>
      <motion.div
        animate={{
          width: size,
          height: size,
          backgroundColor: variant === "default" ? "#0A0A0A" : "rgba(255,79,0,0.9)",
        }}
        transition={SPRING}
        className="-translate-x-1/2 -translate-y-1/2 flex items-center justify-center rounded-full"
      >
        {variant === "view" && (
          <span className="font-mono text-[11px] font-semibold text-white">{label}</span>
        )}
      </motion.div>
    </motion.div>
  );
};

export const CursorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const canHover = useCanHover();
  const reduced = useReducedMotion();
  const [enabled, setEnabled] = useState(false);
  const [variant, setVariant] = useState<Variant>("default");
  const [label, setLabel] = useState("");

  // On by default only for desktop + full-motion users.
  useEffect(() => {
    if (canHover && !reduced) setEnabled(true);
  }, [canHover, reduced]);

  const enter = (l?: string) => {
    setVariant(l ? "view" : "grow");
    setLabel(l ?? "");
  };
  const leave = () => {
    setVariant("default");
    setLabel("");
  };

  return (
    <CursorContext.Provider value={{ enter, leave }}>
      <div className={cn(enabled && "spark-cursor-none")}>{children}</div>

      {enabled && <CustomCursor variant={variant} label={label} />}

      {canHover && (
        <button
          type="button"
          onClick={() => setEnabled((e) => !e)}
          className="fixed bottom-4 right-4 z-[101] flex min-h-[44px] items-center rounded-pill bg-ink/85 px-4 font-mono text-xs font-semibold text-white shadow-lg backdrop-blur hover:bg-ink focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-orange-deep focus-visible:ring-offset-2"
          aria-pressed={enabled}
        >
          Cursor: {enabled ? "on" : "off"}
        </button>
      )}
    </CursorContext.Provider>
  );
};
