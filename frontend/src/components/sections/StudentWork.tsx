import React from "react";
import { ArrowRight } from "lucide-react";
import { Section } from "../ui/Section";
import { SectionHeading } from "../ui/SectionHeading";
import { Button } from "../ui/Button";
import { ProjectCard } from "./ProjectCard";
import { site } from "../../content/site";

export const StudentWork: React.FC = () => (
  <Section id="projects">
    <SectionHeading
      title="Student Work"
      subtitle="A glimpse into what our young makers design, build, print and fly every term."
    />

    <div className="mt-14 flex snap-x snap-mandatory gap-6 overflow-x-auto pb-4 md:grid md:grid-cols-2 md:overflow-visible md:pb-0 lg:grid-cols-4">
      {site.projects.map((project, i) => (
        <ProjectCard key={project.id} project={project} index={i} />
      ))}
    </div>

    <div className="mt-12 hidden justify-center md:flex">
      <Button variant="link" href="#projects" icon={<ArrowRight size={18} />}>
        View all projects
      </Button>
    </div>
  </Section>
);

export default StudentWork;
