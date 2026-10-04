import React, { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
import { Section } from "../ui/Section";
import { site } from "../../content/site";
import { EASE } from "../../lib/motion";

const CountUp: React.FC<{ to: number; prefix?: string; suffix?: string }> = ({ to, prefix = "", suffix = "" }) => {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const [val, setVal] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const dur = 1200;
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      setVal(Math.round(p * to));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, to]);

  return (
    <span ref={ref}>
      {prefix}
      {val}
      {suffix}
    </span>
  );
};

export const About: React.FC = () => (
  <Section id="about">
    <div className="grid grid-cols-1 gap-16 lg:grid-cols-2">
      {/* Left */}
      <div>
        <motion.h2
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, ease: EASE }}
          className="font-sans font-bold tracking-heading text-ink"
          style={{ fontSize: "clamp(2rem, 4vw, 3rem)", lineHeight: 1.1 }}
        >
          {site.about.heading}
        </motion.h2>
        <p className="mt-6 max-w-[52ch] font-mono text-[17px] leading-relaxed text-muted">{site.about.body}</p>

        <div className="mt-12 grid grid-cols-3 gap-6">
          {site.about.stats.map((s) => (
            <div key={s.label}>
              <div className="font-mono text-5xl font-bold text-ink">
                <CountUp to={s.to} prefix={s.prefix} suffix={s.suffix} />
              </div>
              <p className="mt-2 font-mono text-sm uppercase tracking-[0.15em] text-muted">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right — mentors */}
      <div className="grid grid-cols-2 gap-6">
        {site.about.mentors.map((m, i) => (
          <motion.div
            key={m.name}
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ delay: i * 0.1, duration: 0.6, ease: EASE }}
            whileHover={{ y: -6 }}
            className="overflow-hidden rounded-card bg-cardwhite p-4 shadow-sm"
          >
            <div
              className="flex aspect-square items-center justify-center rounded-inner"
              style={{ background: `linear-gradient(135deg, ${m.gradient[0]}, ${m.gradient[1]})` }}
              role="img"
              aria-label={`${m.name} portrait placeholder`}
            >
              {/* simple blob face placeholder */}
              <svg viewBox="0 0 100 100" className="h-20 w-20">
                <circle cx="50" cy="50" r="34" fill="rgba(255,255,255,.6)" />
                <circle cx="40" cy="46" r="4" fill="#0A0A0A" />
                <circle cx="60" cy="46" r="4" fill="#0A0A0A" />
                <path d="M38 60 Q50 70 62 60" stroke="#0A0A0A" strokeWidth="3" fill="none" strokeLinecap="round" />
              </svg>
            </div>
            <div className="px-2 py-3">
              <p className="font-mono text-base font-bold text-ink">{m.name}</p>
              <p className="font-mono text-sm text-muted">{m.role}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  </Section>
);

export default About;
