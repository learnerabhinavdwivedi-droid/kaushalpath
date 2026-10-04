import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { cn } from "../../lib/cn";
import { EASE } from "../../lib/motion";
import { useReveal } from "../../hooks/interactions";
import { useCursor } from "../ui/Cursor";
import { SmartImage } from "../ui/SmartImage";
import type { Project } from "../../content/site";

const DOT_COLORS = ["#FF4F00", "#DDB9FB", "#0F7B3F"];

export const ProjectCard: React.FC<{ project: Project; index: number }> = ({ project, index }) => {
  const [hovered, setHovered] = useState(false);
  const [typed, setTyped] = useState("");
  const reveal = useReveal(index * 0.12);
  const cursor = useCursor();
  const full = `sparklab.school${project.url}`;
  const rotate = index % 2 === 0 ? 1.2 : -1.2;

  // Typewriter: retype from 0 on hover; show full text when idle.
  useEffect(() => {
    if (!hovered) return;
    setTyped("");
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setTyped(full.slice(0, i));
      if (i >= full.length) window.clearInterval(id);
    }, 30);
    return () => window.clearInterval(id);
  }, [hovered, full]);

  return (
    <motion.article {...reveal} className="w-[80vw] shrink-0 snap-center md:w-auto">
      <motion.div
        onHoverStart={() => {
          setHovered(true);
          cursor.enter("View");
        }}
        onHoverEnd={() => {
          setHovered(false);
          cursor.leave();
        }}
        whileTap={{ scale: 0.98 }}
        animate={{ y: hovered ? -10 : 0, rotate: hovered ? rotate : 0, boxShadow: hovered ? "0 30px 60px -20px rgba(0,0,0,.25)" : "0 10px 30px -18px rgba(0,0,0,.12)" }}
        transition={{ type: "spring", stiffness: 300, damping: 22 }}
        className="group rounded-[36px] bg-cardwhite p-[15px]"
      >
        {/* Browser window */}
        <div className="overflow-hidden rounded-[24px] border border-[#E6E6DF]">
          {/* Titlebar */}
          <div className="flex h-14 items-center px-5">
            <div className="flex items-center gap-2">
              {DOT_COLORS.map((c) => (
                <motion.span
                  key={c}
                  whileHover={{ scale: 1.4 }}
                  transition={{ type: "spring", stiffness: 500, damping: 18 }}
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            <div className="ml-4 flex-1 truncate rounded-pill bg-[#F2F2EC] px-[14px] py-2 font-mono text-[13px] text-[#666]">
              {hovered ? typed : full}
              {hovered && <span className="caret-blink ml-0.5">|</span>}
            </div>
          </div>

          {/* Image (clip-path reveal + inner zoom, shimmer/blur via SmartImage) */}
          <motion.div
            initial={{ clipPath: "inset(0 0 100% 0)" }}
            whileInView={{ clipPath: "inset(0 0 0% 0)" }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.7, ease: EASE }}
            className="mx-3 mb-3 overflow-hidden rounded-[20px]"
          >
            <SmartImage
              alt={`${project.title} preview`}
              gradient={project.gradient}
              className="aspect-[4/3] w-full origin-center transition-transform duration-700 ease-out group-hover:scale-[1.08]"
            />
          </motion.div>
        </div>

        {/* Meta */}
        <div className="p-6">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[12px] uppercase tracking-[0.25em] text-[#777]">
              {project.label}
            </span>
            <ArrowRight
              size={15}
              className={cn("text-[#777] transition-all duration-300", hovered ? "translate-x-0 opacity-100" : "-translate-x-1 opacity-0")}
            />
          </div>
          <h3 className="mt-2 font-mono text-[22px] font-bold text-ink">{project.title}</h3>
          <p className="mt-2 font-mono text-[15px] leading-relaxed text-muted">{project.description}</p>
        </div>
      </motion.div>
    </motion.article>
  );
};

export default ProjectCard;
