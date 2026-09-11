# B2-PACE-NEUTRAL-v1 — Frozen Preregistration

**Status:** FROZEN for Train-A research evaluation only  
**Not promoted. Not production default. Not scored on Test-A, pocket_2025, or sealed 2024–25 holdout.**  
**Parent candidate `B2-PACE-v1` remains immutable under its existing ID.**

## Immutable identifiers

| Field | Value |
| --- | --- |
| Candidate ID | `B2-PACE-NEUTRAL-v1` |
| Method ID | `kenpom_adjem_pit_tempo_gated_hca_v1` |
| Parent (unchanged) | `B2-PACE-v1` / `kenpom_adjem_pit_tempo_plus_game_hca_v1` |
| Incumbent materialize | `B2-C0-v1` / `kenpom_adjem_plus_hca_v1` |
| Research aliases | none (do not reuse “C3”) |

## Exact population

- **Development / freeze evidence:** Train-A only — tip dates in Lab cut window `2022-11-07` → `2023-03-12` as stamped on `ncaam-fair-lab-train_a-latest.parquet`.
- **Forbidden for this candidate in this phase:** Test-A scoring, pocket_2025, sealed 2024–25 holdout, any production board.

## Train-A-only development boundary

1. May join Schedule SoT packs `2022_23` and `2023_24` only.
2. Must refuse paths containing `holdout_2024_25`, `test_a`, `pocket_2025`, or `ncaam_official_schedule_2024_25`.
3. Single authorized Train-A diagnostic run after freeze; **no post-result retune**.

## Neutral-site eligibility definition

| `venue_status` | Source | Eligible for fair? | HCA |
| --- | --- | --- | --- |
| `confirmed_home` | SoT `neutral_site=false` after venue contract | YES | `2.8696` |
| `confirmed_neutral` | SoT `neutral_site=true` after venue contract | YES | `0.0` |
| `unknown` | missing join, ambiguous key, or contract conflict | **NO** | — |

Tournament ≠ auto-neutral. Designated home ≠ auto home-court when postseason venue token conflicts.

## Exact formula (immutable under this ID)

```
adjem_diff = clip(home_adjem - away_adjem, -30, +30)
expected_possessions = (home_adjt + away_adjt) / 2
hca = 0.0 if venue_status==confirmed_neutral else 2.8696  # only if confirmed_home
raw_home_margin = adjem_diff * (expected_possessions / 100) + hca
fair_home_margin = clip(raw_home_margin, -28, +28)
```

Operation order identical to parent except HCA gate. Non-finite AdjEM/AdjT/PIT failure → no fair.

## Exclusions

- SETTLED / post-tip KenPom
- Unknown venue rows (fail closed, not coerced)
- Ambiguous SoT duplicate keys
- Market/injury/open-shrink features
- Any change to parent `B2-PACE-v1` behavior

## Metrics (Train-A research evidence)

Primary descriptive:

- Overall MAE / RMSE / signed bias / cal slope for NEUTRAL vs C0 / PACE / B1
- Paired ΔMAE bootstrap (B=2000, seed=`20260909`, game grain): NEUTRAL−PACE, NEUTRAL−B1, NEUTRAL−C0
- Venue-status split metrics (home / neutral / unknown counts)

**Not** acceptance for promotion. Train-A cannot clear pocket/holdout gates.

## Acceptance / rejection gates

| Gate | Applies now? | Rule |
| --- | --- | --- |
| Train-A plumbing + tests green | YES | Required to land research branch |
| Train-A ΔMAE vs PACE | Descriptive only | No threshold shopping |
| Pocket / holdout predictive gates | **NO — blocked** | Require Ryan unseal + independent validation |
| Materialize / board / PLAY | **NO** | Ryan-only |

Future pocket/holdout gates (preregistered, not run): eligible n≥100; leakage=0; no SETTLED; report paired bootstrap vs B1 and vs PACE; unknown venue rate documented. Exact numeric cutoffs for promotion remain Ryan-only after independent review.

## Missing-data behavior

| Condition | Behavior |
| --- | --- |
| Missing/non-finite AdjEM or AdjT | ineligible / fair null |
| PIT as-of missing or > tip | ineligible |
| Unknown venue | ineligible |
| Missing actual_margin | excluded from scored diagnostics only |

## Rollback / non-promotion status

- Default remains `B2-C0-v1` via `compute_fair_b2`.
- `B2-PACE-v1` unchanged and non-default.
- `B2-PACE-NEUTRAL-v1` research-only; delete/revert branch restores prior tip with no production model change.
- Candidate ID must not be reused for a different formula.

## Authorized Train-A command

```bash
cd <repo>
PYTHONPATH=apps/web/src python3 apps/web/scripts/lab_ncaam_b2_pace_neutral_v1_train_a.py
```

Output: `data/ops/lab/ncaam/ncaam-b2-pace-neutral-v1-train-a-diagnostics.{json,md}`  
Classification: **research evidence only**.
