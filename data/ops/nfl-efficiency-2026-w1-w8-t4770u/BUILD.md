# Build — t4770u 2026 W1–W8 efficiency recovery

Offline only. No `DATABASE_URL`. No C10 / Railway. No paid data.

Bound to Alex v2 `b41f4b43` after IMV PASS_CONTRACT `1a53bbd3` (D1 CLOSED).
Incomplete W8 → `DATA_PARTIAL`. PASS_CONTRACT ≠ DATA ACCEPT ≠ emit.

## Approved source

```
https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet
```

Same URL template CLEARed on t4696u S1 restage (2012–2022). Public HTTPS. Hash raw bytes before parse.

## Rebuild

**Through-W7 PARTIAL only** (W8 incomplete — current sealed state). Reuses local parquet:

```bash
python3 scripts/nfl/build_efficiency_2026_w1_w8_t4770u.py --skip-fetch
python3 scripts/nfl/prove_if_consume_2026_w09_t4770u.py
cd services/model-service && python3 -m pytest tests/test_nfl_efficiency_2026_w1_w8_t4770u.py -q
```

**DATA_READY (only after W8 14/14 including MNF CHI@SEA).** Do **not** `--skip-fetch`. Builder refuses skip-fetch when through_w8_complete (O-a). Follow `STANDBY.md`:

```bash
python3 scripts/nfl/check_w8_complete_t4770u.py --fetch
# only if through_w8_complete=true and MNF present:
python3 scripts/nfl/build_efficiency_2026_w1_w8_t4770u.py
python3 scripts/nfl/prove_if_consume_2026_w09_t4770u.py
# pytest PARTIAL-era asserts (status/as_of_week/STATUS sha) must be rewritten
# to the new seal as part of the READY commit — do not withhold READY on those reds.
```

`--skip-fetch` reuses `data/raw/nfl/pbp/t4770u/play_by_play_2026.parquet` (gitignored). READY must re-fetch + archive + pin `fetched_at_utc`.
The prove script reseals `SHA256SUMS` over the whole packet, including authority files.

## Transforms (Alex contract v2 `b41f4b43` — existing only)

- T1 situational weekly from PBP pass/run (ingest.py semantics)
- T2 rolling 5g `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` per team-week
- T3 matchup diffs per ingest.py
- T4 `matchup_diff_success_rate_5g` = mean of both success terms
- T5 `team_strength_from_record` on 2026 W-L (ties recorded, excluded from wp denom)
- Rest days: `rest_days_from_schedule`
- W9 consume uses each team's latest rolling row with week ≤ panel cap (7 while W8 incomplete; 8 only when W8 is final).
- v2 catch-all: every `NflGameInputs` field outside the 20 required + context is written None (live dataclass).

## t4776u consume proof

`if_required_20_consumed.json` is not a presence check. For each of the 20 required fields it records:

1. AST call-graph cite on `simulate_nfl_game_independent_fair` → `simulate_nfl_game(independent_fair=True)` → `_build_matchup_adjustments` / `_build_totals_adjustments` / `compute_nfl_projection_decomposition`
2. sha256 of the 20-field payload actually passed into `NflGameInputs`
3. A single-field perturbation that changes that input hash **and** the Independent Fair output hash (`predicted_*` + `margin_mu` / `total_mu`)

A field that is on the row but does not move the IF path fails closed.

## Fail closed

Week 8 incomplete → `DATA_PARTIAL`. Do not declare through-W8. Do not fill with 2025 priors. Do not emit.
