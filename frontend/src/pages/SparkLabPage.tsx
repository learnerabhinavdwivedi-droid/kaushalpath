import React from "react";
import { Layout } from "../components/layout/Layout";
import { Marquee } from "../components/ui/Marquee";
import { Hero } from "../components/sections/Hero";
import { WhatWeTeach } from "../components/sections/WhatWeTeach";
import { StudentWork } from "../components/sections/StudentWork";
import { HowItWorks } from "../components/sections/HowItWorks";
import { Schedule } from "../components/sections/Schedule";
import { About } from "../components/sections/About";
import { Testimonials } from "../components/sections/Testimonials";
import { Faq } from "../components/sections/Faq";
import { FinalCta } from "../components/sections/FinalCta";

/**
 * Full SparkLab-style marketing landing (Phases 3–6).
 * Nav anchors: #courses, #projects, #about, #schedule; CTA form is #cta.
 */
export const SparkLabPage: React.FC = () => (
  <Layout>
    <Hero />
    <WhatWeTeach />
    <StudentWork />
    <Marquee />
    <HowItWorks />
    <Schedule />
    <About />
    <Marquee />
    <Testimonials />
    <Faq />
    <FinalCta />
  </Layout>
);

export default SparkLabPage;
