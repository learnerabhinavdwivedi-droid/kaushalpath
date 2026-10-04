import React from "react";
import { cn } from "../../lib/cn";

export type PillVariant = "onWhite" | "onGreen" | "onLavender";

const VARIANTS: Record<PillVariant, string> = {
  // pale-lime bg + green text
  onWhite: "bg-page text-green",
  // lighter green bg + white text
  onGreen: "bg-[#2E9E5B] text-white",
  // near-white bg + dark text
  onLavender: "bg-[#F5ECFE] text-ink",
};

/**
 * Small tag: mono 13px / weight 600, px 16 / py 6, rounded-full.
 */
export const Pill: React.FC<{
  children: React.ReactNode;
  variant?: PillVariant;
  className?: string;
}> = ({ children, variant = "onWhite", className }) => (
  <span
    className={cn(
      "inline-flex items-center rounded-pill font-mono font-semibold",
      VARIANTS[variant],
      className,
    )}
    style={{ fontSize: 13, padding: "6px 16px" }}
  >
    {children}
  </span>
);
