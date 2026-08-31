import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import PageShell from "../components/PageShell";

/* Smoke test for the test harness itself, not for PageShell's design: proves
 * jsdom is present, JSX compiles under the TypeScript 6.0.3 pin, Testing
 * Library queries run, and the jest-dom matchers are registered. If this test
 * cannot be made to pass, the problem is the harness, not the component. */
describe("test harness", () => {
  it("renders PageShell and shows the footer disclaimer", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<PageShell />}>
            <Route index element={<div>content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(
      screen.getByText(/Not affiliated with the Premier League/i),
    ).toBeInTheDocument();
  });
});
