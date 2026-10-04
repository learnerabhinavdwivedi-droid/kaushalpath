/**
 * Central site content (master rule #3): every string the marketing frontend
 * renders lives here so copy can be swapped without touching components.
 */

export type NavLink = { label: string; href: string };

/** A hero heading token: either a word or an inline mascot. */
export type HeroSegment = { text?: string; mascot?: "drone" | "bulb" };

export type CourseVariant = "white" | "orange" | "lavender" | "green";
export type PillStyle = "onWhite" | "onOrange" | "onLavender" | "onGreenLight";
export type Project = {
  id: string;
  label: string;
  title: string;
  description: string;
  url: string;
  gradient: [string, string];
};
export type Course = {
  id: string;
  title: string;
  description: string;
  variant: CourseVariant;
  pillStyle: PillStyle;
  mascot: "brain-bulb" | "drone" | "print-cube" | "skate-robot" | "maker-bench";
  pills: string[];
  footnote?: string;
  span?: 1 | 2;
};

export const site = {
  brand: {
    first: "SPARK",
    second: "LAB",
  },

  nav: {
    links: [
      { label: "Courses", href: "#courses" },
      { label: "Projects", href: "#projects" },
      { label: "About", href: "#about" },
      { label: "Schedule", href: "#schedule" },
    ] as NavLink[],
    cta: { label: "Book a Trial", href: "#cta" } as NavLink,
  },

  hero: {
    // Each inner array is one H1 line; segments are words or inline mascots.
    heading: [
      [{ text: "Curious" }, { text: "Kids." }],
      [{ text: "Real" }, { mascot: "drone" }, { text: "Machines." }],
      [{ mascot: "bulb" }, { text: "Big" }, { text: "Futures." }],
    ] as HeroSegment[][],
    paragraph:
      "SparkLab is a neighborhood tech school where children aged 6-14 learn AI, 3D printing, drone piloting and robotics - by building real things with their own hands.",
    primaryCta: { label: "Book a Free Trial", href: "#cta" } as NavLink,
    secondaryCta: { label: "Explore Courses", href: "#courses" } as NavLink,
    meta: "AGES 6-14 · MAX 12 PER CLASS · ALL EQUIPMENT PROVIDED",
  },

  courses: [
    {
      id: "ai-ml",
      title: "AI & Machine Learning",
      variant: "white",
      pillStyle: "onWhite",
      mascot: "brain-bulb",
      span: 2,
      description:
        "Kids train real models to recognize drawings, sounds and gestures - then bend them into games, art generators and chatbots.",
      pills: ["Ages 8-14", "Train real models", "Games & art"],
    },
    {
      id: "drone-school",
      title: "Drone Flight School",
      variant: "orange",
      pillStyle: "onOrange",
      mascot: "drone",
      span: 1,
      description:
        "From first hover to full flight plans. Kids learn aerodynamics, safety checks and stick time with drones in our indoor field.",
      pills: ["Ages 7-14", "Indoor field", "Safety checks"],
    },
    {
      id: "3d-print-lab",
      title: "3D Print Lab",
      variant: "lavender",
      pillStyle: "onLavender",
      mascot: "print-cube",
      span: 1,
      description:
        "Sketch it, model it, print it. Kids design their own toys, tools and inventions, then watch them appear layer by layer on our printer farm.",
      pills: ["Ages 7-14", "Design software", "Prints go home"],
      footnote: "Every project leaves in a backpack.",
    },
    {
      id: "robot-builders",
      title: "Robot Builders",
      variant: "green",
      pillStyle: "onGreenLight",
      mascot: "skate-robot",
      span: 1,
      description:
        "Assemble, wire and program rolling, grabbing, sensing robots. Younger builders start with blocks; older ones graduate to Python.",
      pills: ["Ages 6-12", "Scratch → Python", "Team builds"],
      footnote: "From first circuit to full autonomy.",
    },
    {
      id: "weekend-camps",
      title: "Weekend Maker Camps",
      variant: "white",
      pillStyle: "onWhite",
      mascot: "maker-bench",
      span: 1,
      description:
        "School holidays mean build weeks: five days, one big invention, and a Friday demo where kids present their creations to family.",
      pills: ["Ages 6-14", "School holidays", "Materials included"],
      footnote: "Next camp: autumn half-term - places are limited.",
    },
  ] as Course[],

  projects: [
    {
      id: "print-farm",
      label: "3D Print Lab",
      title: "The Print Farm",
      description:
        "A weekend of modeling and printing: kids designed a whole zoo of dinosaurs and rockets, then watched them appear layer by layer.",
      url: "/print-farm",
      gradient: ["#DDB9FB", "#8B5CF6"],
    },
    {
      id: "first-flight",
      label: "Drone Flight School",
      title: "First Solo Flight",
      description:
        "After weeks of sim time and safety checks, our junior pilots flew their first fully solo obstacle course in the indoor field.",
      url: "/first-flight",
      gradient: ["#BFE3C4", "#0F7B3F"],
    },
    {
      id: "robo-pet",
      label: "Robot Builders",
      title: "Robo-Pet",
      description:
        "Rolling, sensing, and a little bit opinionated — teams wired and programmed desk-sized pets that react to sound and touch.",
      url: "/robo-pet",
      gradient: ["#FFD9C2", "#FF4F00"],
    },
    {
      id: "dream-machine",
      label: "AI Studio",
      title: "Dream Machine",
      description:
        "Kids trained a model on their own doodles, then built a gallery where the AI dreams up brand-new creatures in real time.",
      url: "/dream-machine",
      gradient: ["#CFE0FF", "#1D4ED8"],
    },
  ] as Project[],

  marquee: ["AI", "3D Printing", "Drones", "Robotics"],

  schedule: {
    tabs: [
      {
        id: "weekdays",
        label: "Weekdays",
        classes: [
          { time: "Mon · 4:00 PM", course: "Robot Builders", ages: "Ages 6-12", seats: 3 },
          { time: "Tue · 5:30 PM", course: "AI & Machine Learning", ages: "Ages 8-14", seats: 5 },
          { time: "Wed · 4:00 PM", course: "3D Print Lab", ages: "Ages 7-14", seats: 2 },
          { time: "Thu · 6:00 PM", course: "Drone Flight School", ages: "Ages 7-14", seats: 6 },
        ],
      },
      {
        id: "weekends",
        label: "Weekends",
        classes: [
          { time: "Sat · 10:00 AM", course: "Robot Builders", ages: "Ages 6-12", seats: 4 },
          { time: "Sat · 1:00 PM", course: "AI & Machine Learning", ages: "Ages 8-14", seats: 1 },
          { time: "Sun · 11:00 AM", course: "3D Print Lab", ages: "Ages 7-14", seats: 7 },
        ],
      },
      {
        id: "camps",
        label: "Holiday Camps",
        classes: [
          { time: "Autumn · 5 days", course: "Weekend Maker Camps", ages: "Ages 6-14", seats: 8 },
          { time: "Winter · 5 days", course: "Game Jam Camp", ages: "Ages 9-14", seats: 2 },
        ],
      },
    ],
  },

  howItWorks: {
    steps: [
      { n: "01", title: "Book a trial", desc: "Pick a free slot online. One hands-on class, no commitment, all gear provided." },
      { n: "02", title: "Meet the mentor", desc: "A short chat to understand what your kid loves and where to start building." },
      { n: "03", title: "Start building", desc: "They join a small crew and take home something they designed and made themselves." },
    ],
  },

  about: {
    heading: "Small classes. Real tools. Big confidence.",
    body:
      "SparkLab started in 2018 with four kids, one 3D printer and a pile of cardboard. Today we keep every class tiny so every child gets real time at the bench — with mentors who treat their ideas seriously.",
    stats: [
      { to: 12, prefix: "", suffix: "", label: "max per class" },
      { to: 14, prefix: "6–", suffix: "", label: "years of age" },
      { to: 4, prefix: "", suffix: "", label: "core tracks" },
    ],
    mentors: [
      { name: "Ananya Rao", role: "Robotics Lead", gradient: ["#DDB9FB", "#8B5CF6"] },
      { name: "Vikram Shetty", role: "AI & Data Mentor", gradient: ["#CFE0FF", "#1D4ED8"] },
      { name: "Meera Nair", role: "3D Design Coach", gradient: ["#FFD9C2", "#FF4F00"] },
      { name: "Rohan Gupta", role: "Drone Instructor", gradient: ["#BFE3C4", "#0F7B3F"] },
    ],
  },

  testimonials: {
    quotes: [
      { quote: "My daughter went from ‘I can’t’ to demoing her own robot at the Friday showcase in one term. The mentors are magic.", name: "Priya S.", meta: "Parent, Robot Builders", variant: "white" },
      { quote: "The class size is the whole point — every kid actually gets hands on the tools. He comes home buzzing every single time.", name: "Amit K.", meta: "Parent, 3D Print Lab", variant: "lavender" },
      { quote: "I was skeptical about screen-time, but this is the opposite. They build, fly and fix real things together.", name: "Fatima R.", meta: "Parent, Drone Flight School", variant: "green" },
    ],
  },

  faq: {
    items: [
      { q: "Do kids need any experience?", a: "None at all. Every track starts from zero and mentors meet each child where they are — younger builders use blocks, older ones graduate to Python." },
      { q: "What should my child bring?", a: "Just themselves. All hardware, software, safety gear and materials are provided, and 3D prints go home in their backpack." },
      { q: "Is it safe around drones?", a: "Yes. Flight happens in our indoor field with certified instructors, geo-fenced drones and a strict safety-check routine every class." },
      { q: "How do holiday camps work?", a: "Five build days, one big invention, and a Friday demo where kids present their creations to family. Places are limited and fill fast." },
    ],
  },

  cta: {
    title: "Book a free trial class",
    subtitle: "Tell us a little about your young maker and we’ll set up a hands-on session.",
    courseOptions: ["AI & Machine Learning", "Drone Flight School", "3D Print Lab", "Robot Builders", "Weekend Maker Camps"],
    ageOptions: ["6", "7", "8", "9", "10", "11", "12", "13", "14"],
    success: "Thanks! We’ll be in touch within a day to lock in the trial slot.",
  },

  footer: {
    blurb:
      "SparkLab is a neighborhood tech school where children aged 6–14 learn AI, 3D printing, drone piloting and robotics — by building real things with their own hands.",
    quickLinks: [
      { label: "Courses", href: "#courses" },
      { label: "Projects", href: "#projects" },
      { label: "About", href: "#about" },
      { label: "Schedule", href: "#schedule" },
    ] as NavLink[],
    contact: {
      address: "221B Green Lane, Sector 14, Gurugram",
      phone: "+91 98765 43210",
      email: "hello@sparklab.in",
    },
    newsletter: {
      title: "Get the term calendar",
      placeholder: "you@example.com",
      buttonLabel: "Subscribe",
    },
    copyright: "© 2026 SparkLab. All rights reserved.",
    // NOTE: brand icons were dropped from this lucide-react version, so we use
    // honest generic placeholders (replaceable later per master rule #2).
    socials: [
      { label: "Instagram", href: "#", icon: "at-sign" },
      { label: "Community", href: "#", icon: "message-circle" },
      { label: "Newsletter", href: "#", icon: "send" },
      { label: "Website", href: "#", icon: "globe" },
    ] as Array<{ label: string; href: string; icon: string }>,
  },
};
