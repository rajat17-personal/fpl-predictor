/* Shell-level fallback for a fetch that resolves with zero rows/items (UI-SPEC
 * E2 empty). Per-page singular/plural list-length copy is Phase 2+ scope — this
 * is the only zero-item behaviour the app shell defines this phase. */
export function EmptyState() {
  return (
    <div className="flex min-h-[16rem] flex-col items-center justify-center gap-2 py-12 text-center">
      <h2 className="font-heading text-heading font-bold text-ink">Nothing here yet</h2>
      <p className="font-body text-body text-ink-2">
        This data source returned no results. Try again shortly — the weekly export
        may still be running.
      </p>
    </div>
  );
}

export default EmptyState;
