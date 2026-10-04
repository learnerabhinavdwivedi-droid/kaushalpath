import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "wouter";
import { Menu, X } from "lucide-react";
import { site, type NavLink } from "../../content/site";
import { useScrolled } from "../../hooks/useScrolled";
import { useActiveSection } from "../../hooks/useActiveSection";
import { cn } from "../../lib/cn";

/**
 * The shell is shared by the marketing page (`/home`) and the themed app entry
 * (`/`), so brand / links / CTA are props that default to the marketing nav.
 */
export type NavbarProps = {
  brand?: { first: string; second: string };
  links?: NavLink[];
  cta?: NavLink;
};

const Logo: React.FC<{ brand: { first: string; second: string }; onClick?: () => void }> = ({
  brand,
  onClick,
}) => (
  <a
    href="#top"
    onClick={onClick}
    className="font-display text-[26px] font-extrabold leading-none tracking-[-0.03em]"
  >
    <span className="text-ink">{brand.first}</span>
    <span className="text-orange">{brand.second}</span>
  </a>
);

const TrialButton: React.FC<{ cta: NavLink }> = ({ cta }) => {
  const inner = (
    <>
      <span className="absolute inset-0 translate-y-full bg-orange-deep transition-transform duration-[350ms] ease-out group-hover:translate-y-0" />
      <span className="relative">{cta.label}</span>
    </>
  );
  const cls =
    "group relative hidden shrink-0 overflow-hidden rounded-full bg-ink px-[26px] py-[14px] font-mono text-base font-semibold text-white min-[900px]:inline-block";

  return cta.href.startsWith("#") ? (
    <motion.a
      href={cta.href}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className={cls}
    >
      {inner}
    </motion.a>
  ) : (
    <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} className="hidden min-[900px]:block">
      <Link href={cta.href} className={cls}>
        {inner}
      </Link>
    </motion.div>
  );
};

export const Navbar: React.FC<NavbarProps> = ({
  brand = site.brand,
  links = site.nav.links,
  cta = site.nav.cta,
}) => {
  const scrolled = useScrolled(80);
  const sectionIds = useMemo(() => links.map((l) => l.href.replace("#", "")), [links]);
  const active = useActiveSection(sectionIds);
  const [hovered, setHovered] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const menuBtnRef = useRef<HTMLButtonElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const highlight = hovered ?? active;

  const closeMenu = () => {
    setOpen(false);
    menuBtnRef.current?.focus();
  };

  // A11y: while the overlay is open — focus the close button, trap Tab,
  // close on Esc and lock background scroll.
  useEffect(() => {
    if (!open) return;
    closeBtnRef.current?.focus();
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeMenu();
        return;
      }
      if (e.key !== "Tab") return;
      const focusables = overlayRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled])',
      );
      if (!focusables || focusables.length === 0) return;
      const list = Array.from(focusables);
      const first = list[0];
      const last = list[list.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <>
      <motion.header
        initial={false}
        animate={{ top: scrolled ? 12 : 24, height: scrolled ? 64 : 80 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className={cn(
          "fixed left-4 right-4 z-50 rounded-pill px-6 md:left-10 md:right-10 md:px-9",
          scrolled
            ? "bg-white/85 shadow-[0_1px_0_rgba(0,0,0,.04)] backdrop-blur-md"
            : "bg-white shadow-[0_1px_0_rgba(0,0,0,.04)]",
        )}
      >
        <div className="relative flex h-full items-center justify-between">
          <Logo brand={brand} />

          {/* Center links — absolutely centered, hidden below 900px */}
          <nav
            className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-10 min-[900px]:flex"
            onMouseLeave={() => setHovered(null)}
          >
            {links.map((link) => {
              const id = link.href.replace("#", "");
              const isHighlighted = highlight === id;
              const isActive = active === id;
              return (
                <a
                  key={link.href}
                  href={link.href}
                  onMouseEnter={() => setHovered(id)}
                  className={cn(
                    "relative px-1 py-2 font-mono text-base transition-colors",
                    isActive || isHighlighted
                      ? "font-semibold text-ink"
                      : "text-muted",
                  )}
                >
                  <AnimatePresence>
                    {isHighlighted && (
                      <motion.span
                        layoutId="nav-pill"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ type: "spring", stiffness: 400, damping: 32 }}
                        className="absolute inset-0 -z-10 rounded-pill bg-black/[0.06]"
                      />
                    )}
                  </AnimatePresence>
                  {link.label}
                </a>
              );
            })}
          </nav>

          <div className="flex items-center gap-3">
            <TrialButton cta={cta} />
            {/* Hamburger — only below 900px */}
            <button
              ref={menuBtnRef}
              type="button"
              aria-label="Open menu"
              aria-expanded={open}
              onClick={() => setOpen(true)}
              className="inline-flex h-11 w-11 items-center justify-center rounded-pill bg-ink text-white min-[900px]:hidden"
            >
              <Menu size={22} />
            </button>
          </div>
        </div>
      </motion.header>

      {/* Full-screen mobile overlay */}
      <AnimatePresence>
        {open && (
          <motion.div
            ref={overlayRef}
            role="dialog"
            aria-modal="true"
            aria-label="Site menu"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="fixed inset-0 z-[60] flex flex-col bg-page px-6 py-6 min-[900px]:hidden"
          >
            <div className="flex items-center justify-between">
              <Logo brand={brand} onClick={closeMenu} />
              <button
                ref={closeBtnRef}
                type="button"
                aria-label="Close menu"
                onClick={closeMenu}
                className="inline-flex h-11 w-11 items-center justify-center rounded-pill bg-ink text-white"
              >
                <X size={22} />
              </button>
            </div>

            <nav className="mt-16 flex flex-col gap-6">
              {links.map((link, i) => (
                <motion.a
                  key={link.href}
                  href={link.href}
                  onClick={closeMenu}
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.08 + i * 0.07, duration: 0.35 }}
                  className="font-mono text-[40px] font-bold leading-tight text-ink"
                >
                  {link.label}
                </motion.a>
              ))}
              {(() => {
                const overlayCta =
                  "mt-4 inline-flex w-fit items-center rounded-full bg-ink px-7 py-4 font-mono text-base font-semibold text-white";
                const anim = {
                  initial: { opacity: 0, y: 24 },
                  animate: { opacity: 1, y: 0 },
                  transition: { delay: 0.08 + links.length * 0.07, duration: 0.35 },
                } as const;
                return cta.href.startsWith("#") ? (
                  <motion.a key="cta-anchor" href={cta.href} onClick={closeMenu} {...anim} className={overlayCta}>
                    {cta.label}
                  </motion.a>
                ) : (
                  <motion.div key="cta-route" {...anim}>
                    <Link href={cta.href} onClick={closeMenu} className={overlayCta}>
                      {cta.label}
                    </Link>
                  </motion.div>
                );
              })()}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
