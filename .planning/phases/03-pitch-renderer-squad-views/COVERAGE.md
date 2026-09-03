# API Coverage — FPL ML solver API (`api/main.py`) consumed as a browser client

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

**Scope note.** This phase integrates no third-party API surface. The roadmap's
original external-API flag (FPL CDN shirt/badge image URLs) was closed by
`03-CONTEXT.md` D-01: kits are self-hosted neutral SVGs, so **zero FPL CDN
endpoints are consumed**. The surface enumerated below is the project's own
FastAPI service, consumed for the first time from the React client in this phase.

## Endpoint capability matrix

| capability | decision | reason |
|---|---|---|
| `GET /api/team/{entry}` — load a manager's picks, bank, value, manager summary | INTEGRATE | D-10/PITCH-03 loaded-team flow; plan 03-02 Task 3 |
| `POST /api/solve` (`entry: <id>` → `kind: "transfers"`) | INTEGRATE | PITCH-03 solve flow; plan 03-04 Task 2 |
| `POST /api/solve` `locks[]` / `excludes[]` | INTEGRATE | D-13 lock/exclude; always sent as `player_code` ints (Pitfall 3) |
| `POST /api/solve` `free_transfers`, `max_transfers` | INTEGRATE | D-14 essentials-only knob set |
| `POST /api/solve` (`entry: null` → `kind: "squad"`, wildcard/from-scratch) | OPT-OUT | Claude's Discretion resolved to view-only default Squad tab (`03-RESEARCH.md` Open Question 1) — the loaded-team flow already covers the whole solve surface; the `SolveSquadResult` arm is still typed so the discriminated union stays exhaustive and a later phase can enable it without a type change |
| `POST /api/solve` `mode` (`normal`/`tc`/`bb`) | OPT-OUT | D-14 explicitly limits exposed knobs to essentials; server default `"normal"` applies |
| `POST /api/solve` `budget` | OPT-OUT | D-14 — server default applies; a client-set budget only has meaning for the opted-out `entry: null` arm |
| `POST /api/solve` `horizon` | INTEGRATE | D-14 plan horizon knob; plan 03-04 Task 2 |
| `GET /api/rate/{entry}` — score, tiles, `best_move`, `xi[]`, `free_transfers` | INTEGRATE | PITCH-04 + D-19/D-20; plans 03-02 Task 3 and 03-03 |
| `POST /api/plan` — multi-week joint plan | INTEGRATE | D-19 plan-transfers flow carried over verbatim; plan 03-03 Task 3 |
| `GET /api/meta` | OPT-OUT | Duplicate of `web/data/meta.json`, which `PageShell` already fetches once and shares app-wide (UI-06). Adding a second source of gameweek truth would let the banner and the pitch label disagree |
| `GET /api/health` | OPT-OUT | Operations/liveness probe, not user-facing data. Vanilla's `detectApiBase()` used it for API-availability probing; the React app uses relative paths with no base detection (`lib/api.ts` module contract), so there is nothing to probe |

## Static export contract (`web/data/*.json`, consumed unchanged)

| capability | decision | reason |
|---|---|---|
| `squad.json` (`squad[]`, `captain`, `formation`, `cost`, `xi_xp`) | INTEGRATE | D-10 default model-squad pitch |
| `xp_table.json` (`p10`/`p90`/`xp_capt`/`team_short`/`status`/`news`/`ownership`) | INTEGRATE | Join source for D-06 intervals, D-08 VC derivation, and the `team_short` kit key |
| `chips.json` (`note`, `structure[]`) | INTEGRATE | UIX-03/D-21 chip timeline |
| `meta.json` (`gw`) | INTEGRATE | "Model squad · GW{n}" label, via the existing shared `PageShell` query |
| Writing to / extending any `web/data/*.json` schema | OPT-OUT | Milestone invariant — the export schema is the pipeline↔site contract and is consumed unchanged. D-08 explicitly rejected adding a VC field to the export in favour of client-side derivation |

**Every OPT-OUT above carries a reason. No un-decided holes remain.**
