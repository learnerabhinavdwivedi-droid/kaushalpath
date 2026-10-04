import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Section } from "../ui/Section";
import { SectionHeading } from "../ui/SectionHeading";
import { site } from "../../content/site";
import { cn } from "../../lib/cn";
import { EASE } from "../../lib/motion";

export const Schedule: React.FC = () => {
  const [active, setActive] = useState(0);
  const tab = site.schedule.tabs[active];

  return (
    <Section id="schedule">
      <SectionHeading
        title="Class Schedule"
        subtitle="Pick a slot that fits your week. Every class is capped small — the orange pill shows how many seats are left."
      />

      {/* Pill tabs */}
      <div className="mt-10 inline-flex flex-wrap gap-2 rounded-pill bg-cardwhite p-2 shadow-sm">
        {site.schedule.tabs.map((t, i) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActive(i)}
            aria-pressed={active === i}
            className={cn(
              "rounded-pill px-6 py-3 font-mono text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-orange-deep focus-visible:ring-offset-[3px] focus-visible:ring-offset-page",
              active === i ? "bg-ink text-white" : "text-muted hover:text-ink",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content crossfade + slide on tab change */}
      <div className="mt-8">
        <AnimatePresence mode="wait">
          <motion.ul
            key={tab.id}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="space-y-3"
          >
            {tab.classes.map((c) => (
              <li
                key={c.time + c.course}
                className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-card bg-cardwhite p-6 shadow-sm transition-transform hover:-translate-y-0.5"
              >
                <span className="w-40 font-mono text-sm font-semibold text-ink">{c.time}</span>
                <span className="flex-1 font-mono text-base text-ink">{c.course}</span>
                <span className="font-mono text-sm text-muted">{c.ages}</span>
                <span className="rounded-pill bg-orange-deep px-4 py-1.5 font-mono text-xs font-semibold text-white">
                  {c.seats} {c.seats === 1 ? "seat" : "seats"} left
                </span>
              </li>
            ))}
          </motion.ul>
        </AnimatePresence>
      </div>
    </Section>
  );
};

export default Schedule;
