# NCAAM Lab fair engine — research materialize (#14 Phase E)

**Status:** research only · Contract v1 / Phase E Lab Protocol LOCKED  
**Branch target:** `deploy-vercel`  
**As of:** 2026-09-04  
**Protocol:** [`docs/lab/NCAAM_FAIR_LAB_PROTOCOL_v1.md`](../../docs/lab/NCAAM_FAIR_LAB_PROTOCOL_v1.md)

## What this is

Research Lab fair path for `ncaam`:

- Schedule SoT **D** (Odds `event_id` + commence + B7 `team_id`, fail-closed)
- KenPom AdjEM **feed** as-of ≤ tip (snapshots)
- `fair_spread_home` (B2) + optional `fair_total` with stated method
- B1 close consensus joined for later scorecard
- Continuity tagged `PRIOR` / `UNKNOWN` only (never fake `SETTLED`)

## What this is not

- Not Edge Board populate / PLAY / Conf% / props
- Does **not** write `kei_lines_ncaam.json` or assemble product JSON
- No Odds densify / credit burns
- No #12 GO-2
- Scorecard fill is a **follow-up** — protocol frozen first

## How to run

From repo root (uses Path A parquet + KenPom snapshots already in tree).
Canonical CLI is under `apps/web/scripts/` (web Python allowlist / house path):

```bash
# Train-A (default) — 2022-11-07 → 2023-03-12
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut train_a

# Test-A OOS — 2023-11-06 → 2024-01-28
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut test_a

# Full Path A universe (2025 pocket still OUT)
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut universe_path_a

# Summary only
python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut train_a --dry-run

# Optional thin wrapper (same behavior):
python3 scripts/lab/ncaam_fair_materialize.py --cut train_a
```

Requires: `polars`, `pyarrow`. Working directory may be repo root; script adds
`apps/web` + `apps/web/src` to `sys.path`.

## Cut windows (LOCKED)

| `--cut` | Tip dates | Role |
| ------- | --------- | ---- |
| `train_a` | 2022-11-07 → 2023-03-12 | Train (Valid-A folded in) |
| `test_a` | 2023-11-06 → 2024-01-28 | OOS test |
| `universe_path_a` | 2022-11-01 → 2024-01-28 | Universe; 2025 pocket OUT |

Odds: Path A only (`apps/web/data/raw/odds/{open,close}` →
`apps/web/data/processed/ncaab_historical_odds_open_close.parquet`). Path B never.

## Outputs

Under `data/ops/lab/ncaam/`:

| File | Contents |
| ---- | -------- |
| `ncaam-fair-lab-{cut}-latest.parquet` | Lab fair rows |
| `ncaam-fair-lab-{cut}-*.manifest.json` | Counts + leakage audit + paths |
| `ncaam-fair-lab-protocol-v1.json` | Frozen protocol machine twin |

## Tests

```bash
cd apps/web && PYTHONPATH=.:src python3 -m pytest tests_pipeline/test_ncaam_lab_fair.py -q
```

Covers fail-closed B7 joins, open-timestamp honesty filter, and KenPom as-of
leakage rejection.

## Parallel track

ESPN Schedule SoT A is a separate agent. Lab does not block on it. Field
`espn_game_id` is present and null for future crosswalk.
