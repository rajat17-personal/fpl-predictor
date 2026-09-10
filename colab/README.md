# Colab handoff: GRU + transformer sequence candidates

D-13 sends the two GPU-bound D-12 sequence candidates (the GRU recurrent
model and the small transformer, `models/bracket/recurrent.py` /
`models/bracket/transformer.py`) to Google Colab; Ridge/XGBoost/CatBoost/MLP
ran locally (plans 10-10/10-11). This directory is the human-run handoff: a
local export, a notebook that trains on Colab's GPU, and a downloaded
prediction artifact scored back through this project's own validating local
seam (D-14, `backtest.walk_forward.load_external_predictions`) -- the local
harness stays the sole judge (D-14) of any number this handoff produces.

## Source

The notebook's input is `data/processed/experiments/colab_input/` --
produced locally by `models.bracket.registry.export_sequence_bundle`, never
committed (gitignored under `data/processed/`, verified empty by
`git status --porcelain` after every export).

## Attribution

Google Colab Pro. D-13 budgets all 200 owned compute units for this handoff;
no new spend, no new account, no third-party data source.

## Regeneration

```bash
python -c "
from models.bracket.registry import export_sequence_bundle
import config
export_sequence_bundle(['2025-26'], config.EXPERIMENTS_DIR / 'colab_input')
"
```

Then, by hand:

1. Upload `colab/bracket_deep.ipynb` and the exported
   `data/processed/experiments/colab_input/` directory to Colab.
2. Select a GPU runtime, run all cells.
3. Download the produced per-test-season prediction parquet(s) into
   `data/processed/experiments/colab/`.

This is a deliberate, human-run, network-using step -- **never wired into cron or CI** -- exactly like `data/external/README.md`'s own
`backtest/benchmark_external.py --fetch` regeneration step.

## Reduction applied

The exported bundle carries, per needed season: the padded/masked raw
per-gameweek sequence tensor (`x_seq`), its padding mask (`mask`), the
pre-match static context vector (`x_static`), the training targets
(`y` = `y_points`, `minutes` = `y_minutes`), and an identity frame (`season`,
`gw`, `player_code`, `fixture_id`) parallel to the tensors. It deliberately
omits everything else in `features.parquet` -- no player name, no manager
identity, no free text, no column beyond `models/bracket/sequence.py`'s own
`SEQ_STATS`/`STATIC_COLS` declared lists.

## PII spot-check

The bundle carries no manager identity and no free text. The only per-row
identity fields are `season`, `gw`, `player_code` (this project's own
season-invariant integer player id, already public in every other exported
artifact) and `fixture_id` -- no player name, no email, no date of birth.

## Artifact contract

The notebook must write back EXACTLY the six columns
`backtest.walk_forward._EXTERNAL_PRED_COLS` requires, one file per test
season, named `colab_<candidate>_<season>.parquet`
(e.g. `colab_rnn_2025-26.parquet`, `colab_transformer_2025-26.parquet`):

| Column | Meaning |
|--------|---------|
| `season` | This project's season label, e.g. `2025-26` |
| `gw` | Gameweek number |
| `player_code` | This project's season-invariant player id |
| `fixture_id` | The individual fixture id (this project's model granularity is per-FIXTURE, never per-gameweek) |
| `xp_med` | The candidate's median-objective prediction |
| `xp_mean` | The candidate's mean-objective prediction |

**Two prohibitions, stated as prohibitions:**

- The artifact must **NOT** contain any `y_*` ground-truth column
  (`y_points`, `y_minutes`, `y_played`, `y_started`, `y_clean_sheets`) -- the
  local seam drops and warns about any it finds; ground truth is always
  re-attached locally, never trusted from the artifact.
- The artifact must **NOT** contain more than one season per file -- the
  local seam raises `ValueError` on a multi-season dump (this is exactly
  the shape a notebook that trained one global model instead of per-season
  models would produce).

## Split contract

The notebook reads its per-test-season `(train_seasons, val_season,
test_season)` triple from `manifest.json`'s `"splits"` key and must **never**
derive its own. `manifest.json` is written by the same expanding-window rule
`backtest.walk_forward._preds_for` uses -- it is the split authority, not a
suggestion.

**Consequence, stated plainly:** a notebook that trained one global model
across every season, or that accidentally included the test season's own
rows in training, produces a file that is schema-valid and
leakage-corrupt -- `backtest.walk_forward.load_external_predictions` can
only flag that shape by IMPLAUSIBILITY (an unexpectedly high Spearman
against the in-process LightGBM baseline), never detect it directly. Do not
edit the notebook's split-reading cell to compute its own train/val/test
boundaries, no matter how convenient a shortcut it looks like.

## Compute accounting

Colab's own usage panel (top-right, "Compute units remaining") reports
consumption. **Record the units consumed per candidate**, checked before and
after each candidate's run -- D-13's budget is all 200 owned units with a
hard stop at exhaustion, and an unrecorded spend cannot be hard-stopped. If
the GRU run alone consumes enough that the transformer candidate cannot
complete within the remaining balance, stop and report the remaining balance
rather than starting a run that will be killed mid-way -- a truncated run
produces a partial artifact that still looks scoreable.
