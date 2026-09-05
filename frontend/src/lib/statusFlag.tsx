import { useEffect, useId, useRef, useState } from "react";

interface StatusFlagProps {
  status: string;
  news: string;
}

/* Ported from web/assets/app.js's statusFlag (lines 81-88), verified
 * 2026-09-01. Renders only when status !== "a" (R4); glyph/aria-label
 * mapping and the `news || label` tooltip fallback are ported verbatim
 * (R5-R6). D-09 replaces vanilla's desktop-only `title` attribute with a
 * tap/click-friendly, keyboard-accessible popover (ledger entry 2) —
 * visible on hover, on focus, and on click-toggle; closes on Escape and on
 * a click outside. */
export function StatusFlag({ status, news }: StatusFlagProps) {
  const [open, setOpen] = useState(false);
  const tooltipId = useId();
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handleDocumentClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("click", handleDocumentClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("click", handleDocumentClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  if (status === "a") {
    return null;
  }

  const out = ["i", "s", "u", "n"].includes(status);
  const label = out ? "unavailable" : "doubtful";
  const glyph = out ? "✕" : "▲";
  const body = news || label;

  return (
    <span ref={containerRef} className="relative ml-1 inline-block">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-describedby={tooltipId}
        onFocus={() => setOpen(true)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex min-h-[44px] min-w-[44px] items-center justify-center font-label text-label ${
          out ? "text-bad" : "text-warn"
        }`}
      >
        {glyph}
      </button>
      {open && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute z-10 max-w-[240px] whitespace-normal rounded border border-line bg-surface p-2 font-label text-label text-ink shadow"
        >
          {body}
        </span>
      )}
    </span>
  );
}

export default StatusFlag;
