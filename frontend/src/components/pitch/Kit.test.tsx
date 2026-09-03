import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { Kit } from "./Kit";

describe("Kit", () => {
  it("is aria-hidden — carries no information the card's name text does not", () => {
    const { container } = render(<Kit primary="#111111" secondary="#222222" pattern="plain" />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("uses a fixed viewBox so it scales at any card size", () => {
    const { container } = render(<Kit primary="#111111" secondary="#222222" pattern="plain" />);
    expect(container.querySelector("svg")).toHaveAttribute("viewBox", "0 0 32 32");
  });

  it("colours the shirt body from the primary/secondary props, not a hard-coded value", () => {
    const { container } = render(<Kit primary="#ABCDEF" secondary="#123456" pattern="plain" />);
    const path = container.querySelector("path");
    expect(path).toHaveAttribute("fill", "#ABCDEF");
    expect(path).toHaveAttribute("stroke", "#123456");
  });

  it.each(["plain", "stripes", "hoops", "sleeves"] as const)(
    "renders without crest, sponsor mark or external image for pattern '%s'",
    (pattern) => {
      const { container } = render(<Kit primary="#111111" secondary="#222222" pattern={pattern} />);
      expect(container.querySelector("image")).toBeNull();
      expect(container.querySelector("use")).toBeNull();
      expect(container.textContent).toBe("");
    },
  );

  it("draws stripes, hoops and sleeves with distinct extra shapes (pattern variance is visible in the markup)", () => {
    const plain = render(<Kit primary="#111111" secondary="#222222" pattern="plain" />).container
      .innerHTML;
    const stripes = render(<Kit primary="#111111" secondary="#222222" pattern="stripes" />)
      .container.innerHTML;
    const hoops = render(<Kit primary="#111111" secondary="#222222" pattern="hoops" />).container
      .innerHTML;
    const sleeves = render(<Kit primary="#111111" secondary="#222222" pattern="sleeves" />)
      .container.innerHTML;

    expect(stripes).not.toBe(plain);
    expect(hoops).not.toBe(plain);
    expect(sleeves).not.toBe(plain);
    expect(new Set([stripes, hoops, sleeves]).size).toBe(3);
  });
});
