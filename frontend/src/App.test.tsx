import { test, expect, vi } from "vitest";
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

test("renders the app title heading", () => {
  render(<App />);
  expect(
    screen.getByRole("heading", { name: /KaushalPath/i }),
  ).toBeInTheDocument();
});
