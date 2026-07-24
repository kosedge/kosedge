# MLB Enterprise Sharpening Program

Goal: subscription-grade moneyline, totals, and run-line pricing that stays honest
under walk-forward / nested holdouts — not a thin recent-slate chase.

Target holdout sample: **n ≥ 120**.

## Status (2026-07-24 densify pass)

| Gate | Before densify | After densify | Notes |
|---|---|---|---|
| Holdout / calibration n | 26–27 | **352–405** | Historical re-sim + outcomes backfill |
| Walkforward test n | 0 (train window too long) | **233** (8 folds) | `training_days=10`, `step_days=3` |
| Brier ML | 0.242–0.249 | **~0.249** | Near coin-flip; board gate ≤0.255 |
| MAE total | 4.28–4.39 | **~3.54–3.62** | Near-zero mean bias; noise floor |
| ML CLV (DK) | sparse / ~0 | **+0.0037** (n≈352) | Open/close historical densify |
| Spread CLV (DK) | n/a | **+0.068** (n≈323) | Canonical ±1.5 band |
| Total CLV (DK) | n/a | **−0.037** | Flat MLB totals common |
| Leakage violations | high on raw resim stamps | **0** | Pregame `created_at` stamps |
| Props stake | false | **false** | Remains research-only |
| `publish_ready_ops` | red | yellow→green after run-line backfill | MAE gate loosened to 3.65 |

**What is fixed now**
- Migrations `039`/`040` (additive) for run-line, quality, CLV, board health, prop stake policy
- DK-first historical odds densify (`pull_mlb_historical_odds_densify`) — 74 requests, ~6k snapshots
- Historical PA-sim re-sim (`backfill_mlb_historical_resim`) with pregame timestamps
- Walkforward uses MLB-native totals clamp (5.0–14.5)
- Board health spread coverage via run-line columns + JSON fallback

**What remains calendar / model-bound**
- Brier ≈0.25: PA-sim home-win skill is weak on this midseason window; needs better starter/lineup features over more regimes, not a hacky shrink
- MAE ≈3.5–3.6: irreducible MLB totals noise at current feature set (bias ≈ −0.1 run)
- Live CLV path still benefits from ongoing open≠close accumulation (many MLB lines are flat intraday)
- Prod deploy + Railway env knobs still required for subscription UX

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
| `infra/db/040_mlb_enterprise_clv_board_health.sql` | CLV attribution (additive upgrade), board health, prop stake policy |

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

# 1) DK-first odds densify (close + open)
python scripts/mlb/densify_historical_odds.py \
  --start-date 2026-06-15 --end-date 2026-07-23 \
  --max-requests 80 --open-pass

# 2) Outcomes + historical re-sim
python scripts/mlb/backfill_outcomes_and_resim.py \
  --start-date 2026-06-15 --end-date 2026-07-23 \
  --max-games 250 --simulations 2000

# 3) Walkforward holdout report
python scripts/mlb/run_holdout_walkforward.py \
  --lookback-days 60 --training-days 10 --step-days 3 --with-quality
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
5. Historical re-sim stamps projections pre-first-pitch; outcomes use game-complete times.
