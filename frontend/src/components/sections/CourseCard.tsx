import React, { useRef, useState } from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { COURSE_MASCOTS } from "./CoursesArt";
import { cn } from "../../lib/cn";
import { EASE } from "../../lib/motion";
import { useCanHover, useTilt, useSpotlight, useReveal } from "../../hooks/interactions";
import { useCursor } from "../ui/Cursor";
import type { Course, CourseVariant, PillStyle } from "../../content/site";

const CARD_STYLES: Record<CourseVariant, { title: string; desc: string; foot: string; arrow: string }> = {
  white: { title: "text-ink", desc: "text-black/55", foot: "text-muted", arrow: "bg-black/5 text-ink" },
  orange: { title: "text-white", desc: "text-white/90", foot: "text-white/80", arrow: "bg-white/20 text-white" },
  lavender: { title: "text-[#2A2A2A]", desc: "text-[#2A2A2A]/75", foot: "text-[#2A2A2A]/70", arrow: "bg-black/5 text-[#2A2A2A]" },
  green: { title: "text-white", desc: "text-white/90", foot: "text-white/80", arrow: "bg-white/20 text-white" },
};

const PILL_STYLES: Record<PillStyle, string> = {
  onWhite: "bg-page text-green",
  onOrange: "bg-black/20 text-white",
  onLavender: "bg-[#F5ECFE] text-[#2A2A2A]",
  onGreenLight: "bg-black/20 text-white",
};

const pillContainer: Variants = { rest: {}, hover: { transition: { staggerChildren: 0.05 } } };
const pillItem: Variants = { rest: { y: 0 }, hover: { y: [0, -6, 0], transition: { duration: 0.4, ease: EASE } } };

export const CourseCard: React.FC<{ course: Course }> = ({ course }) => {
  const reduced = useReducedMotion();
  const canHover = useCanHover();
  const ref = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState(false);

  const tiltEnabled = canHover && !reduced;
  const tilt = useTilt(ref, 6, tiltEnabled);
  const spot = useSpotlight(ref, tiltEnabled);
  const reveal = useReveal();
  const cursor = useCursor();

  const s = CARD_STYLES[course.variant];
  const Mascot = COURSE_MASCOTS[course.mascot];
  const onMove = (e: React.MouseEvent) => {
    tilt.onMove(e);
    spot.onMove(e);
  };

  return (
    <motion.div {...reveal} className={cn(course.span === 2 && "min-[700px]:col-span-2")}>
      <motion.div
        ref={ref}
        onMouseMove={onMove}
        onMouseEnter={() => {
          setHovered(true);
          cursor.enter("View");
        }}
        onMouseLeave={() => {
          setHovered(false);
          tilt.onLeave();
          cursor.leave();
        }}
        whileTap={{ scale: 0.98 }}
        animate={{
          y: hovered && canHover ? -8 : 0,
          boxShadow: hovered && canHover
            ? "0 30px 60px -20px rgba(0,0,0,.25)"
            : "0 10px 30px -18px rgba(0,0,0,.15)",
        }}
        transition={{ type: "spring", stiffness: 300, damping: 24 }}
        style={{ rotateX: tilt.rotateX, rotateY: tilt.rotateY, transformPerspective: 1000, transformStyle: "preserve-3d" }}
        className={cn(
          "relative flex min-h-[480px] flex-col overflow-hidden rounded-card p-8 min-[700px]:p-[50px] md:min-h-[620px]",
          course.variant === "white" && "bg-cardwhite",
          course.variant === "orange" && "bg-orange-deep",
          course.variant === "lavender" && "bg-lavender",
          course.variant === "green" && "bg-green",
        )}
      >
        {/* Cursor-follow spotlight */}
        <div
          className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-300"
          style={{
            opacity: hovered && tiltEnabled ? 1 : 0,
            background:
              "radial-gradient(300px circle at var(--mx,50%) var(--my,50%), rgba(255,255,255,.35), transparent 60%)",
          }}
        />

        {/* Arrow button (top-right) */}
        <motion.a
          href={`#${course.id}`}
          aria-label={`Explore ${course.title}`}
          initial={false}
          animate={{ opacity: hovered && canHover ? 1 : 0, x: hovered && canHover ? 0 : 12, rotate: hovered && canHover ? 45 : 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className={cn(
            "absolute right-8 top-8 z-20 flex h-12 w-12 items-center justify-center rounded-full",
            s.arrow,
          )}
        >
          <ArrowUpRight size={22} />
        </motion.a>

        {/* Mascot (decorative placeholder art) */}
        <div className="relative z-10 h-[190px] w-[190px] shrink-0" aria-hidden>
          <motion.div
            className="h-full w-full"
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
          >
            <motion.div
              className="h-full w-full"
              animate={{ scale: hovered ? 1.12 : 1, rotate: hovered ? -6 : 0 }}
              transition={{ type: "spring", stiffness: 200, damping: 15 }}
            >
              <Mascot className="h-full w-full" />
            </motion.div>
          </motion.div>
        </div>

        {/* Body */}
        <div className="relative z-10 mt-auto pt-8">
          <h3 className={cn("font-mono text-[28px] font-bold", s.title)}>{course.title}</h3>
          <p className={cn("mt-4 font-mono text-[17px] leading-[1.85]", s.desc)}>{course.description}</p>

          <motion.ul
            variants={pillContainer}
            animate={hovered ? "hover" : "rest"}
            className="mt-6 flex flex-wrap gap-[10px]"
          >
            {course.pills.map((p) => (
              <motion.li
                key={p}
                variants={pillItem}
                className={cn("rounded-pill px-4 py-1.5 font-mono text-[13px] font-semibold", PILL_STYLES[course.pillStyle])}
              >
                {p}
              </motion.li>
            ))}
          </motion.ul>

          {course.footnote && (
            <p className={cn("mt-6 font-mono text-[17px]", s.foot)}>{course.footnote}</p>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CourseCard;
