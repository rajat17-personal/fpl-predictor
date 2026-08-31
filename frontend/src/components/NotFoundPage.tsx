import { Link } from "react-router";

/* Rendered by the router's catch-all ("*") route (UI-SPEC "Routes" table). Fixed
 * composition: heading, body, and a link back to the xP table (UI-SPEC E4) — no
 * data, no async source, nothing that can be absent or partial. */
export default function NotFoundPage() {
  return (
    <div className="py-12">
      <h1 className="font-heading text-heading font-bold text-ink">Page not found</h1>
      <p className="mt-2 font-body text-body text-ink-2">
        That page doesn't exist. Head back to{" "}
        <Link to="/" className="text-accent underline">
          the xP table
        </Link>
        .
      </p>
    </div>
  );
}
