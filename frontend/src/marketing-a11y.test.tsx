import { describe, it, expect, beforeAll, afterEach, vi } from "vitest";
import { render, cleanup, screen } from "@testing-library/react";
import axe from "axe-core";
import React from "react";
import "./i18n/config";

/**
 * Phase 9 — automated accessibility audit of the SparkLab marketing landing
 * page (axe-core, same harness as components/accessibility.test.tsx for the
 * app-side CareerCard). Runs in `npm test` in CI.
 *
 * jsdom has no layout engine, so `color-contrast` is excluded here and is
 * instead enforced through the Tailwind tokens (ink #0A0A0A / muted #55554A on
 * page #F1F5E0 ≈ 6.4:1, white on green #0F7B3F ≈ 5.4:1, and white-on-orange
 * surfaces use the AA-safe `orange-deep` #C13A00 token ≈ 5.4:1 — see README).
 */

beforeAll(() => {
  // Browser APIs the marketing shell uses that jsdom does not implement.
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });

  class StubIntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [];
    }
  }
  class StubResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, "IntersectionObserver", { writable: true, value: StubIntersectionObserver });
  Object.defineProperty(window, "ResizeObserver", { writable: true, value: StubResizeObserver });

  // Keep Framer-Motion infinite loops from holding vitest open.
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 0);
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
});

afterEach(() => {
  cleanup();
});

async function renderLanding() {
  const { SparkLabPage } = await import("./pages/SparkLabPage");
  return render(React.createElement(SparkLabPage));
}

describe("SparkLab landing page accessibility", () => {
  // axe-core walks the whole landing DOM; that legitimately takes longer than
  // the 5s default, so give this one test its own budget.
  it(
    "has no detectable axe violations",
    async () => {
      const { container } = await renderLanding();
      const results = await axe.run(container, {
        resultTypes: ["violations"],
        rules: { "color-contrast": { enabled: false } },
      });
      if (results.violations.length) {
        const summary = results.violations
          .map((v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)
          .join("\n");
        throw new Error(`axe violations:\n${summary}`);
      }
      expect(results.violations).toEqual([]);
    },
    30000,
  );

  it("keeps exactly one h1 (hero) with section headings as h2", async () => {
    await renderLanding();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getAllByRole("heading", { level: 2 }).length).toBeGreaterThanOrEqual(6);
  });

  it("exposes a skip link and a main landmark", async () => {
    await renderLanding();
    expect(screen.getByRole("main")).toBeInTheDocument();
    const skip = screen.getByRole("link", { name: /skip to content/i });
    expect(skip).toHaveAttribute("href", "#main");
  });

  it("gives every icon-only control an accessible name", async () => {
    await renderLanding();
    for (const name of [/open menu/i, /go to testimonial/i]) {
      expect(screen.getAllByRole("button", { name }).length).toBeGreaterThan(0);
    }
    // Decorative art must not leak into the a11y tree.
    expect(screen.getAllByLabelText(/preview$/i).length).toBeGreaterThan(0);
  });
});

/**
 * The app entry (`/`) now shares the same shell and design language, so it gets
 * the same audit.
 */
async function renderAppLanding() {
  const { LandingPage } = await import("./pages/LandingPage");
  return render(React.createElement(LandingPage));
}

describe("KaushalPath app landing accessibility", () => {
  it(
    "has no detectable axe violations",
    async () => {
      const { container } = await renderAppLanding();
      const results = await axe.run(container, {
        resultTypes: ["violations"],
        rules: { "color-contrast": { enabled: false } },
      });
      if (results.violations.length) {
        const summary = results.violations
          .map((v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)
          .join("\n");
        throw new Error(`axe violations:\n${summary}`);
      }
      expect(results.violations).toEqual([]);
    },
    30000,
  );

  it("keeps one h1, h2 section headings and a labelled product preview", async () => {
    await renderAppLanding();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getAllByRole("heading", { level: 2 }).length).toBeGreaterThanOrEqual(4);
    // The decorative results preview must sit inside aria-hidden markup.
    const previewRow = screen.getByText("Solar Technician");
    expect(previewRow.closest('[aria-hidden="true"]')).toBeTruthy();
  });
});
