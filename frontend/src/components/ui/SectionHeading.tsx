import React from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { cn } from "../../lib/cn";
import { EASE } from "../../lib/motion";

/**
 * Section heading: title words clip-reveal one by one (overflow-hidden mask,
 * translateY 110% -> 0), subtitle fades in 150ms later. Reduced-motion users
 * get a plain opacity fade.
 */
const titleContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
};

const titleWord: Variants = {
  hidden: { y: "110%" },
  show: { y: "0%", transition: { duration: 0.5, ease: EASE } },
};

const fadeOnly: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.3 } },
};

const subtitleFade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { delay: 0.15, duration: 0.4 } },
};

export const SectionHeading: React.FC<{
  title: string;
  subtitle?: string;
  className?: string;
  id?: string;
}> = ({ title, subtitle, className, id }) => {
  const reduced = useReducedMotion();
  const words = title.split(" ");

  return (
    <div className={cn("max-w-[46rem]", className)}>
      <motion.h2
        id={id}
        variants={reduced ? fadeOnly : titleContainer}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-60px" }}
        className="font-sans font-bold tracking-heading text-ink"
        style={{ fontSize: "clamp(2.25rem, 4.5vw, 3.5rem)", lineHeight: 1.1 }}
      >
        {words.map((w, i) =>
          reduced ? (
            <React.Fragment key={i}>
              {w}
              {i < words.length - 1 ? " " : ""}
            </React.Fragment>
          ) : (
            <span
              key={i}
              className="mr-[0.25em] inline-block overflow-hidden align-bottom pb-[0.12em] -mb-[0.12em]"
            >
              <motion.span variants={titleWord} className="inline-block">
                {w}
              </motion.span>
            </span>
          ),
        )}
      </motion.h2>
      {subtitle && (
        <motion.p
          variants={subtitleFade}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-60px" }}
          className="mt-5 text-muted"
          style={{ fontSize: "18px", lineHeight: 1.8, maxWidth: "52ch" }}
        >
          {subtitle}
        </motion.p>
      )}
    </div>
  );
};
