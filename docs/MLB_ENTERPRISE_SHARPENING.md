# MLB Enterprise Sharpening Program

Goal: subscription-grade moneyline, totals, and run-line pricing that stays honest
under walk-forward / nested holdouts — not a thin recent-slate chase.

Target holdout sample: **n ≥ 120**.

## What shipped

### P0 — Run-line markets + DK-first odds firewall
- Simulators emit `fair_fg_spread_home`, margin means, and ±1.5 cover probs.
- `mlb_odds_firewall.py`: DraftKings-first book preference; alternate run lines
  outside the canonical band are excluded from CLV aggregation.
- Densify task: `pull_mlb_historical_odds_densify` (open/close passes).

### P0 — Outcomes backfill + historical re-sim / walkforward
- `backfill_mlb_historical_resim` pulls outcomes then re-sims completed games
  (`MLB_ALLOW_HISTORICAL_SIM=true`).
- Walkforward uses **MLB-native totals calibration** (5.0–14.5). The prior
  NFL-era clamp (24–66) destroyed MAE at larger baseball n.

### P1 — CLV including spread/run-line
- `compute_mlb_clv_with_spread` + `run_mlb_clv_attribution`
- Persists to `mlb_clv_attribution` (moneyline / total / spread)
- `GET /mlb/metrics/clv` returns `avg_spread_clv`

### P1 — Quality snapshots + board health
- `mlb_model_quality_snapshots`, `mlb_board_health_snapshots`
- `run_mlb_quality_grading`, `GET /mlb/ops/board-health`, `GET /mlb/fair-lines`

### P2 — Props remain research-only
- `PLAY_STAKE_ELIGIBLE=false` in `mlb_prop_edge_policy.py`
- Seeded in `mlb_prop_stake_policy` (migration 040)

## Migrations

| File | Purpose |
|---|---|
| `infra/db/039_mlb_enterprise_runline_quality.sql` | Run-line columns, quality snapshots, densify ledger |
| `infra/db/040_mlb_enterprise_clv_board_health.sql` | CLV attribution, board health, prop stake policy |

```bash
# Prod apply
psql "$PROD_DATABASE_URL" -f infra/db/039_mlb_enterprise_runline_quality.sql
psql "$PROD_DATABASE_URL" -f infra/db/040_mlb_enterprise_clv_board_health.sql
# or:
python scripts/mlb/apply_039_040_prod.py
```

## Holdout densify runbook (local / Railway)

```bash
export DATABASE_URL=...
export ODDS_API_KEY=...
export MLB_ALLOW_HISTORICAL_SIM=true
export PYTHONPATH=services/model-service

# 1) Ensure schedule/context games exist for the window
# 2) DK-first odds densify (close + open)
python scripts/mlb/densify_historical_odds.py \
  --start-date 2025-04-01 --end-date 2025-06-30 \
  --max-requests 80 --open-pass

# 3) Outcomes + historical re-sim
python scripts/mlb/backfill_outcomes_and_resim.py \
  --start-date 2025-04-01 --end-date 2025-06-30 \
  --max-games 250 --simulations 2000

# 4) Walkforward holdout report
python scripts/mlb/run_holdout_walkforward.py \
  --lookback-days 180 --with-quality
```

Job endpoints (model-service):

- `POST /api/jobs/mlb-historical-odds-densify`
- `POST /api/jobs/mlb-historical-resim`
- `POST /api/jobs/mlb-clv-attribution`
- `POST /api/jobs/mlb-quality-grading`
- `POST /api/jobs/mlb-walkforward-backtest`

## Railway / env knobs

| Variable | Default | Notes |
|---|---|---|
| `MLB_ODDS_PREFERRED_BOOK` | `draftkings` | Firewall preferred book |
| `MLB_DENSIFY_BOOKMAKERS` | `draftkings,fanduel` | Historical densify books |
| `MLB_ALLOW_HISTORICAL_SIM` | `false` | Must be true for re-sim densify |
| `MLB_RUN_DAILY_CLV_ATTRIBUTION` | `true` | Daily cycle stage |
| `MLB_CLV_LOOKBACK_DAYS` | `45` | Beat schedule |
| `MLB_QUALITY_LOOKBACK_DAYS` | `60` | Beat schedule |
| `MLB_MAX_ACCEPTABLE_ECE` | `0.06` | Drift alert |

## Honesty rules

1. No PLAY stake promotion for MLB props without a **pre-registered unused holdout**.
2. `PLAY_STAKE_ELIGIBLE` stays **false** until that holdout clears.
3. Holdout n must approach **≥120** before promotion / go-no-go green claims.
4. DK-first firewall is required for CLV; do not average noisy alternate run lines.
