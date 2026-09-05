import { describe, expect, it, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { PAGE_META, usePageMeta } from "./usePageMeta";

function Wrapper({ path }: { path: string }) {
  usePageMeta(path);
  return null;
}

function resetHead() {
  document.title = "";
  document.querySelectorAll('meta[name="description"]').forEach((el) => el.remove());
}

describe("usePageMeta", () => {
  beforeEach(() => {
    resetHead();
  });

  it("sets document.title for a known route", () => {
    render(<Wrapper path="/" />);
    expect(document.title).toBe(PAGE_META["/"].title);
  });

  it("creates a meta[name=description] element when the document has none", () => {
    expect(document.querySelector('meta[name="description"]')).toBeNull();

    render(<Wrapper path="/fixtures" />);

    const meta = document.querySelector('meta[name="description"]');
    expect(meta).not.toBeNull();
    expect(meta?.getAttribute("content")).toBe(PAGE_META["/fixtures"].description);
  });

  it("upserts the content of an already-present meta[name=description] element", () => {
    const existing = document.createElement("meta");
    existing.setAttribute("name", "description");
    existing.setAttribute("content", "stale");
    document.head.appendChild(existing);

    render(<Wrapper path="/prices" />);

    const metas = document.querySelectorAll('meta[name="description"]');
    expect(metas).toHaveLength(1);
    expect(metas[0].getAttribute("content")).toBe(PAGE_META["/prices"].description);
  });

  it("carries the complete 8-route table (D-11), including /team for future completeness", () => {
    expect(Object.keys(PAGE_META).sort()).toEqual(
      [
        "/",
        "/team",
        "/fixtures",
        "/prices",
        "/league",
        "/scoreboard",
        "/differentials",
        "/methodology",
      ].sort(),
    );
  });
});
