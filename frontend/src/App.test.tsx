import { test, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";
import "./i18n/config";

vi.mock("react-i18next", () => ({
  initReactI18next: {
    type: '3rdParty',
    init: vi.fn(),
  },
  useTranslation: () => ({
    t: (key: string) => {
      if (key === 'landing.title') return 'Welcome to KaushalPath';
      return key;
    },
    i18n: { language: 'en', changeLanguage: vi.fn() }
  })
}));

// The themed landing page reuses the marketing shell (custom cursor, active
// section observer, scroll reveals), so provide the browser APIs jsdom lacks.
beforeAll(() => {
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
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 0);
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
});

test("renders the app title heading", () => {
  render(<App />);
  expect(
    screen.getByRole("heading", { name: /KaushalPath/i }),
  ).toBeInTheDocument();
});
