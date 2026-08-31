interface PlaceholderPageProps {
  title: string;
}

/* Used by all 8 routes this phase — real page content is Phase 2 scope
 * (UI-02..UI-06). Renders inside PageShell's existing 68rem wrapper, so it sets
 * no width, no fixed height, and no overflow handling of its own (UI-SPEC E3). */
export default function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <div className="py-12">
      <h1 className="font-display text-display font-bold text-ink">{title}</h1>
      <p className="mt-2 font-body text-body text-ink-2">
        This page is under construction — content lands in a later phase.
      </p>
    </div>
  );
}
