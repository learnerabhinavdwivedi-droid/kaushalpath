import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "../../lib/cn";
import { useCanHover, useMagnetic } from "../../hooks/interactions";
import { useCursor } from "./Cursor";

type BaseProps = {
  children: React.ReactNode;
  className?: string;
};

type ButtonProps = BaseProps & {
  variant?: "primary" | "link";
  href?: string;
  onClick?: () => void;
  icon?: React.ReactNode;
  type?: "button" | "submit";
  disabled?: boolean;
};

const RING =
  "focus:outline-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-orange-deep focus-visible:ring-offset-[3px] focus-visible:ring-offset-page";

/**
 * Button primitives:
 * - primary: black pill, magnetic on desktop, press scale 0.97, orange focus ring.
 * - link:    inline text with a 2px orange underline + trailing icon.
 */
export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  href,
  onClick,
  icon,
  type = "button",
  disabled,
  className,
}) => {
  const canHover = useCanHover();
  const reduced = useReducedMotion();
  const cursor = useCursor();
  const magneticOn = canHover && !reduced && !disabled && variant === "primary";
  const mag = useMagnetic(8, magneticOn);
  const handlers = magneticOn
    ? {
        style: { x: mag.x, y: mag.y },
        onMouseMove: mag.onMove,
        onMouseEnter: () => cursor.enter(),
        onMouseLeave: () => {
          mag.onLeave();
          cursor.leave();
        },
      }
    : cursor.bind();

  if (variant === "link") {
    const content = (
      <>
        {children}
        {icon && <span aria-hidden className="ml-1 inline-flex">{icon}</span>}
      </>
    );
    const linkClass = cn("link-underline inline-flex items-center font-mono font-semibold text-ink", RING, className);
    return href ? (
      <a href={href} className={linkClass} {...cursor.bind()}>
        {content}
      </a>
    ) : (
      <button type={type} onClick={onClick} className={linkClass} {...cursor.bind()}>
        {content}
      </button>
    );
  }

  const primaryClass = cn(
    "inline-flex items-center justify-center rounded-pill bg-ink text-white",
    "font-mono font-semibold",
    RING,
    "disabled:opacity-50 disabled:cursor-not-allowed",
    className,
  );
  const pad = { fontSize: 16, padding: "16px 28px" } as const;

  return href ? (
    <motion.a
      href={href}
      className={primaryClass}
      style={pad}
      ref={mag.ref as unknown as React.Ref<HTMLAnchorElement>}
      whileTap={{ scale: 0.97 }}
      {...handlers}
    >
      {children}
    </motion.a>
  ) : (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={primaryClass}
      style={pad}
      ref={mag.ref as unknown as React.Ref<HTMLButtonElement>}
      whileTap={{ scale: 0.97 }}
      {...handlers}
    >
      {children}
    </motion.button>
  );
};
