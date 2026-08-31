/* Centred loading indicator shown while a route's TanStack Query fetch to
 * `web/data/*.json` or `/api/*` is in flight (UI-SPEC "Loading / error
 * components"). Reserves the content area's expected minimum height so nothing
 * jumps on resolve. */
export function Spinner() {
  return (
    <div
      role="status"
      className="flex min-h-[16rem] flex-col items-center justify-center gap-3 py-12"
    >
      <div
        aria-hidden="true"
        className="h-8 w-8 animate-spin rounded-full border-4 border-accent-bg border-t-accent"
      />
      <span className="font-label text-label text-ink-2">Loading…</span>
    </div>
  );
}

export default Spinner;
