# t4643u WAREHOUSE AUTHORITY — do not wire because available

Ticket: t4643u · DECISION **098da1dd**
Sealed: completeness **675e1cf7** (access CLOSED) · CONSUME_PROOF **7c2d9625** (forecast GAP)
CERT=0 · No DML/DDL · No Option B · No prod wire

**Determination: do not SELECT `nfl_dp_*` into the W8 game-forecast path or season engine from this ticket.**
Access CLOSED ≠ authoritative ≠ appropriate. Reasons below. Needs Ryan CLEAR to change SoT.

## What the RO probe actually showed (counts only; no secrets)

Source: `data/ops/nfl-t4615u-w8-depth-db-fresh-vm/depth_db_ro_probe.json` sha8 `f50ba2f0`.
`SET TRANSACTION READ ONLY`. W8 window `season=2026 AND week<=8`.

| table | present | n | teams | min_week | max_week | W8 grain |
|---|---|---|---|---|---|---|
| `nfl_dp_depth_chart_weekly` | yes | 23256 | 32 | 1 | 8 | W8 n=**2907** / 32 |
| `nfl_dp_official_depth_charts` | yes | 3171 | 32 | 1 | 1 | none |
| `nfl_dp_injuries` | yes | 734 | 32 | 1 | **3** | none |

## Authority tests (must all pass before a wire)

| test | weekly depth | official depth | injuries | rolling features (not probed this ticket) |
|---|---|---|---|---|
| Populated for requested week | W8 row count yes | no (W1 only) | **no** (stops W3) | game path lists MISSING |
| Timestamp / weekly change | **not proven** — n=2907 / 32 teams **identical for weeks 1–8** | W1 only | stale vs W7 designated pack | unknown here |
| Schema matches consumer | unknown (2907 vs research pack 809 = different grain/filter) | official `depth_team` 1–3 skill | nowcast expects `nfl_dp_injuries` columns | season priors use 5g rolling cols |
| Coded SoT agrees | **No** — season engine **ignores** weekly/official while packaged W1 exists (`loaders.py:7-17,1653-1682`) | ignored if pack present | season uses `packaged_injury_paths`, not this table, on the research emit | season prefers this table **when a DB session exists**; game research path does not |
| Appropriate for game EPA mean | Depth does not enter `NflGameInputs` today | n/a | W3 cannot replace W7 designated / W8 official | would be a **second** strength SoT vs nflverse W1–W7 |

## Verdicts

### `nfl_dp_injuries` — NOT authoritative for W8
Max week 3 vs nflverse designated week 7 (n=153) and W8 official MISSING. Wiring this would **regress** the overlay. Do not invent W8 from W3.

### `nfl_dp_official_depth_charts` — NOT current
Week 1 only. Same vintage class as packaged W1.

### `nfl_dp_depth_chart_weekly` — populated, **not proven authoritative**
- Row counts are **flat** across weeks 1–8 (2907 every week). That is compatible with a copied snapshot stamped onto each week, not with a demonstrated weekly refresh. This ticket did not (and must not) invent player-diff proof.
- Season engine SoT is still packaged `nfl_depth_chart_2026_w1.json` (as_of **2026-08-13**). The loader **explicitly skips** this table when the pack exists.
- Game forecast does not consume depth volume (`GAP_SIM_VOLUME`). Wiring warehouse depth into `simulate_nfl_game` would be a **new model**, not a consume-fix.
- Grain ≠ research W8 pack (809 filtered skill+defense rows).

### Rolling / KAV warehouse — not authorized here
Every restore game already flags `nfl_dp_team_rolling_features_weekly` and `kav_5g_warehouse` MISSING. Proving those tables current is a **separate** RO audit + SoT decision. Not this wire.

## Appropriate use (if later CLEAR)

| use | ok? | condition |
|---|---|---|
| Access/completeness probe (RO SELECT counts) | already done | keep READ ONLY |
| Replace W7 designated injury overlay | **no** | warehouse injuries stale |
| Replace season W1 depth SoT | **not yet** | need week-over-week identity diffs + pack retirement decision |
| Drive `simulate_nfl_game` volume | **not yet** | would change the game mean model; needs design + tests |
| Silent fallback when nflverse pack exists | **no** | silent fallback is the failure mode this ticket forbids |

**Needs CLEAR to change:** coded SoT (`_PACKAGED_DEPTH_FILES` / loader skip), any `DATABASE_URL` SELECT on the research emit, any merge/deploy.
