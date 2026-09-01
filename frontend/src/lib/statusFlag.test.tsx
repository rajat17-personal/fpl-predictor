import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatusFlag } from "./statusFlag";

describe("StatusFlag", () => {
  it("renders nothing for an available player (status 'a')", () => {
    const { container } = render(<StatusFlag status="a" news="x" />);
    expect(container).toBeEmptyDOMElement();
  });

  it.each(["i", "s", "u", "n"])(
    "renders the ✕ glyph with accessible name 'unavailable' for status '%s'",
    (status) => {
      render(<StatusFlag status={status} news="" />);
      const btn = screen.getByRole("button", { name: "unavailable" });
      expect(btn).toHaveTextContent("✕");
    },
  );

  it("renders the ▲ glyph with accessible name 'doubtful' for status 'd'", () => {
    render(<StatusFlag status="d" news="" />);
    const btn = screen.getByRole("button", { name: "doubtful" });
    expect(btn).toHaveTextContent("▲");
  });

  it("reveals a role=tooltip element containing the news text on focus", () => {
    render(<StatusFlag status="i" news="Ankle knock" />);
    const btn = screen.getByRole("button", { name: "unavailable" });
    fireEvent.focus(btn);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Ankle knock");
  });

  it("falls back to the label word when news is empty", () => {
    render(<StatusFlag status="d" news="" />);
    const btn = screen.getByRole("button", { name: "doubtful" });
    fireEvent.focus(btn);
    expect(screen.getByRole("tooltip")).toHaveTextContent("doubtful");
  });

  it("clicking toggles aria-expanded, and Escape closes it", () => {
    render(<StatusFlag status="i" news="Ankle knock" />);
    const btn = screen.getByRole("button", { name: "unavailable" });
    expect(btn).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-expanded", "true");

    fireEvent.keyDown(document, { key: "Escape" });
    expect(btn).toHaveAttribute("aria-expanded", "false");
  });

  it("closes when clicking outside", () => {
    render(
      <div>
        <StatusFlag status="i" news="Ankle knock" />
        <button type="button">outside</button>
      </div>,
    );
    const btn = screen.getByRole("button", { name: "unavailable" });

    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(screen.getByRole("button", { name: "outside" }));
    expect(btn).toHaveAttribute("aria-expanded", "false");
  });
});
