import React from "react";
import { MotionConfig } from "framer-motion";
import { Navbar, type NavbarProps } from "./Navbar";
import { Footer } from "./Footer";
import { CursorProvider } from "../ui/Cursor";
import { ScrollProgress } from "../ui/ScrollProgress";
import { HelpFab } from "../HelpFab";

/**
 * Shared shell: floating Navbar + page content + Footer.
 * MotionConfig reducedMotion="user" makes every child Framer-Motion transform
 * animation respect the OS "prefers-reduced-motion" setting (master rule #4).
 * CursorProvider adds the desktop-only custom cursor (Phase 7).
 * `navbar` / `footer` let the app entry (`/`) reuse the shell with its own
 * brand, links and footer content.
 */
export const Layout: React.FC<{
  children: React.ReactNode;
  navbar?: NavbarProps;
  footer?: React.ReactNode;
}> = ({ children, navbar, footer = <Footer /> }) => (
  <MotionConfig reducedMotion="user">
    <CursorProvider>
      <ScrollProgress />
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[110] focus:rounded-pill focus:bg-ink focus:px-6 focus:py-3 focus:font-mono focus:text-white"
      >
        Skip to content
      </a>
      <div id="top" className="flex min-h-screen flex-col bg-page text-ink">
        <Navbar {...navbar} />
        <main id="main" className="flex-1">{children}</main>
        {footer}
      </div>
      <HelpFab />
    </CursorProvider>
  </MotionConfig>
);
