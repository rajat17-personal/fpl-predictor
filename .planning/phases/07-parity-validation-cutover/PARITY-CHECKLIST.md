# Phase 7 Parity Checklist

Manual verification `e2e/parity/parity-diff.mjs` cannot do: judgement calls about how a page
*looks*, and one same-session comparison of the interactive solver flows a script would be
expensive to fake convincingly. Run this alongside each of the three `PARITY-REPORT.md` stage
passes, on the dual-site pair (`bash scripts/dual_site.sh start`, vanilla at
`http://127.0.0.1:8000`, react at `http://127.0.0.1:8001`, unless overridden).

**Value and sort-order checking is the script's job.** `parity-diff.mjs` already compares every
table's cell values and row order field-for-field against the ledger. Do not re-verify a
number, a row's position, or a sort click by eye here — if a value looks wrong, that is either
already a defect in the stage's `PARITY-REPORT.md` table or a gap in `extract.mjs`'s field map,
not something this checklist re-derives.

## Part 1 — Per-page manual pass (D-05 eyeball half)

For each of the eight pages, at both desktop (~1280px) and mobile (~375px) widths, and in both
light and dark theme (the theme toggle in the header):

- Layout and spacing look intentional — no cramped, misaligned, or overlapping elements.
- No horizontal overflow or scroll; no table or card visibly clipped.
- Text wraps sensibly; nothing truncated mid-word without an ellipsis.
- Table rows and cells stay legible (contrast, size) at both widths.
- Page copy (headings, intro paragraphs, footer disclaimer) reads the same on both sites,
  word for word, wherever it is meant to port verbatim (`PARITY-DEVIATIONS.md`'s parity model).

### xP table (`/` vs `/index.html`)

- [ ] Layout/spacing, desktop + mobile
- [ ] Dark + light theme
- [ ] xP table and Captain picks sub-table both readable, no overflow
- [ ] Position chips and search box usable at 375px

### Rate my team (`/team` vs `/team.html`)

- [ ] Layout/spacing, desktop + mobile
- [ ] Dark + light theme
- [ ] Pitch renderer (React) / rate form (vanilla) both usable at 375px
- [ ] Note: the two sites' default views differ structurally (React opens on the model-squad
      pitch, vanilla opens on the rate-ID form) — judge each side on its own layout quality,
      not against the other's structure. Content-level rate/solve/plan comparison is Part 2,
      not this pass.

### Fixture ticker (`/fixtures` vs `/fixtures.html`)

- [ ] Layout/spacing, desktop + mobile
- [ ] Dark + light theme
- [ ] FDR chips readable and not clipped at 375px; legend visible

### Price watch (`/prices` vs `/prices.html`)

- [ ] Layout/spacing, desktop + mobile
- [ ] Dark + light theme
- [ ] Risers/fallers tables both readable, no overflow

### League table & leaders (`/league` vs `/league.html`)

- [ ] Layout/spacing, desktop + mobile
- [ ] Dark + light theme
- [ ] Standings table and leader-board cards both readable, no overflow

### Scoreboard (`/scoreboard` vs `/scoreboard.html`)

- [ ] Layout/spacing, desktop + mobile
- [ ] Dark + light theme
- [ ] Tiles and (if present) history table both readable, no overflow

### Differentials (`/differentials` vs `/differentials.html`)

- [ ] Layout/spacing, desktop + mobile
- [ ] Dark + light theme
- [ ] Slider control usable at 375px (44px touch target); table readable

### Methodology (`/methodology` vs `/methodology.html`)

- [ ] Layout/spacing, desktop + mobile
- [ ] Dark + light theme
- [ ] Prose sections and "The receipts" content both readable, no overflow

## Part 2 — Same-session interactive comparison (D-08)

One session, entry **6980093** loaded on both sites back to back (never a placeholder ID, and
never the manager's own first/last name — the numeric entry id and, where a team name is
needed, the team name only; this repo's Phase 4 fixture capture set that precedent
deliberately). Both processes read the same live model artifact and the same live pool at the
same instant, so a same-session cross-site difference here is a real defect, not noise —
record it in the current stage's `PARITY-REPORT.md` "Defects found" table, not this checklist.

Perform each flow identically on vanilla (`/team.html?entry=6980093`) and react
(`/team?tab=rate&entry=6980093`, or via the Squad tab's "Load your own team" control).

- [ ] **Rate my team.** Load entry 6980093 on both. Compare: Team score, best-XI xP (and its
      p10–p90 band if shown), Season-so-far points/rank/last-GW figure, Captain, Best move
      (sell → buy names and xP gain, or "Hold"). All figures should match exactly.
- [ ] **One solve, identical locks.** On both sites, run a solve with the same lock/exclude
      set (pick 1–2 players to lock, note the exact names/codes used so the run is
      reproducible) and the same free-transfers/horizon inputs. Compare: the suggested
      transfers (sell → buy pairs) and the resulting starting XI.
- [ ] **One two-gameweek plan.** On both sites, request a plan over horizon = 2 with the same
      inputs. Compare: each week's suggested moves, hit cost (if any), and projected XI xP.

## Cron-green step (D-16, criterion 3 evidence)

Before marking a stage's rows closed in `PARITY-REPORT.md`, cite the concrete evidence that the
daily/weekly cron kept running clean since the previous pass — never a recollection:

1. **`data/cron.log`** — if the file exists on the host, quote the relevant `[daily]`/`[weekly]`
   lines showing every step `OK` since the last pass. **If the file does not exist**, record
   that fact verbatim in the `Cron-green citation` cell (e.g. "no data/cron.log on this host as
   of `<date>`") — an absent log is never written up as a green run.
2. **`FPL_ALERT_LOG` (default `data/alerts.jsonl`)** — confirm no new records were appended
   since the previous pass (`ops.notify.report`'s on-disk sink). Cite the absence explicitly
   ("no new alerts.jsonl records since `<previous stage timestamp>`"), or quote any record found
   and treat it as a defect requiring investigation before this stage can close.
3. **`web/data/` git history** — `git log --oneline -- web/data/meta.json` (or the relevant
   export file) since the previous pass, confirming the weekly/daily export actually landed
   in the window this stage claims to cover.

Cite whichever of the three actually apply in each stage's `Cron-green citation` column; a row
with none of the three cited is not closed.
