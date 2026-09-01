import ReactMarkdown from "react-markdown";
import { Link } from "react-router";
import content from "../content/methodology.md?raw";
import { usePageMeta } from "../lib/usePageMeta";

/* Ported verbatim from web/methodology.html lines 30-77 (D-03) into
 * frontend/src/content/methodology.md, imported at build time via Vite's
 * `?raw` suffix (D-13, UI-SPEC "static-content, build-time bundled") — no
 * runtime fetch, so this page has no pending, error or empty state and must
 * never render a <Spinner> or an <ErrorState>.
 *
 * Rendered through react-markdown's default component (D-13's package-
 * legitimacy-approved renderer, plan 02-02), which parses to real React
 * elements and escapes rather than injects raw HTML by default — no React
 * raw-markup escape-hatch prop, no `rehype-raw` plugin, matching the
 * repo-wide "no raw-HTML sink" rule this task's threat model enforces.
 *
 * The data-source credit line that lives in vanilla's own per-page footer
 * is the final paragraph of methodology.md's body instead — Phase 1's
 * single unified PageShell footer (ledger entry 6) stays untouched. */
export default function Methodology() {
  usePageMeta("/methodology");

  return (
    <div className="py-8">
      <ReactMarkdown
        components={{
          h1: (props) => (
            <h1 className="font-display text-display font-bold text-ink" {...props} />
          ),
          h2: (props) => (
            <h2 className="mt-8 font-heading text-heading font-bold text-ink" {...props} />
          ),
          p: (props) => <p className="mt-2 font-body text-body text-ink-2" {...props} />,
          ul: (props) => (
            <ul
              className="mt-2 list-disc space-y-1 pl-5 font-body text-body text-ink-2"
              {...props}
            />
          ),
          li: (props) => <li {...props} />,
          a: ({ href, children, ...props }) =>
            href?.startsWith("/") ? (
              <Link to={href} className="text-accent underline">
                {children}
              </Link>
            ) : (
              <a href={href} className="text-accent underline" {...props}>
                {children}
              </a>
            ),
          strong: (props) => <strong className="font-bold text-ink" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
