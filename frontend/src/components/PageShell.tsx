import { NavLink, Outlet } from "react-router";
import { useQuery } from "@tanstack/react-query";
import GwBanner from "./GwBanner";
import ThemeToggle from "./ThemeToggle";
import { fetchJson, type MetaResponse } from "../lib/api";

/* Fixed, literal array (never Object.keys over a map) so the header nav's render
 * order is pinned to source and cannot vary between renders — UI-SPEC "Routes"
 * table order. Labels reuse web/index.html's existing nav copy for parity. */
export const NAV_LINKS: { to: string; label: string }[] = [
  { to: "/", label: "xP table" },
  { to: "/team", label: "My team" },
  { to: "/fixtures", label: "Fixtures" },
  { to: "/prices", label: "Prices" },
  { to: "/league", label: "League" },
  { to: "/scoreboard", label: "Scoreboard" },
  { to: "/differentials", label: "Differentials" },
  { to: "/methodology", label: "Method" },
];

/* App shell chrome: non-sticky header (brand + nav + GW banner + theme
 * toggle) + route content, all three sections contained at a shared 68rem
 * centred column with a full-bleed border above/below + a persistent footer
 * disclaimer. The header and footer outer elements carry the border and stay
 * edge to edge; the 68rem cap and the 16px gutter live on an inner wrapper so
 * chrome content edges align with the route content beneath them.
 *
 * PageShell owns the single `meta.json` query (UI-06) so it is fetched once
 * and shared by every route via GwBanner, rather than refetched per page.
 * Every colour reference below goes through a Tailwind v4 @theme token name
 * (see src/index.css); no hex literal appears in this file. */
export default function PageShell() {
  const metaQuery = useQuery({
    queryKey: ["meta"],
    queryFn: () => fetchJson<MetaResponse>("/data/meta.json"),
    staleTime: 60_000,
  });

  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      <header className="border-b border-line py-4">
        {/* 07-03 UAT G-07-3: at desktop width (~1280px, 68rem/1088px inner
         * cap) the un-tightened row (18px section gaps, px-3 nav padding,
         * GwBanner's original two-line pill) measured ~1289px against a
         * ~1088px container -- it always wrapped, at any viewport, because
         * the cap never grows. Measured live via Playwright (headless
         * Chromium, IBM Plex Sans/Mono, not a hand estimate): the combined
         * padding/gap tightening here plus GwBanner's line reflow lands the
         * row at ~1000px with real margin to spare, confirmed by a header
         * height of 83px (one line) vs. 145px (wrapped) before the fix. */}
        <div className="mx-auto flex w-full max-w-[68rem] flex-wrap items-center gap-1 px-4">
          <span className="font-heading text-[1.25rem] font-bold tracking-tight">
            FPL<span className="text-accent">ML</span>
          </span>
          <nav aria-label="Site" className="flex flex-wrap gap-0">
            {NAV_LINKS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex min-h-[44px] items-center rounded px-1.5 py-2 font-label text-label ${
                    isActive
                      ? "bg-accent-bg font-bold text-accent-ink"
                      : "text-ink-2 hover:bg-surface hover:text-ink"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex flex-wrap items-center gap-1">
            <GwBanner status={metaQuery.status} data={metaQuery.data} />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[68rem] flex-1 px-4">
        <Outlet />
      </main>

      <footer className="border-t border-line py-4 text-label text-ink-2">
        <p className="mx-auto w-full max-w-[68rem] px-4">
          Predictions are statistics, not certainties. This site hosts no contests and
          takes no stakes. Not affiliated with the Premier League or the official
          Fantasy Premier League game. Player kit colors shown are generic illustrations,
          not licensed team imagery.
        </p>
      </footer>
    </div>
  );
}
