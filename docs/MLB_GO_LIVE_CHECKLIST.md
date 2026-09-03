# MLB go-live checklist (enterprise upgrade)

## Code on branch

- [x] Migrations `039` + `040`
- [x] Run-line / spread fair outputs from PA + pitch simulators
- [x] DK-first odds densify + CLV (ML / total / spread)
- [x] Quality snapshots + board health
- [x] MLB-native totals calibration bounds (fixes NFL 24–66 clamp)
- [x] Props `PLAY_STAKE_ELIGIBLE=false`
- [x] Scripts under `scripts/mlb/`
- [x] Nowcast SP/lineup shock reprice + shock diagnostics on audit
- [x] Pre-registered unused holdout registry (`unused_holdout_registry.json`)
      excluded from walkforward train / promotion tune
- [x] PA-sim feature sharpening (firmness / rest / platoon / bullpen / dome weather)
- [x] Thin-first densify targeting + evening-close / noon-open snapshot passes

### Stake gate (not yet cleared)

- [ ] Unused holdout eval pass (frozen `2026-07-18`–`23`; reserved `2026-07-25`–`08-10`) before any game-line stake marketing — local unused eval n≈58 today
- [x] Props remain research-only (`PLAY_STAKE_ELIGIBLE=false`)
- [x] Local sprint gates: walkforward n≥120, MAE≤3.5, positive densified CLV, `publish_ready_ops=true` (see `subscription_sharpen_sprint_report.json`)
- [ ] Merge `mlb-subscription-sharpen` → `deploy-vercel` to Railway-deploy sharpened PA-sim

## Prod deploy steps (Railway + warehouse)

### 1) Apply migrations (tracked runner)

On **prod** Postgres (public URL or `railway ssh` into model-service), use the
tracked migration runner — see `infra/db/README.md`. Do **not** replay already-live
SQL; baseline first if `schema_migrations` is empty on a nonempty warehouse.

```bash
DATABASE_URL="$PROD_DATABASE_URL" python scripts/db/migrate.py status
# If unbaselined legacy: stamp through the last version already live, then apply.
# DATABASE_URL="$PROD_DATABASE_URL" python scripts/db/migrate.py baseline --through 053
DATABASE_URL="$PROD_DATABASE_URL" python scripts/db/migrate.py apply
DATABASE_URL="$PROD_DATABASE_URL" python scripts/db/migrate.py status --require-current
```

Historical (pre-runner) note — `039` + `040` were originally applied with:

```bash
# psql "$PROD_DATABASE_URL" -f infra/db/039_mlb_enterprise_runline_quality.sql
# psql "$PROD_DATABASE_URL" -f infra/db/040_mlb_enterprise_clv_board_health.sql
# DATABASE_URL="$PROD_DATABASE_URL" python scripts/mlb/apply_039_040_prod.py
```

Verify:

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'mlb_market_projections' AND column_name LIKE '%spread%';
SELECT play_stake_eligible FROM mlb_prop_stake_policy WHERE market_family = 'player_props';
-- expect: false
```

### 2) Railway model-service env

**Project:** `brave-art` (same as NFL)  
**Services:** `model-service` (api), `model-service-worker`, `model-service-beat`

Set / confirm:

| Variable                          | Value                                                              |
| --------------------------------- | ------------------------------------------------------------------ |
| `DATABASE_URL`                    | Prod warehouse                                                     |
| `REDIS_URL` / `CELERY_BROKER_URL` | Redis                                                              |
| `ODDS_API_KEY`                    | Shared Odds API key                                                |
| `MLB_ODDS_PREFERRED_BOOK`         | `draftkings`                                                       |
| `MLB_DENSIFY_BOOKMAKERS`          | `draftkings,fanduel`                                               |
| `MLB_ALLOW_HISTORICAL_SIM`        | `true` only while running holdout densify; return to `false` after |
| `MLB_RUN_DAILY_CLV_ATTRIBUTION`   | `true`                                                             |
| `MLB_BASE_MODEL_VERSION`          | `mlb-v1-pa-sim`                                                    |

Deploy path (unchanged): GitHub Actions on `deploy-vercel` when
`services/model-service/**` changes, or:

```bash
railway up services/model-service --path-as-root
```

### 3) Holdout densify (one-time / catch-up)

```bash
# From a worker shell or local with prod DATABASE_URL + ODDS_API_KEY
PYTHONPATH=services/model-service \
  python scripts/mlb/densify_historical_odds.py \
  --start-date 2025-04-01 --end-date 2025-07-15 \
  --max-requests 100 --open-pass

MLB_ALLOW_HISTORICAL_SIM=true PYTHONPATH=services/model-service \
  python scripts/mlb/backfill_outcomes_and_resim.py \
  --start-date 2025-04-01 --end-date 2025-07-15 \
  --max-games 300

PYTHONPATH=services/model-service \
  python scripts/mlb/run_holdout_walkforward.py --lookback-days 180 --with-quality
```

Pass criteria: densify/walkforward `sample_size >= 120`, calibrated Brier/MAE not
worse than base beyond promotion guardrails, `props_play_stake_eligible=false`.

### 3b) Unused holdout stake gate (required before marketing)

Pre-registered windows live in
`data/ops/mlb-enterprise-holdout/unused_holdout_registry.json`
(loader: `mlb_unused_holdout.py`):

- **Frozen eval:** 2026-07-18 → 2026-07-23 (exists in local May–Jul densify DB)
- **Reserved future:** 2026-07-25 → 2026-08-10 (label only until warehouse has games)

Rules:

1. Train / tune / calibration fit **must not** use unused dates (enforced in
   walkforward + promotion).
2. **Stake marketing** for ML / totals / run-line only after unused-slice eval
   passes (target n ≥ 120). Densify walkforward alone is not a stake green light.
3. Props remain research-only (`PLAY_STAKE_ELIGIBLE=false`) until a separate props
   unused holdout clears — do not imply paid +EV prop cards.

### 4) Verify API

1. `$MODEL_SERVICE_URL/health` → ok
2. `$MODEL_SERVICE_URL/mlb/fair-lines` → lines with spread fields
3. `$MODEL_SERVICE_URL/mlb/metrics/clv` → includes `avg_spread_clv`
4. `$MODEL_SERVICE_URL/mlb/ops/board-health` → health payload
5. `$MODEL_SERVICE_URL/mlb/ops/go-no-go` → sample_size trending toward 120+

## Blockers if credentials missing

- Cloud agent environments without `DATABASE_URL` / `ODDS_API_KEY` / Railway token
  can ship code + scripts only; densify/holdout metrics must be run against the
  warehouse after deploy.
- Do **not** commit secrets. Use Railway / Vercel / GH Actions secret stores.
