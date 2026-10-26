# t4359u evidence package v1 — local fair-line path

**Spec:** `nfl-model-spec-t4359u-v1` / `1.0.0`  
**Spec file:** `docs/nfl/NFL_MODEL_SPEC_t4359u_v1.md`  
**Spec sha256:** `506aa07e9f9d4eda5c24fd20d4767711ce5d64d064966a3de6fe5b09071e8dcf`  
**Addendum:** `t4366u-stage12` (T7 frozen; weekly manual slate)  
**Authority:** DECISION_RYAN_t4359u + Ryan t4366u  
**Publication:** NFL NO-GO. Coming Soon ON. Draft PR only. Do not merge or deploy.

This package is for CoS/IMV submission-readiness. It does **not** rerun accepted W4–W6 seals.

---

## Reproduce (local, no Beat, no Railway)

```bash
# 1) Pins
sha256sum docs/nfl/NFL_MODEL_SPEC_t4359u_v1.md
# expect 506aa07e9f9d4eda5c24fd20d4767711ce5d64d064966a3de6fe5b09071e8dcf

sha256sum services/model-service/src/services/nfl_season_engine/data/nfl_team_epa_priors_2026.json
# expect a4e3fa90df77aa8bba78c626827b03a6d2c71f651b9c32f852c499ca8a6922b6

# 2) Engine tests for the claimed path
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_enterprise_green_path.py \
  tests/test_nfl_simulator.py \
  tests/test_nfl_regression_decompose.py \
  tests/test_nfl_564_remediation.py -q
# expect: 56 passed, 1 skipped (local-Postgres null-week proof; assertion file untouched)

# 3) Deterministic HOME demo (BUF vs KC, week 6, overlays off)
cd ../..
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_enterprise_green_local.py \
  --fixture demo --out /tmp/t4359u-demo.json

# or the checked-in card:
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_enterprise_green_local.py \
  --card data/ops/nfl_enterprise_green_t4359u/demo_card.json

# 4) Manual weekly slate (scheduling off; T7 neutrals stay blocked)
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_enterprise_green_local.py \
  --fixture week6
```

Scheduling must stay off. If `NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED=true` the runner BLOCKS.

---

## Demo receipt pins (this revision)

| Field | Value |
|-------|--------|
| game_id | `t4359u-DEMO-KC@BUF` |
| site_class | HOME |
| seed | 4359 |
| simulations | 2000 |
| fair_spread_home | -2.47 |
| fair_total | 45.51 |
| home_win_prob | 0.5675 |
| away_win_prob | 0.4325 |
| fair_home_ml | -131 |
| fair_away_ml | 131 |
| run fingerprint | `238e9c133768c8ac3be4bfe432ff0107845243dc7dacbf873c990dca440207e9` |
| spec_sha256 | `506aa07e9f9d4eda5c24fd20d4767711ce5d64d064966a3de6fe5b09071e8dcf` |
| packaged EPA sha256 | `a4e3fa90df77aa8bba78c626827b03a6d2c71f651b9c32f852c499ca8a6922b6` |
| overlays_off | true |
| injury_status | OVERLAY_OFF_UNAVAILABLE |
| hfa_status | LOCKED_HOME_1_05 |
| schedule_enabled | false |
| publication | NFL_NO_GO |

Checked-in twin: `data/ops/nfl_enterprise_green_t4359u/demo_receipt.json`.

Same card + seed must reproduce the fingerprint. A second run that differs is a FAIL for this path.

---

## File pins (this revision)

| Path | sha256 |
|------|--------|
| `docs/nfl/NFL_MODEL_SPEC_t4359u_v1.md` | `506aa07e9f9d4eda5c24fd20d4767711ce5d64d064966a3de6fe5b09071e8dcf` |
| `services/model-service/src/services/nfl_enterprise_green_path.py` | `4de4d35d8c4c261b8e8b11d890fb4d574f8e204ed2830fcc5c6e58182dfd8118` |
| `scripts/nfl/run_nfl_enterprise_green_local.py` | `db63ee161f5618f5b5c55581f941c0b89948da9bfdc3d0886d35407d673a6ce0` |
| `services/model-service/tests/test_nfl_enterprise_green_path.py` | `6641a8ce445c834673876a2a2f1fc85cb10550a06ee9b093cdb656f3b88c1379` |
| `data/ops/nfl_enterprise_green_t4359u/demo_card.json` | `0251b88a5f6ddab2ed7ba8b2d55846c67c1204bb3d2955f0da1734e8865aca27` |
| `data/ops/nfl_enterprise_green_t4359u/week6_receipt.json` | `f1cae5bd6af19ff58b7224505af2e804e3dc10e49b82b708eff09159e7b8510d` |
| packaged EPA priors 2026 | `a4e3fa90df77aa8bba78c626827b03a6d2c71f651b9c32f852c499ca8a6922b6` |

Also: `sha256sum -c data/ops/nfl_enterprise_green_t4359u/SHA256SUMS`

---

## Fail-closed cases covered by tests

- Missing `kickoff_utc` → BLOCKED `MISSING_REQUIRED_INPUT`
- `site_class=UNKNOWN` → BLOCKED `UNKNOWN_HFA_REFUSED`
- `site_class=NEUTRAL` → BLOCKED `T7_BLOCKED_NEUTRAL_SITE` (no invented 0.0 HFA)
- rest `7.0` without `*_source=explicit_named_value` → BLOCKED
- offense/defense index `1.0` without explicit source → BLOCKED
- injury impact `0.0` without explicit source → BLOCKED `UNKNOWN_INJURY_AS_ZERO_REFUSED`
- `unlock_overlays=true` → BLOCKED
- `NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED=true` → BLOCKED
- GitHub weekly-operate cron remains commented

---

## Accepted seals not rerun

W4 `3317280e` / W5 `6713c273` / W6 `4b7ef1b5` + erratum `beadf892`. Seal script `20a4d8bf`. 1A-D implementation `4d7e53ca` accepted but component not PASS (T7, Q9).

---

## Still blocked (not invented)

- T7 (1A-D B1) — Ryan A vs B. Frozen until Ryan authorizes after IMV packet. Neutral stays `T7_BLOCKED_NEUTRAL_SITE`.
- ADD141 Q9 — Ryan Mac 7-name search + IMV class
- E-9 — after T7 + Q9
- Full-engine FAIL until pre-registered rerun (`f4c61237`)
- Predictive GREEN / holdout 2024–25 / injury overlays ON / W8 capture / deploy / Coming Soon OFF

---

## t4366u weekly slate (manual, scheduling off)

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_enterprise_green_local.py --fixture week6
```

| Field | Value |
|-------|--------|
| n_ready / n_blocked | 2 / 3 |
| blocked reasons | `T7_BLOCKED_NEUTRAL_SITE`, `MISSING_REQUIRED_INPUT` (null week), `STRENGTH_MISSING` |
| week fingerprint | `03e87f2dec9069b329d0d7bc1b6ffc9874482954dc2ae19dc56b18bde6137267` |
| T7 expectation | unchanged (no option A/B) |
| Overview null-week test | `test_prior_season_null_week_cap_sql_is_typed` not edited |
