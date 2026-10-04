import React from "react";
import { ArrowRight } from "lucide-react";
import { Section } from "../components/ui/Section";
import { SectionHeading } from "../components/ui/SectionHeading";
import { Pill } from "../components/ui/Pill";
import { Button } from "../components/ui/Button";

const COLOR_TOKENS: Array<{ name: string; hex: string; cls: string }> = [
  { name: "page", hex: "#F1F5E0", cls: "bg-page" },
  { name: "ink", hex: "#0A0A0A", cls: "bg-ink" },
  { name: "muted", hex: "#55554A", cls: "bg-muted" },
  { name: "orange", hex: "#FF4F00", cls: "bg-orange" },
  { name: "orange-deep", hex: "#C13A00", cls: "bg-orange-deep" },
  { name: "green", hex: "#0F7B3F", cls: "bg-green" },
  { name: "lavender", hex: "#DDB9FB", cls: "bg-lavender" },
  { name: "cardwhite", hex: "#FFFFFF", cls: "bg-cardwhite" },
];

const swatchBorder = "border border-ink/10";

export const StyleGuidePage: React.FC = () => (
  <div className="min-h-screen bg-page text-ink">
    <Section>
      <SectionHeading
        title="KaushalPath Design System"
        subtitle="Phase 1 tokens & primitives. Every SparkLab-style section in later phases is built from these."
      />
    </Section>

    {/* Colors */}
    <Section className="pt-0">
      <h3 className="mb-6 font-bold">Color tokens</h3>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {COLOR_TOKENS.map((c) => (
          <div key={c.name} className="rounded-card bg-cardwhite p-4 shadow-sm">
            <div className={`h-16 w-full rounded-inner ${c.cls} ${swatchBorder}`} />
            <p className="mt-3 text-sm font-semibold">{c.name}</p>
            <p className="font-mono text-xs text-muted">{c.hex}</p>
          </div>
        ))}
      </div>
    </Section>

    {/* Typography */}
    <Section className="pt-0">
      <h3 className="mb-6 font-bold">Typography</h3>
      <div className="space-y-5 rounded-card bg-cardwhite p-8 shadow-sm">
        <p className="font-display text-5xl font-extrabold tracking-tight">
          Barlow Condensed 800 — Logo / Display
        </p>
        <p className="text-3xl font-bold tracking-heading">
          IBM Plex Mono 700 — Heading
        </p>
        <p className="text-base font-semibold">IBM Plex Mono 600 — Label</p>
        <p className="max-w-[52ch] text-base text-muted" style={{ lineHeight: 1.8 }}>
          IBM Plex Mono 400 — Body copy. Body line-height is 1.8 and headings use
          -0.02em letter-spacing with a 1.1 line-height.
        </p>
      </div>
    </Section>

    {/* Radius */}
    <Section className="pt-0">
      <h3 className="mb-6 font-bold">Radius tokens</h3>
      <div className="flex flex-wrap gap-6">
        {[
          { label: "pill · 9999px", cls: "rounded-pill" },
          { label: "card · 32px", cls: "rounded-card" },
          { label: "inner · 20px", cls: "rounded-inner" },
        ].map((r) => (
          <div key={r.label} className="text-center">
            <div className={`h-24 w-24 bg-lavender ${r.cls}`} />
            <p className="mt-2 font-mono text-xs text-muted">{r.label}</p>
          </div>
        ))}
      </div>
    </Section>

    {/* Pills */}
    <Section className="pt-0">
      <h3 className="mb-6 font-bold">Pill variants</h3>
      <div className="flex flex-wrap items-center gap-4">
        <Pill variant="onWhite">onWhite</Pill>
        <Pill variant="onGreen">onGreen</Pill>
        <Pill variant="onLavender">onLavender</Pill>
      </div>
    </Section>

    {/* Buttons */}
    <Section className="pt-0">
      <h3 className="mb-6 font-bold">Buttons</h3>
      <div className="flex flex-wrap items-center gap-8">
        <Button variant="primary" href="#primary">Book a Trial</Button>
        <Button variant="link" href="#link" icon={<ArrowRight size={18} />}>
          See courses
        </Button>
      </div>
    </Section>

    {/* SectionHeading */}
    <Section className="pt-0">
      <h3 className="mb-6 font-bold">SectionHeading</h3>
      <div className="rounded-card bg-cardwhite p-8 shadow-sm">
        <SectionHeading
          title="What We Teach"
          subtitle="Four core tracks plus holiday camps. Every course is project-based: kids leave each term with something they designed, built and launched themselves."
        />
      </div>
    </Section>
  </div>
);

export default StyleGuidePage;
