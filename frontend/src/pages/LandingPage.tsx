import React from 'react';
import { motion, useReducedMotion, type Variants } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Link } from 'wouter';
import { ArrowDown, Briefcase, GraduationCap, Users } from 'lucide-react';
import { Layout } from '../components/layout/Layout';
import { Section } from '../components/ui/Section';
import { SectionHeading } from '../components/ui/SectionHeading';
import { WaveButton } from '../components/ui/WaveButton';
import { Marquee } from '../components/ui/Marquee';
import { useReveal } from '../hooks/interactions';
import { EASE } from '../lib/motion';
import { cn } from '../lib/cn';

/**
 * App entry (`/`) — the KaushalPath product intro, dressed in the same
 * SparkLab design language as the marketing shell on `/home`: pale-lime page,
 * ink type, orange/green/lavender surfaces, pill CTAs, 32px cards, word-reveal
 * headings and scroll reveals. All copy comes from the i18n dictionaries
 * (`landing.*`), because this page is part of the app UI, not the marketing
 * site (`src/content/site.ts`).
 */

/** i18n arrays are only typed as arrays when `returnObjects` is honoured; the
 *  test mock returns the key, so guard before mapping. */
const list = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

const WORD_CONTAINER: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.1 } },
};
const WORD: Variants = {
  hidden: { y: 40, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { duration: 0.6, ease: EASE } },
};

/** Decorative product preview — the app's own vocabulary, marked aria-hidden. */
const PreviewCard: React.FC<{
  title: string;
  demoBadge: string;
  reasonsLabel: string;
  chips: string[];
}> = ({ title, demoBadge, reasonsLabel, chips }) => {
  const rows = [
    { name: 'Solar Technician', score: 92, tone: 'bg-green' },
    { name: 'Nursing Assistant', score: 87, tone: 'bg-orange-deep' },
    { name: 'IT Support Technician', score: 81, tone: 'bg-ink' },
  ];
  return (
    <div
      aria-hidden
      className="relative w-full max-w-[480px] rounded-card border border-ink/10 bg-cardwhite p-6 shadow-[0_24px_60px_-30px_rgba(10,10,10,.45)] md:p-8"
    >
      <div className="flex items-center justify-between gap-4">
        <span className="font-mono text-sm font-bold text-ink">{title}</span>
        <span className="rounded-pill bg-lavender px-3 py-1 font-mono text-[11px] font-semibold uppercase text-[#2A2A2A]">
          {demoBadge}
        </span>
      </div>

      <ul className="mt-5 space-y-3">
        {rows.map((r, i) => (
          <motion.li
            key={r.name}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.55 + i * 0.12, duration: 0.5, ease: EASE }}
            className="flex items-center gap-4 rounded-inner bg-page/70 px-4 py-3"
          >
            <span className="font-mono text-sm font-bold text-muted">{i + 1}</span>
            <span className="flex-1 truncate font-mono text-sm font-semibold text-ink">{r.name}</span>
            <span className={cn('rounded-pill px-3 py-1 font-mono text-xs font-bold text-white', r.tone)}>
              {r.score}%
            </span>
          </motion.li>
        ))}
      </ul>

      <p className="mt-6 font-mono text-[11px] uppercase tracking-[0.16em] text-muted">{reasonsLabel}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {chips.map((c) => (
          <span key={c} className="rounded-pill bg-page px-3 py-1 font-mono text-[11px] text-muted">
            {c}
          </span>
        ))}
      </div>

      {/* Floating factor badge, echoing the marketing hero characters. */}
      <motion.span
        className="absolute -right-4 -top-6 hidden rounded-card bg-ink px-5 py-4 font-mono text-xs font-bold text-white shadow-lg md:block"
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
      >
        {chips[0] ?? ''}
      </motion.span>
    </div>
  );
};

/** Step / feature / audience card tones, shared with the marketing bento. */
const TONES = {
  white: { card: 'bg-cardwhite border-ink/10', title: 'text-ink', body: 'text-muted' },
  orange: { card: 'bg-orange-deep border-transparent', title: 'text-white', body: 'text-white/90' },
  lavender: { card: 'bg-lavender border-transparent', title: 'text-[#2A2A2A]', body: 'text-[#2A2A2A]/80' },
  green: { card: 'bg-green border-transparent', title: 'text-white', body: 'text-white/90' },
} as const;

type Tone = keyof typeof TONES;

const StepCard: React.FC<{ n: string; title: string; desc: string; tone: Tone; index: number }> = ({
  n,
  title,
  desc,
  tone,
  index,
}) => {
  const reveal = useReveal(index * 0.12);
  const t = TONES[tone];
  return (
    <motion.div
      {...reveal}
      whileHover={{ y: -8 }}
      className={cn('flex min-h-[300px] flex-col rounded-card border p-10', t.card)}
    >
      <span
        aria-hidden
        className="font-mono font-bold leading-none"
        style={{ fontSize: 96, color: 'transparent', WebkitTextStroke: `2px ${tone === 'lavender' ? 'rgba(42,42,42,.35)' : 'rgba(255,255,255,.5)'}` }}
      >
        {n}
      </span>
      <h3 className={cn('mt-4 font-mono text-2xl font-bold', t.title)}>{title}</h3>
      <p className={cn('mt-3 font-mono text-[15px] leading-relaxed', t.body)}>{desc}</p>
    </motion.div>
  );
};

const FeatureCard: React.FC<{
  title: string;
  desc: string;
  tone: Tone;
  wide: boolean;
  index: number;
}> = ({ title, desc, tone, wide, index }) => {
  const reveal = useReveal(index * 0.08);
  const t = TONES[tone];
  return (
    <motion.div
      {...reveal}
      whileHover={{ y: -8 }}
      className={cn(
        'flex flex-col justify-between rounded-card border p-8 min-[700px]:p-10',
        t.card,
        wide && 'min-[700px]:col-span-2',
      )}
    >
      <h3 className={cn('font-mono text-2xl font-bold md:text-[28px]', t.title)}>{title}</h3>
      <p className={cn('mt-4 max-w-[46ch] font-mono text-[15px] leading-relaxed', t.body)}>{desc}</p>
    </motion.div>
  );
};

const AUDIENCE_ICONS = [GraduationCap, Users, Briefcase] as const;

const AudienceCard: React.FC<{
  title: string;
  desc: string;
  Icon: typeof GraduationCap;
  index: number;
}> = ({ title, desc, Icon, index }) => {
  const reveal = useReveal(index * 0.1);
  return (
    <motion.div
      {...reveal}
      whileHover={{ y: -8 }}
      className="rounded-card border border-ink/10 bg-cardwhite p-10"
    >
      <span className="inline-flex h-14 w-14 items-center justify-center rounded-pill bg-page text-orange-deep">
        <Icon size={26} aria-hidden />
      </span>
      <h3 className="mt-6 font-mono text-2xl font-bold text-ink">{title}</h3>
      <p className="mt-3 font-mono text-[15px] leading-relaxed text-muted">{desc}</p>
    </motion.div>
  );
};

const AppFooter: React.FC<{
  blurb: string;
  exploreLabel: string;
  productLabel: string;
  exploreLinks: { label: string; href: string }[];
  links: { label: string; href: string }[];
  copyright: string;
}> = ({ blurb, exploreLabel, productLabel, exploreLinks, links, copyright }) => {
  return (
    <footer className="mt-24 bg-ink text-white">
      <div className="mx-auto w-full max-w-container rounded-t-[48px] px-5 py-16 md:px-10">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-3">
          <div>
            <p className="font-display text-[26px] font-extrabold leading-none tracking-[-0.03em]">
              <span className="text-white">Kaushal</span>
              <span className="text-orange">Path</span>
            </p>
            <p className="mt-4 max-w-[34ch] text-sm leading-relaxed text-white/70">{blurb}</p>
          </div>

          <nav aria-label="On this page">
            <h3 className="font-mono text-sm font-semibold uppercase tracking-wide text-white/60">
              {exploreLabel}
            </h3>
            <ul className="mt-5 space-y-3">
              {exploreLinks.map((a) => (
                <li key={a.href}>
                  <a href={a.href} className="link-underline text-white/70 transition-colors hover:text-white">
                    {a.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <nav aria-label="Product">
            <h3 className="font-mono text-sm font-semibold uppercase tracking-wide text-white/60">
              {productLabel}
            </h3>
            <ul className="mt-5 space-y-3">
              {links.map((l) => (
                <li key={l.label}>
                  <Link
                    href={l.href}
                    className="link-underline text-white/70 transition-colors hover:text-white"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <p className="mt-14 border-t border-white/10 pt-8 font-mono text-xs text-white/50">{copyright}</p>
      </div>
    </footer>
  );
};

export const LandingPage: React.FC = () => {
  const { t } = useTranslation();
  const reduced = useReducedMotion();

  const marquee = list<string>(t('landing.marquee', { returnObjects: true }));
  const steps = list<{ n: string; title: string; desc: string }>(
    t('landing.how.steps', { returnObjects: true }),
  );
  const features = list<{ title: string; desc: string; tone: Tone; span: 'yes' | 'no' }>(
    t('landing.features.items', { returnObjects: true }),
  );
  const audience = list<{ title: string; desc: string }>(t('landing.who.items', { returnObjects: true }));

  const titleWords = t('landing.title').split(' ');
  const stepTones: Tone[] = ['lavender', 'green', 'orange'];
  const navLinks = [
    { label: t('landing.nav.how'), href: '#how' },
    { label: t('landing.nav.features'), href: '#features' },
    { label: t('landing.nav.who'), href: '#who' },
  ];

  return (
    <Layout
      navbar={{
        brand: { first: 'Kaushal', second: 'Path' },
        links: navLinks,
        cta: { label: t('landing.start_button'), href: '/register' },
      }}
      footer={
        <AppFooter
          blurb={t('landing.footer.blurb')}
          exploreLabel={t('landing.footer.explore')}
          productLabel={t('landing.footer.product')}
          copyright={t('landing.footer.copyright')}
          exploreLinks={navLinks}
          links={[
            { label: t('landing.footer.start'), href: '/register' },
            { label: t('landing.footer.login'), href: '/login' },
            { label: t('landing.footer.counsellor'), href: '/login' },
            { label: t('landing.footer.room'), href: '/room/join' },
            { label: t('landing.footer.styleguide'), href: '/styleguide' },
            { label: t('landing.footer.marketing'), href: '/home' },
          ]}
        />
      }
    >
      {/* ---------------- HERO ---------------- */}
      <section className="relative mx-auto grid w-full max-w-container grid-cols-1 items-center gap-12 px-5 pb-16 pt-32 md:px-10 lg:grid-cols-[1.2fr_1fr] lg:pt-40">
        <div>
          <motion.h1
            variants={reduced ? undefined : WORD_CONTAINER}
            initial="hidden"
            animate="show"
            className="font-sans font-bold tracking-heading text-ink"
            style={{ fontSize: 'clamp(2.75rem, 7vw, 6.5rem)', lineHeight: 1.08 }}
          >
            {titleWords.map((w, i) =>
              reduced ? (
                <React.Fragment key={i}>
                  {w}
                  {i < titleWords.length - 1 ? ' ' : ''}
                </React.Fragment>
              ) : (
                <motion.span key={i} variants={WORD} className="mr-[0.25em] inline-block">
                  {w}
                </motion.span>
              ),
            )}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45, duration: 0.6, ease: EASE }}
            className="mt-8 max-w-[45ch] text-[22px] leading-[1.7] text-muted"
          >
            {t('landing.subtitle')}
          </motion.p>

          <div className="mt-10 flex flex-wrap items-center gap-8">
            <WaveButton label={t('landing.start_button')} href="/register" />
            <Link
              href="#how"
              className="group inline-flex items-center gap-2 font-mono text-[17px] font-semibold text-ink"
            >
              <span className="relative">
                {t('landing.scroll_hint')}
                <span className="absolute -bottom-1 left-0 h-[2px] w-full origin-left bg-orange transition-colors duration-300 group-hover:bg-ink" />
              </span>
              <ArrowDown size={18} className="transition-transform duration-300 group-hover:translate-y-1" />
            </Link>
          </div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8, duration: 0.6 }}
            className="mt-14 font-mono text-[13px] uppercase tracking-[0.2em] text-[#8A8A7A]"
          >
            {t('landing.meta')}
          </motion.p>
        </div>

        {/* RIGHT — product preview */}
        <div className="relative mx-auto flex w-full max-w-[520px] justify-center">
          <PreviewCard
            title={t('results.title')}
            demoBadge={t('results.demo_badge')}
            reasonsLabel={t('career.reasons')}
            chips={[t('weights.cost'), t('weights.local_jobs'), t('weights.distance')]}
          />
        </div>
      </section>

      <Marquee words={marquee} />

      {/* ---------------- HOW IT WORKS ---------------- */}
      <Section id="how">
        <SectionHeading title={t('landing.how.title')} subtitle={t('landing.how.subtitle')} />
        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3">
          {steps.map((s, i) => (
            <StepCard key={s.n ?? i} n={s.n} title={s.title} desc={s.desc} tone={stepTones[i % 3]} index={i} />
          ))}
        </div>
      </Section>

      {/* ---------------- FEATURES BENTO ---------------- */}
      <Section id="features">
        <SectionHeading title={t('landing.features.title')} subtitle={t('landing.features.subtitle')} />
        <div className="mt-14 grid grid-cols-1 gap-[25px] min-[700px]:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <FeatureCard
              key={`${f.title}-${i}`}
              title={f.title}
              desc={f.desc}
              tone={f.tone}
              wide={f.span === 'yes'}
              index={i}
            />
          ))}
        </div>
      </Section>

      {/* ---------------- WHO ---------------- */}
      <Section id="who">
        <SectionHeading title={t('landing.who.title')} subtitle={t('landing.who.subtitle')} />
        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3">
          {audience.map((a, i) => (
            <AudienceCard
              key={`${a.title}-${i}`}
              title={a.title}
              desc={a.desc}
              Icon={AUDIENCE_ICONS[i % AUDIENCE_ICONS.length]}
              index={i}
            />
          ))}
        </div>
      </Section>

      {/* ---------------- CTA ---------------- */}
      <Section id="cta">
        <div className="overflow-hidden rounded-[48px] bg-orange-deep px-6 py-16 text-white md:px-16 md:py-20">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="font-sans text-4xl font-bold tracking-heading md:text-5xl">{t('landing.cta.title')}</h2>
            <p className="mx-auto mt-4 max-w-[46ch] font-mono text-[17px] leading-relaxed text-white/90">
              {t('landing.cta.subtitle')}
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-5">
              <WaveButton label={t('landing.cta.start')} href="/register" />
              <Link
                href="/login"
                className="inline-flex h-[60px] min-w-[265px] items-center justify-center rounded-full border-2 border-white px-8 font-mono text-lg font-bold text-white transition-colors hover:bg-white hover:text-orange-deep focus:outline-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ink focus-visible:ring-offset-[3px] focus-visible:ring-offset-orange-deep"
              >
                {t('landing.cta.login')}
              </Link>
            </div>
            <p className="mt-8 font-mono text-sm text-white/80">
              <Link href="/login" className="link-underline">
                {t('landing.cta.counsellor')}
              </Link>
            </p>
          </div>
        </div>
      </Section>
    </Layout>
  );
};

export default LandingPage;
