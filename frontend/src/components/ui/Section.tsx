import React from "react";
import { cn } from "../../lib/cn";
import { Container } from "./Container";

/**
 * Vertical section wrapper with the section padding token:
 * 120px desktop / 72px mobile. Pass `bleed` to skip the inner container.
 */
export const Section: React.FC<{
  children: React.ReactNode;
  className?: string;
  id?: string;
  bleed?: boolean;
}> = ({ children, className, id, bleed }) => (
  <section id={id} className={cn("py-[72px] md:py-section-y", className)}>
    {bleed ? children : <Container>{children}</Container>}
  </section>
);
