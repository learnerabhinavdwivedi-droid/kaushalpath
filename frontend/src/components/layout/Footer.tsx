import React from "react";
import {
  AtSign,
  MessageCircle,
  Send,
  Globe,
  Mail,
  Phone,
  MapPin,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";
import { site } from "../../content/site";

const SOCIAL_ICONS: Record<string, LucideIcon> = {
  "at-sign": AtSign,
  "message-circle": MessageCircle,
  send: Send,
  globe: Globe,
};

const footerLink = "link-underline text-white/70 hover:text-white transition-colors";

export const Footer: React.FC = () => (
  <footer className="mt-24 bg-ink text-white">
    <div className="mx-auto w-full max-w-container rounded-t-[48px] px-5 py-16 md:px-10 md:py-20">
      <div className="grid grid-cols-1 gap-12 md:grid-cols-2 lg:grid-cols-4">
        {/* Brand */}
        <div>
          <a href="#top" className="font-display text-[26px] font-extrabold leading-none tracking-[-0.03em]">
            <span className="text-white">{site.brand.first}</span>
            <span className="text-orange">{site.brand.second}</span>
          </a>
          <p className="mt-4 max-w-[34ch] text-sm leading-relaxed text-white/60">
            {site.footer.blurb}
          </p>
        </div>

        {/* Quick links */}
        <nav aria-label="Footer">
          <h3 className="font-mono text-sm font-semibold uppercase tracking-wide text-white/60">
            Explore
          </h3>
          <ul className="mt-5 space-y-3">
            {site.footer.quickLinks.map((link) => (
              <li key={link.href}>
                <a href={link.href} className={footerLink}>
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        {/* Contact */}
        <div>
          <h3 className="font-mono text-sm font-semibold uppercase tracking-wide text-white/60">
            Contact
          </h3>
          <ul className="mt-5 space-y-3 text-sm text-white/70">
            <li className="flex items-start gap-3">
              <MapPin size={18} className="mt-0.5 shrink-0 text-orange" />
              <span>{site.footer.contact.address}</span>
            </li>
            <li className="flex items-center gap-3">
              <Phone size={18} className="shrink-0 text-orange" />
              <a href={`tel:${site.footer.contact.phone}`} className={footerLink}>
                {site.footer.contact.phone}
              </a>
            </li>
            <li className="flex items-center gap-3">
              <Mail size={18} className="shrink-0 text-orange" />
              <a href={`mailto:${site.footer.contact.email}`} className={footerLink}>
                {site.footer.contact.email}
              </a>
            </li>
          </ul>
        </div>

        {/* Newsletter */}
        <div>
          <h3 className="font-mono text-sm font-semibold uppercase tracking-wide text-white/60">
            {site.footer.newsletter.title}
          </h3>
          <form
            className="mt-5"
            onSubmit={(e) => e.preventDefault()}
          >
            <div className="flex items-center gap-2 rounded-pill bg-white/10 p-1.5 pl-5">
              <label htmlFor="newsletter-email" className="sr-only">
                Email address
              </label>
              <input
                id="newsletter-email"
                type="email"
                required
                placeholder={site.footer.newsletter.placeholder}
                className="w-full bg-transparent font-mono text-sm text-white placeholder:text-white/40 focus:outline-none"
              />
              <button
                type="submit"
                aria-label={site.footer.newsletter.buttonLabel}
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-pill bg-orange text-white transition-transform hover:scale-105 active:scale-95"
              >
                <ArrowRight size={18} />
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Bottom row */}
      <div className="mt-14 flex flex-col items-center justify-between gap-6 border-t border-white/10 pt-8 sm:flex-row">
        <p className="font-mono text-xs text-white/50">{site.footer.copyright}</p>
        <ul className="flex items-center gap-3">
          {site.footer.socials.map((social) => {
            const Icon = SOCIAL_ICONS[social.icon] ?? Globe;
            return (
              <li key={social.label}>
                <a
                  href={social.href}
                  aria-label={social.label}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-pill bg-white/10 text-white/70 transition-colors hover:bg-orange hover:text-white"
                >
                  <Icon size={18} />
                </a>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  </footer>
);
