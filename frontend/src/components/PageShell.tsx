import { Outlet } from "react-router";

/* App shell chrome: non-sticky header (brand + empty nav slot + empty meta-banner
 * slot) + a 68rem centred content wrapper + a persistent footer disclaimer.
 *
 * The nav slot is empty this phase — plan 01-05 fills it with the eight route links.
 * The meta-banner slot is empty this phase — Phase 2's UI-06 live deadline countdown
 * fills it later. Every colour reference below goes through a Tailwind v4 @theme
 * token name (see src/index.css); no hex literal appears in this file. */
export default function PageShell() {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      <header className="flex flex-wrap items-center gap-[18px] border-b border-line px-4 py-4">
        <span className="font-heading text-[1.25rem] font-bold tracking-tight">
          FPL<span className="text-accent">ML</span>
        </span>
        {/* Nav slot — plan 01-05 adds the eight route links here. */}
        <nav aria-label="Site" className="flex flex-wrap gap-0.5" />
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
