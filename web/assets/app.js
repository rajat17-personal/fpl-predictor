/* Shared plumbing: data loading, nav, deadline chip, table sorting. */

export const CONFIG = window.FPL_CONFIG || { API_BASE: null };

/* Where is the solver API? An explicit CONFIG.API_BASE wins; otherwise probe
   the site's own origin (uvicorn serves site + API together), then the
   two-process dev default localhost:8001. Returns a base ("" = same origin)
   or null if no API answers. */
export async function detectApiBase() {
  if (CONFIG.API_BASE !== null) return CONFIG.API_BASE;
  const candidates = ["", ...(
    ["localhost", "127.0.0.1"].includes(location.hostname)
      ? ["http://localhost:8001"] : [])];
  for (const base of candidates) {
    try {
      const r = await fetch(`${base}/api/health`,
                            { signal: AbortSignal.timeout(1500) });
      if (r.ok) return base;
    } catch { /* try the next candidate */ }
  }
  return null;
}

export async function loadJSON(name) {
  const r = await fetch(`data/${name}`);
  if (!r.ok) throw new Error(`${name}: ${r.status}`);
  return r.json();
}

export function fmtDeadline(iso) {
  if (!iso) return "deadline TBC";
  const d = new Date(iso);
  const diff = d - Date.now();
  const rel = diff > 0
    ? `in ${Math.floor(diff / 864e5)}d ${Math.floor((diff % 864e5) / 36e5)}h`
    : "passed";
  const abs = d.toLocaleString(undefined, {
    weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
  return `${abs} · ${rel}`;
}

export async function initChrome(page) {
  document.querySelectorAll("nav.site a").forEach((a) => {
    if (a.dataset.page === page) a.setAttribute("aria-current", "page");
  });
  try {
    const meta = await loadJSON("meta.json");
    const el = document.querySelector(".deadline");
    if (el) el.textContent = `GW${meta.gw} deadline: ${fmtDeadline(meta.deadline_utc)}`;
    return meta;
  } catch { return null; }
}

/* Sortable table: headers carry data-key (and data-num for numeric compare). */
export function makeSortable(tableEl, rows, render) {
  let state = { key: null, dir: -1 };
  const ths = tableEl.querySelectorAll("th[data-key]");
  ths.forEach((th) => {
    const btn = document.createElement("button");
    btn.innerHTML = `${th.textContent} <span class="dir"></span>`;
    th.textContent = "";
    th.appendChild(btn);
    btn.addEventListener("click", () => {
      state = { key: th.dataset.key,
                dir: state.key === th.dataset.key ? -state.dir : -1 };
      ths.forEach((h) => h.querySelector(".dir").textContent =
        h === th ? (state.dir < 0 ? "▼" : "▲") : "");
      const numeric = "num" in th.dataset;
      const sorted = [...rows()].sort((a, b) => {
        const [x, y] = [a[state.key], b[state.key]];
        if (numeric) return state.dir * ((y ?? -1e9) - (x ?? -1e9));
        return state.dir * String(y ?? "").localeCompare(String(x ?? ""));
      });
      render(sorted);
    });
  });
}

export function statusFlag(r) {
  if (r.status === "a") return "";
  const out = ["i", "s", "u", "n"].includes(r.status);
  const label = out ? "unavailable" : "doubtful";
  const cls = out ? "flag out" : "flag";
  const news = (r.news || label).replace(/"/g, "&quot;");
  return ` <span class="${cls}" role="img" aria-label="${label}" title="${news}">${out ? "✕" : "▲"}</span>`;
}

/* Interval band cell: track spans p10–p90 of `scale` max; dot at xp. */
export function bandCell(r, maxHi) {
  const lo = r.p10 ?? r.xp, hi = r.p90 ?? r.xp;
  const pct = (v) => `${Math.min(100, 100 * v / maxHi)}%`;
  const title = `xP ${r.xp?.toFixed(2)} — actual score lands between ${lo?.toFixed(1)} and ${hi?.toFixed(1)} in 8 gameweeks out of 10`;
  return `<span class="band" title="${title}">
    <span class="val">${r.xp?.toFixed(2)}</span>
    <span class="track-wrap" aria-hidden="true">
      <span class="track" style="left:${pct(lo)};width:calc(${pct(hi)} - ${pct(lo)})"></span>
      <span class="pt" style="left:calc(${pct(r.xp)} - 4px)"></span>
    </span>
    <span class="range">${lo?.toFixed(1)}–${hi?.toFixed(1)}</span></span>`;
}
