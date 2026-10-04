import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus } from "lucide-react";
import { Section } from "../ui/Section";
import { SectionHeading } from "../ui/SectionHeading";
import { site } from "../../content/site";
import { EASE } from "../../lib/motion";

export const Faq: React.FC = () => {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <Section id="faq">
      <SectionHeading title="Questions, Answered" subtitle="The things parents ask us most before booking a trial." />

      <div className="mx-auto mt-12 max-w-3xl space-y-4">
        {site.faq.items.map((item, i) => {
          const isOpen = open === i;
          return (
            <div key={item.q} className="overflow-hidden rounded-card bg-cardwhite shadow-sm">
              <button
                type="button"
                onClick={() => setOpen(isOpen ? null : i)}
                aria-expanded={isOpen}
                className="flex w-full items-center justify-between gap-4 p-6 text-left"
              >
                <span className="font-mono text-lg font-semibold text-ink">{item.q}</span>
                <motion.span
                  animate={{ rotate: isOpen ? 45 : 0 }}
                  transition={{ type: "spring", stiffness: 300, damping: 22 }}
                  className="shrink-0 text-ink"
                  aria-hidden
                >
                  <Plus size={22} />
                </motion.span>
              </button>

              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    key="body"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: EASE }}
                    className="overflow-hidden"
                  >
                    <p className="px-6 pb-6 font-mono text-[15px] leading-relaxed text-muted">{item.a}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </Section>
  );
};

export default Faq;
