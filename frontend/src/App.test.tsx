import { render, screen } from "@testing-library/react";

import App from "./App";
import "./i18n";

// Frontend smoke test (PHASE_0 task 9).
test("renders the app title heading", () => {
  render(<App />);
  expect(
    screen.getByRole("heading", { name: /KaushalPath/i }),
  ).toBeInTheDocument();
});
