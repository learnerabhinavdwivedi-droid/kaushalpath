import React, { useState } from "react";
import { motion } from "framer-motion";
import { Section } from "../ui/Section";
import { site } from "../../content/site";
import { cn } from "../../lib/cn";

type Values = { name: string; age: string; contact: string; course: string };
type Errors = Partial<Record<keyof Values, string>>;

const inputCls =
  "w-full rounded-2xl border-2 border-transparent bg-white px-5 py-3 font-mono text-ink placeholder:text-muted/60 focus:border-ink focus:outline-none";

const DOTS = Array.from({ length: 12 });

export const FinalCta: React.FC = () => {
  const [values, setValues] = useState<Values>({ name: "", age: "", contact: "", course: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);

  const set = (k: keyof Values, v: string) => {
    setValues((p) => ({ ...p, [k]: v }));
    setErrors((p) => ({ ...p, [k]: undefined }));
  };

  const validate = (): Errors => {
    const e: Errors = {};
    if (!values.name.trim()) e.name = "Please add your child's name.";
    if (!values.age) e.age = "Pick an age.";
    if (!values.contact.trim()) e.contact = "Add an email or phone.";
    if (!values.course) e.course = "Choose a course.";
    return e;
  };

  const onSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length === 0) setSubmitted(true); // frontend-only; backend wiring later
  };

  return (
    <Section id="cta">
      <div className="overflow-hidden rounded-[48px] bg-orange-deep px-6 py-16 text-white md:px-16 md:py-20">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="font-sans text-4xl font-bold tracking-heading md:text-5xl">{site.cta.title}</h2>
          <p className="mx-auto mt-4 max-w-[46ch] font-mono text-[17px] leading-relaxed text-white/90">
            {site.cta.subtitle}
          </p>
        </div>

        {submitted ? (
          <div className="mx-auto mt-12 max-w-xl text-center">
            <div className="relative mx-auto h-24 w-full">
              {DOTS.map((_, i) => {
                const angle = (i / DOTS.length) * Math.PI * 2;
                const dist = 70;
                return (
                  <motion.span
                    key={i}
                    initial={{ x: 0, y: 0, scale: 0, opacity: 1 }}
                    animate={{ x: Math.cos(angle) * dist, y: Math.sin(angle) * dist, scale: [0, 1, 0], opacity: [1, 1, 0] }}
                    transition={{ duration: 0.9, ease: "easeOut" }}
                    className="absolute left-1/2 top-1/2 h-3 w-3 rounded-full bg-white"
                  />
                );
              })}
            </div>
            <p className="mt-2 font-mono text-lg font-semibold">{site.cta.success}</p>
          </div>
        ) : (
          <form onSubmit={onSubmit} noValidate className="mx-auto mt-12 grid max-w-2xl grid-cols-1 gap-5 sm:grid-cols-2">
            <div>
              <label htmlFor="cta-name" className="sr-only">Child's name</label>
              <input id="cta-name" className={inputCls} placeholder="Child's name" value={values.name} onChange={(e) => set("name", e.target.value)} />
              {errors.name && <p className="mt-1 font-mono text-xs text-white/90">{errors.name}</p>}
            </div>

            <div>
              <label htmlFor="cta-age" className="sr-only">Age</label>
              <select id="cta-age" className={cn(inputCls, !values.age && "text-muted/60")} value={values.age} onChange={(e) => set("age", e.target.value)}>
                <option value="" disabled>Age</option>
                {site.cta.ageOptions.map((a) => (
                  <option key={a} value={a} className="text-ink">{a} years</option>
                ))}
              </select>
              {errors.age && <p className="mt-1 font-mono text-xs text-white/90">{errors.age}</p>}
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="cta-contact" className="sr-only">Parent email or phone</label>
              <input id="cta-contact" className={inputCls} placeholder="Parent email or phone" value={values.contact} onChange={(e) => set("contact", e.target.value)} />
              {errors.contact && <p className="mt-1 font-mono text-xs text-white/90">{errors.contact}</p>}
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="cta-course" className="sr-only">Preferred course</label>
              <select id="cta-course" className={cn(inputCls, !values.course && "text-muted/60")} value={values.course} onChange={(e) => set("course", e.target.value)}>
                <option value="" disabled>Preferred course</option>
                {site.cta.courseOptions.map((c) => (
                  <option key={c} value={c} className="text-ink">{c}</option>
                ))}
              </select>
              {errors.course && <p className="mt-1 font-mono text-xs text-white/90">{errors.course}</p>}
            </div>

            <div className="sm:col-span-2">
              <motion.button
                type="submit"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="w-full rounded-pill bg-ink px-8 py-4 font-mono text-base font-semibold text-white"
              >
                Book a Free Trial
              </motion.button>
            </div>
          </form>
        )}
      </div>
    </Section>
  );
};

export default FinalCta;
