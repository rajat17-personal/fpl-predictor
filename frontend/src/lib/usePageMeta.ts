import { useEffect } from "react";

/* Per-route <title>/<meta name="description"> copy (D-11), ported verbatim
 * from each web/*.html page's <head> block. `/team`'s row is included now
 * for route-table completeness even though Phase 3 fills that page's
 * content. No helmet-style dependency, no new package. */
export const PAGE_META = Object.freeze({
  "/": {
    title: "FPL ML — expected points, honestly measured",
    description:
      "Machine-learned FPL expected points with uncertainty bands, an optimal squad, and a public accuracy scoreboard.",
  },
  "/team": {
    title: "My team — FPL ML",
    description:
      "Score your FPL squad against the model's optimum, get your best move, and see chip timing.",
  },
  "/fixtures": {
    title: "Fixture ticker — FPL ML",
    description: "Next six gameweeks of fixture difficulty for every Premier League club.",
  },
  "/prices": {
    title: "Price watch — FPL ML",
    description: "Likely FPL price risers and fallers tonight.",
  },
  "/league": {
    title: "League table & leaders — FPL ML",
    description:
      "Premier League standings and season player leaderboards: goals, assists, clean sheets, cards.",
  },
  "/scoreboard": {
    title: "Accuracy scoreboard — FPL ML",
    description:
      "Every prediction this model makes, scored publicly against FPL's own expected points.",
  },
  "/differentials": {
    title: "Differentials — FPL ML",
    description: "High expected points, low ownership: template-breaking FPL picks.",
  },
  "/methodology": {
    title: "How the model works — FPL ML",
    description:
      "A two-stage ML model plus integer programming, validated over six seasons of walk-forward backtests.",
  },
} as const);

type PageMetaPath = keyof typeof PAGE_META;

function isPageMetaPath(path: string): path is PageMetaPath {
  return Object.prototype.hasOwnProperty.call(PAGE_META, path);
}

/** Sets document.title and upserts <meta name="description"> for `path`, on
 * mount and whenever `path` changes. Creates the meta element if the
 * document has none. */
export function usePageMeta(path: string): void {
  useEffect(() => {
    if (!isPageMetaPath(path)) {
      return;
    }
    const entry = PAGE_META[path];

    document.title = entry.title;

    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.setAttribute("name", "description");
      document.head.appendChild(meta);
    }
    meta.setAttribute("content", entry.description);
  }, [path]);
}
