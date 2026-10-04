import React from "react";
import { Section } from "../ui/Section";
import { SectionHeading } from "../ui/SectionHeading";
import { CourseCard } from "./CourseCard";
import { site } from "../../content/site";

export const WhatWeTeach: React.FC = () => (
  <Section id="courses">
    <SectionHeading title="What We Teach" subtitle="Four core tracks plus holiday camps. Every course is project-based: kids leave each term with something they designed, built and launched themselves." />
    <div className="mt-14 grid grid-cols-1 gap-[25px] min-[700px]:grid-cols-2 lg:grid-cols-3">
      {site.courses.map((course) => (
        <CourseCard key={course.id} course={course} />
      ))}
    </div>
  </Section>
);

export default WhatWeTeach;
