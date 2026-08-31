import { useRouteError } from "react-router";

export interface ErrorStateProps {
  resource: string;
  onRetry?: () => void;
}

/* Centred error block reused by every route's failed `/data/*` or `/api/*` fetch
 * (UI-SPEC "Loading / error components"). Renders only the Copywriting
 * Contract's heading + resource-named body — the thrown Error's message,
 * response body, request URL, and stack trace never reach the DOM here; send
 * them to console.error instead (T-05-02). */
export function ErrorState({ resource, onRetry }: ErrorStateProps) {
  const handleRetry = onRetry ?? (() => window.location.reload());

  return (
    <div className="flex min-h-[16rem] flex-col items-center justify-center gap-3 py-12 text-center">
      <h1 className="font-display text-display font-bold text-bad">
        Couldn't load this page
      </h1>
      <p className="font-body text-body text-ink-2">
        We couldn't reach {resource} — check your connection and retry.
      </p>
      <button
        type="button"
        onClick={handleRetry}
        className="rounded bg-accent px-4 py-2 font-label text-label font-bold text-bg"
      >
        Retry
      </button>
    </div>
  );
}

/* Wired into router.tsx's per-route errorElement slots. React Router supplies
 * no props to an errorElement, so this reads the thrown error via
 * useRouteError purely for console logging — never rendering it — and falls
 * back to a full reload as its "retry" affordance, since no query refetch is
 * reachable from outside a route's own render. Kept separate from <ErrorState/>
 * itself so the shared presentational component never calls a router hook that
 * requires a data-router context (useRouteError throws outside one), which
 * would make it unsafe to unit-test <ErrorState/> in isolation. */
export function RouteErrorBoundary({ resource }: { resource: string }) {
  const error = useRouteError();
  if (error !== undefined) {
    console.error(error);
  }
  return <ErrorState resource={resource} />;
}

export default ErrorState;
