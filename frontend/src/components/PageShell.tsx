import { NavLink, Outlet } from "react-router";

/* Fixed, literal array (never Object.keys over a map) so the header nav's render
 * order is pinned to source and cannot vary between renders — UI-SPEC "Routes"
 * table order. Labels reuse web/index.html's existing nav copy for parity. */
export const NAV_LINKS: { to: string; label: string }[] = [
  { to: "/", label: "xP table" },
  { to: "/team", label: "Rate my team" },
  { to: "/fixtures", label: "Fixtures" },
  { to: "/prices", label: "Prices" },
  { to: "/league", label: "League" },
  { to: "/scoreboard", label: "Scoreboard" },
  { to: "/differentials", label: "Differentials" },
  { to: "/methodology", label: "Method" },
];

/* App shell chrome: non-sticky header (brand + nav + empty meta-banner slot) +
 * a 68rem centred content wrapper + a persistent footer disclaimer.
 *
 * The meta-banner slot is empty this phase — Phase 2's UI-06 live deadline
 * countdown fills it later. Every colour reference below goes through a
 * Tailwind v4 @theme token name (see src/index.css); no hex literal appears in
 * this file. */
export default function PageShell() {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      <header className="flex flex-wrap items-center gap-[18px] border-b border-line px-4 py-4">
        <span className="font-heading text-[1.25rem] font-bold tracking-tight">
          FPL<span className="text-accent">ML</span>
        </span>
        <nav aria-label="Site" className="flex flex-wrap gap-0.5">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex min-h-[44px] items-center rounded px-3 py-2 font-label text-label ${
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
        {/* Meta-banner slot — Phase 2 UI-06 live deadline countdown lands here. */}
        <div className="ml-auto" />
      </header>

      <main className="mx-auto w-full max-w-[68rem] flex-1 px-4">
        <Outlet />
      </main>

      <footer className="border-t border-line px-4 py-4 text-label text-ink-2">
        <p className="mx-auto max-w-[68rem]">
          Predictions are statistics, not certainties. This site hosts no contests and
          takes no stakes. Not affiliated with the Premier League or the official
          Fantasy Premier League game.
        </p>
      </footer>
    </div>
  );
}
