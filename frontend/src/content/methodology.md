# How the model works

"Best team" is two chained problems: predict expected points per player, then
select the best legal squad. Machine learning can't output a legal 15;
optimization can't invent good predictions. We do both, and we publish how
wrong we are.

## Prediction

A per-position two-stage model: first the probability a player features
(calibrated — injuries, rotation, suspensions), then their conditional points
if they do. Gradient-boosted trees over rolling form at several horizons,
fixture difficulty, days of rest, home/away, set-piece duty, price,
ownership, and bookmaker-implied win/clean-sheet probabilities. Trained on
ten seasons of per-gameweek history, validated with strictly time-ordered
splits — the model never sees the future it is graded on.

## Uncertainty

The 10–90% bands come from the model's real errors on a fully held-out
season, bucketed by position and prediction size — not from a formula.
Measured coverage is 86%, slightly conservative. Football is high-variance;
anyone selling you certainty is selling you something else.

## Selection

Integer linear programming over the full player pool enforces every FPL rule
— budget, 2/5/5/3 squad, three per club, legal formations, captaincy,
transfer hits, the 50% sell-on fee, chip mechanics. The solver returns the
provably optimal team for the predictions, not a greedy guess.

## The receipts

- **Fixture MAE** — 0.87 vs FPL 1.07 (held-out season, per fixture)
- **Rank correlation** — 0.74 vs FPL 0.30 (Spearman, predicted vs actual)
- **Season points** — ~2260 (full system, 6-season walk-forward average)
- **Edge over form-picking** — +102 (points/season vs an ML-free baseline)

Those are backtest numbers — walk-forward, retrained each season, with
chips, autosubs and transfer costs simulated. The live version of that claim
is the [scoreboard](/scoreboard), which scores every published gameweek
automatically. Early season the model leans on price and fixture priors
(there's little current form to roll up), so expect it to sharpen from
around GW4.

## Honesty policy

- Predictions are frozen before the deadline and scored after — never edited.
- Negative results stay documented; features that didn't help were kept out.
- These are statistics about a free fantasy game, not betting advice. No
  stakes are hosted here and none should be placed on this.

Data: official FPL API, historical per-gameweek archives, football-data.co.uk odds.
