import React from "react";
import { cn } from "../../lib/cn";

/**
 * Page container: max-width 1600px, horizontal padding 40px desktop / 20px mobile.
 */
export const Container: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => (
  <div className={cn("mx-auto w-full max-w-container px-5 md:px-10", className)}>
    {children}
  </div>
);
