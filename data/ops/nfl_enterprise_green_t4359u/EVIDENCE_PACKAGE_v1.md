# t4359u evidence package v1.0.1 — local fair-line path

**Spec:** `nfl-model-spec-t4359u-v1` / `1.0.1`  
**Spec file:** `docs/nfl/NFL_MODEL_SPEC_t4359u_v1.md`  
**Addendum:** `imv-textcheck-7c02313d` (T-01..T-10; T7 frozen)  
**Authority:** DECISION_RYAN_t4359u + Ryan t4366u + IMV text-check `7c02313d`  
**Publication:** NFL NO-GO. Coming Soon ON. Draft PR only. Do not merge or deploy.

IMV text-check: **PASS WITH CONDITIONS** (engineering spec candidate only).  
Ruling sha256: `7c02313d4087ca25f5f359eacf31805fc8418096e8b7474fe7857bde2d699bf8`  
Box path (CoS): `fg-repair/imv-gate1-review-2026-10-02/IMV_TEXTCHECK_PR631_NFL_MODEL_SPEC_t4359u_v1.txt`

This package is for CoS/IMV submission-readiness. It does **not** rerun accepted W4–W6 seals.

**This path is not the IFB candidate.** Injury weights=0 ≠ `injury_model=NONE_BY_DESIGN` (IFB scope `41effd43`; still needs separate spec + S-6 + F-8). Markets certified separately (gate matrix `6f1a95b9`). Demo/week6 numbers are **ENGINEERING FIXTURE** only. `TOTAL_PLAY` disabled. No holdout-tuning. Independent reproduction is **MISSING**.

---

## Reproduce (local, no Beat, no Railway)

```bash
# 1) Pins
sha256sum -c data/ops/nfl_enterprise_green_t4359u/SHA256SUMS

# 2) Engine tests for the claimed path (includes week-cap bind)
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_enterprise_green_path.py \
  tests/test_nfl_simulator.py \
  tests/test_nfl_regression_decompose.py \
  tests/test_nfl_564_remediation.py \
  tests/test_nfl_week_cap_bind.py -q
# Independent reproduction: MISSING.
# test_untyped_null_week_bind_raises_ambiguous_parameter skip (no local Postgres) is NOT EVIDENCED.

# 3) ENGINEERING FIXTURE only — HOME demo (BUF vs KC, week 6, overlays off)
cd ../..
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_enterprise_green_local.py \
  --fixture demo --out /tmp/t4359u-demo.json

PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_enterprise_green_local.py \
  --card data/ops/nfl_enterprise_green_t4359u/demo_card.json

# 4) ENGINEERING FIXTURE only — manual weekly slate (scheduling off; T7 neutrals stay blocked)
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_enterprise_green_local.py \
  --fixture week6
```

Scheduling must stay off. If `NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED=true` the runner BLOCKS.

---

## T-09 — simulator frozen-version assertion v1→v3.1

`test_simulator_baseline_unchanged_without_matchup_features` pins `nfl-handicap-core-v3.1` because that is the locked production framework identity already used by `LOCKED_SCORING` / this spec §3; the old `v1` pin was stale and was not a scoring, holdout, or factor change.

---

## T-10 — no holdout-tuning

This path does not tune, select, fit, or certify any parameter against the 2024–25 holdout. Holdout remains sealed. `no_holdout_tuning=true`.

---

## T-08 — week-cap bind + independent repro

- `tests/test_nfl_week_cap_bind.py` is in the claimed test list.
- `test_prior_season_null_week_cap_sql_is_typed` is **untouched** (frozen overview null-week assertion).
- `test_untyped_null_week_bind_raises_ambiguous_parameter` skip without local Postgres is **NOT EVIDENCED**.
- Independent reproduction remains **MISSING**.

---

## Demo receipt pins (this revision) — ENGINEERING FIXTURE only

| Field | Value |
|-------|--------|
| fixture_class | ENGINEERING_FIXTURE |
| game_id | `t4359u-DEMO-KC@BUF` |
| site_class | HOME |
| seed | 4359 |
| simulations | 2000 |
| spec_sha256 | `e57314faffb41343e638cbb191b5dd0449ab39159e5d42dfe2f0c2faf6f3fa16` |
| run fingerprint | `5f15656879a8e993e038dfd05a4ae0b31684b4af3c8622a2ae00b5748f97e994` |
| fair_spread_home | -2.47 |
| fair_total | 45.51 |
| home_win_prob | 0.5675 |
| away_win_prob | 0.4325 |
| fair_home_ml | -131 |
| fair_away_ml | 131 |
| cert_status_spread / total / ml | NOT_CERTIFIED |
| ifb_candidate | false |
| total_play_enabled | false |
| no_holdout_tuning | true |
| independent_repro | MISSING |
| overlays_off | true |
| injury_status | OVERLAY_OFF_UNAVAILABLE |
| hfa_status | LOCKED_HOME_1_05 |
| schedule_enabled | false |
| publication | NFL_NO_GO |

Checked-in twins: `demo_receipt.json`, `week6_receipt.json`. Same card + seed must reproduce the fingerprint. A second run that differs is a FAIL for this path.

### File pins (this revision)

| Path | sha256 |
|------|--------|
| `docs/nfl/NFL_MODEL_SPEC_t4359u_v1.md` | `e57314faffb41343e638cbb191b5dd0449ab39159e5d42dfe2f0c2faf6f3fa16` |
| `services/model-service/src/services/nfl_enterprise_green_path.py` | `8e058a4bc13f7b5e0d94392dbe2b407c0e480bfdcfa16e12e307c6e77c08d663` |
| `scripts/nfl/run_nfl_enterprise_green_local.py` | `db63ee161f5618f5b5c55581f941c0b89948da9bfdc3d0886d35407d673a6ce0` |
| `services/model-service/tests/test_nfl_enterprise_green_path.py` | `0d0e9bed86dda07e18cb4694080a3060556dc393999db56992cb349d291abfa1` |
| `data/ops/nfl_enterprise_green_t4359u/demo_card.json` | `ab4eba30adb2f8d770ac41cd6c83b850bea18f701187f3e9f794534d524ad18b` |
| `data/ops/nfl_enterprise_green_t4359u/demo_receipt.json` | `f9544631df8ad1221fb007d62603b209112fa7f0bf8c10a0240c2893ce212100` |
| `data/ops/nfl_enterprise_green_t4359u/week6_receipt.json` | `bcaefb4fab8ed73ac09f3fbf2660105d04dbd34c91d7b5341487c2e581e6f7a8` |
| `data/ops/nfl_enterprise_green_t4359u/IMV_TEXTCHECK_PR631_POINTER.md` | `a69610574e378d11bce7d307011ce062af6538f5574f1a00a729821ca4ff4880` |
| packaged EPA priors 2026 | `a4e3fa90df77aa8bba78c626827b03a6d2c71f651b9c32f852c499ca8a6922b6` |

---

## Fail-closed cases covered by tests

- Missing `kickoff_utc` → BLOCKED, non-empty `reason_codes` (`MISSING_REQUIRED_INPUT`)
- `site_class=UNKNOWN` → BLOCKED `UNKNOWN_HFA_REFUSED`
- `site_class=NEUTRAL` → BLOCKED `T7_BLOCKED_NEUTRAL_SITE` (no invented 0.0 HFA; T7 frozen)
- rest `7.0` without `*_source=explicit_named_value` → BLOCKED
- offense/defense index `1.0` without explicit source → BLOCKED
- any `injury_impact` / nowcast key, including `0.0` even if tagged explicit → BLOCKED `UNKNOWN_INJURY_AS_ZERO_REFUSED` (not IFB)
- `unlock_overlays=true` → BLOCKED
- `NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED=true` → BLOCKED
- Empty `reason_codes` only on READY
- GitHub weekly-operate cron remains commented

---

## Accepted seals not rerun

W4 `3317280e` / W5 `6713c273` / W6 `4b7ef1b5` + erratum `beadf892`. Seal script `20a4d8bf`. 1A-D implementation `4d7e53ca` accepted but component not PASS (T7, Q9).

---

## Still blocked (not invented)

- T7 (1A-D B1) — Ryan A vs B. Frozen. Neutral stays `T7_BLOCKED_NEUTRAL_SITE`.
- ADD141 Q9 — Ryan Mac 7-name search + IMV class
- E-9 — after T7 + Q9
- IFB candidate / `injury_model=NONE_BY_DESIGN` — separate spec + S-6 + F-8 (`41effd43`)
- Market cert (spread/total/ML) — gate matrix `6f1a95b9`
- Full-engine FAIL until pre-registered rerun (`f4c61237`)
- Predictive GREEN / holdout 2024–25 / injury overlays ON / W8 capture / deploy / Coming Soon OFF
- Independent reproduction — **MISSING**

---

## t4366u weekly slate (manual, scheduling off) — ENGINEERING FIXTURE only

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_enterprise_green_local.py --fixture week6
```

| Field | Value |
|-------|--------|
| fixture_class | ENGINEERING_FIXTURE |
| n_ready / n_blocked | 2 / 3 |
| blocked reasons | `T7_BLOCKED_NEUTRAL_SITE`, `MISSING_REQUIRED_INPUT` (null week), `STRENGTH_MISSING` |
| week fingerprint | `a7bc16b41f3bd9ac69bbb91cc84135593dc8382f009b126777e013a187aa5ef1` |
| T7 expectation | unchanged (no option A/B) |
| Overview null-week test | `test_prior_season_null_week_cap_sql_is_typed` not edited |
