import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import ThemeToggle from "./ThemeToggle";

function installMatchMediaStub(initialMatches: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: initialMatches,
      media: "(prefers-color-scheme: dark)",
      addEventListener: () => {},
      removeEventListener: () => {},
    })),
  );
}

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
    installMatchMediaStub(false);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.documentElement.classList.remove("dark");
  });

  it("renders exactly three buttons with the accessible names Light theme, Dark theme, System theme", () => {
    render(<ThemeToggle />);

    expect(screen.getByRole("button", { name: "Light theme" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dark theme" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "System theme" })).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(3);
  });

  it("carries exactly one aria-pressed=true button reflecting the default (system) choice", () => {
    render(<ThemeToggle />);

    const pressed = screen
      .getAllByRole("button")
      .filter((btn) => btn.getAttribute("aria-pressed") === "true");
    expect(pressed).toHaveLength(1);
    expect(pressed[0]).toBe(screen.getByRole("button", { name: "System theme" }));
  });

  it("moves aria-pressed=true to the clicked button and away from the previous one", () => {
    render(<ThemeToggle />);

    fireEvent.click(screen.getByRole("button", { name: "Dark theme" }));

    expect(screen.getByRole("button", { name: "Dark theme" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "System theme" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );

    const pressed = screen
      .getAllByRole("button")
      .filter((btn) => btn.getAttribute("aria-pressed") === "true");
    expect(pressed).toHaveLength(1);
  });
});
