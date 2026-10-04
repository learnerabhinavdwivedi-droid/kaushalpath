import React, { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, animate } from "framer-motion";
import { Section } from "../ui/Section";
import { SectionHeading } from "../ui/SectionHeading";
import { site } from "../../content/site";
import { cn } from "../../lib/cn";

const CARD_STYLES: Record<string, string> = {
  white: "bg-cardwhite text-ink",
  lavender: "bg-lavender text-[#2A2A2A]",
  green: "bg-green text-white",
};

export const Testimonials: React.FC = () => {
  const quotes = site.testimonials.quotes;
  const n = quotes.length;
  const [active, setActive] = useState(0);
  const [width, setWidth] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setWidth(el.clientWidth);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const controls = animate(x, -active * width, { type: "spring", stiffness: 300, damping: 34 });
    return () => controls.stop();
  }, [active, width, x]);

  const onDragEnd = () => {
    const i = Math.round(-x.get() / (width || 1));
    setActive(Math.min(n - 1, Math.max(0, i)));
  };

  return (
    <Section id="testimonials">
      <SectionHeading
        title="What Parents Say"
        subtitle="Drag to browse a few notes from the families who build with us every term."
      />

      <div ref={ref} className="mt-14 overflow-hidden">
        <motion.div
          className="flex cursor-grab active:cursor-grabbing"
          style={{ x }}
          drag="x"
          dragElastic={0.15}
          dragConstraints={{ left: -(n - 1) * width, right: 0 }}
          onDragEnd={onDragEnd}
        >
          {quotes.map((q) => (
            <div key={q.name} className="w-full flex-none px-1">
              <figure className={cn("flex min-h-[280px] flex-col justify-between rounded-card p-10 shadow-sm", CARD_STYLES[q.variant])}>
                <blockquote className="font-mono text-xl leading-relaxed">“{q.quote}”</blockquote>
                <figcaption className="mt-8">
                  <div className="font-mono text-base font-bold">{q.name}</div>
                  <div className="font-mono text-sm opacity-70">{q.meta}</div>
                </figcaption>
              </figure>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Dots (44px touch target, small visual dot) */}
      <div className="mt-8 flex items-center justify-center">
        {quotes.map((q, i) => (
          <button
            key={q.name}
            type="button"
            aria-label={`Go to testimonial ${i + 1}`}
            onClick={() => setActive(i)}
            className="group flex h-11 w-11 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-orange-deep focus-visible:ring-offset-[3px] focus-visible:ring-offset-page"
          >
            <span
              className={cn(
                "h-3 rounded-full transition-all",
                active === i ? "w-8 bg-ink" : "w-3 bg-ink/25 group-hover:bg-ink/50",
              )}
            />
          </button>
        ))}
      </div>
    </Section>
  );
};

export default Testimonials;
