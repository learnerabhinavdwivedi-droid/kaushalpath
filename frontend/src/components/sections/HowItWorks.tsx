import React from "react";
import { motion } from "framer-motion";
import { Section } from "../ui/Section";
import { SectionHeading } from "../ui/SectionHeading";
import { site } from "../../content/site";
import { cn } from "../../lib/cn";
import { EASE } from "../../lib/motion";

const VARIANTS = [
  { bg: "bg-lavender", text: "text-[#2A2A2A]", stroke: "rgba(42,42,42,.35)" },
  { bg: "bg-green", text: "text-white", stroke: "rgba(255,255,255,.5)" },
  { bg: "bg-orange-deep", text: "text-white", stroke: "rgba(255,255,255,.5)" },
];

export const HowItWorks: React.FC = () => (
  <Section id="how-it-works">
    <SectionHeading
      title="How It Works"
      subtitle="Three simple steps from “just looking” to a shelf full of things your kid built."
    />

    <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3">
      {site.howItWorks.steps.map((step, i) => {
        const v = VARIANTS[i % VARIANTS.length];
        return (
          <motion.div
            key={step.n}
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ delay: i * 0.12, duration: 0.6, ease: EASE }}
            whileHover={{ y: -8 }}
            className={cn("flex min-h-[300px] flex-col rounded-card p-10", v.bg, v.text)}
          >
            <span
              className="font-mono font-bold leading-none"
              style={{ fontSize: 96, color: "transparent", WebkitTextStroke: `2px ${v.stroke}` }}
            >
              {step.n}
            </span>
            <h3 className="mt-4 font-mono text-2xl font-bold">{step.title}</h3>
            <p className="mt-3 font-mono text-[15px] leading-relaxed opacity-90">{step.desc}</p>
          </motion.div>
        );
      })}
    </div>
  </Section>
);

export default HowItWorks;
