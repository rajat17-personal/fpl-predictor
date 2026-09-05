import { useSearchParams } from "react-router";
import { usePageMeta } from "../lib/usePageMeta";
import { SquadTab } from "../components/team/SquadTab";
import { ChipsTab } from "../components/team/ChipsTab";
import { RateTab } from "../components/team/RateTab";

type TabKey = "squad" | "rate" | "chips";

const TABS: { key: TabKey; label: string }[] = [
  { key: "squad", label: "Squad" },
  { key: "rate", label: "Rate my team" },
  { key: "chips", label: "Chips" },
];

/* `?tab=` accepts squad (default, including absent/unrecognised)/rate/chips
 * (D-09/D-11). An unrecognised value falls back to Squad rather than
 * rendering an unmounted panel or throwing (T-03-06). */
function normalizeTab(value: string | null): TabKey {
  return value === "rate" || value === "chips" ? value : "squad";
}

/* `?entry=` is the only place a real manager's team ever lives (D-10) — it
 * is never written to storage, and a non-numeric or non-positive value is
 * treated exactly like "absent" (falls back to the model squad) rather than
 * reaching a component that would try to fetch it. */
function parseEntry(value: string | null): number | null {
  if (value == null || !/^\d+$/.test(value)) {
    return null;
  }
  const parsed = Number(value);
  return parsed >= 1 ? parsed : null;
}

/* Three-tab shell (D-09..D-12): `?entry=` and `?tab=` are the only URL
 * state this route owns (locks/excludes/solve results stay ephemeral, per
 * Phase 2's D-07). Only the active tab's panel is mounted — never rendered-
 * but-hidden — so a tab that is not open cannot fire a request (D-20). Each
 * tab component owns its own data fetching entirely; this shell never
 * fetches on its own behalf. */
export default function Team() {
  usePageMeta("/team");
  const [searchParams, setSearchParams] = useSearchParams();

  const tab = normalizeTab(searchParams.get("tab"));
  const entry = parseEntry(searchParams.get("entry"));

  function selectTab(next: TabKey) {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (next === "squad") {
        params.delete("tab");
      } else {
        params.set("tab", next);
      }
      return params;
    });
  }

  function loadEntry(id: number) {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set("entry", String(id));
      return params;
    });
  }

  function clearEntry() {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.delete("entry");
      return params;
    });
  }

  return (
    <div className="py-8">
      <div
        role="tablist"
        aria-label="Team page sections"
        className="inline-flex items-center gap-0.5 rounded-full border border-line bg-surface p-0.5"
      >
        {TABS.map(({ key, label }) => {
          const selected = tab === key;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              id={`team-tab-${key}`}
              aria-selected={selected}
              aria-controls={`team-panel-${key}`}
              onClick={() => selectTab(key)}
              className={`min-h-[44px] rounded-full px-4 py-2 font-label text-label ${
                selected
                  ? "bg-accent-bg font-bold text-accent-ink"
                  : "text-ink-2 hover:bg-surface-2"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className="mt-4">
        {tab === "squad" && (
          <div id="team-panel-squad" role="tabpanel" aria-labelledby="team-tab-squad">
            <SquadTab entry={entry} onLoadEntry={loadEntry} onClearEntry={clearEntry} />
          </div>
        )}
        {tab === "rate" && (
          <div id="team-panel-rate" role="tabpanel" aria-labelledby="team-tab-rate">
            <RateTab entry={entry} />
          </div>
        )}
        {tab === "chips" && (
          <div id="team-panel-chips" role="tabpanel" aria-labelledby="team-tab-chips">
            <ChipsTab />
          </div>
        )}
      </div>
    </div>
  );
}
