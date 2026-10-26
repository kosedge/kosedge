# NFL Model Specification — t4359u v1

**Spec id:** `nfl-model-spec-t4359u-v1`  
**Spec version:** `1.0.0`  
**Authority:** `DECISION_RYAN_t4359u_NFL_ENTERPRISE_GREEN_EXECUTION_PROGRAM_v1`  
**Class:** Engineering execution spec (not predictive GREEN; not production GREEN)  
**Publication:** NFL NO-GO. Coming Soon ON. Do not merge, deploy, or publish without required authorization.

This document is the single versioned model specification for producing **fair spreads, totals, and moneyline probabilities** from approved inputs. It reconciles already-accepted components. It does **not** reopen or rerun accepted W4–W6 seals.

---

## 1. One execution route

```text
approved game card
  → required-input gate (fail-closed)
  → site / HFA gate (HOME only until T7 closes)
  → team strength (explicit or packaged EPA; never 1.0 default)
  → LOCKED_SCORING + nfl-handicap-core-v3.1 decomposition
  → Monte Carlo (simulate_nfl_game), overlays OFF, no market blend, no totals-cal defaults
  → fair spread / total / ML
  → fingerprint (canonical sha256)
```

**Local entrypoints (scheduling off):**

```bash
# Single game or slate (fixture or JSON file). No Beat. No cron.
python3 scripts/nfl/run_nfl_enterprise_green_local.py --fixture demo
python3 scripts/nfl/run_nfl_enterprise_green_local.py --card path/to/card.json

# Tests for the path this spec claims
cd services/model-service && PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_enterprise_green_path.py \
  tests/test_nfl_simulator.py \
  tests/test_nfl_regression_decompose.py \
  tests/test_nfl_564_remediation.py -q
```

Implementation: `services/model-service/src/services/nfl_enterprise_green_path.py`.

This is **not** a second model. It is the production engine (`nfl-handicap-core-v3.1` + `simulate_nfl_game`) with a fail-closed input gate and overlays forced off. Deviation from production feature plumbing is labeled, never hidden.

---

## 2. Reused certified / accepted components (do not rerun)

| Component | Status | Pointer (do not rerun) |
|-----------|--------|------------------------|
| W4 seal 130415Z | PASS WITH CONDITIONS | IMV `3317280e`; Ryan t4274u `b3f5b3a9` |
| W5 build 144149Z / seal 145144Z | ACCEPT / PASS | `e08007ba` / `6713c273`; Ryan t4284s14641 |
| W6 build 155318Z / seal 155753Z | ACCEPT / PASS retro-research | `cc83065b` / `4b7ef1b5`; erratum `beadf892` |
| Seal script | pinned v2.4.3 | `20a4d8bf` |
| IMV route-B env | approved t4194u | EV |
| 1A-D implementation | accepted; **component NOT PASS** | `4d7e53ca` — blocked on B1 T7, B2 ADD141 Q9 |
| PC-2 | PASS | `35c64323` |
| 1A-C, 1A-E | approved | frozen; F-EXP KEEP t4111u |
| ADD141 v2 provenance hold | LIFTED; route approved | IMV `c311493a` / `9bd5f4be` |
| Injury design v2 | APPROVED W/ CONDITIONS | `a3dac17a` |
| D-1 / D-4 | ACCEPT W/ COND; D-4 v2 FINAL ACK | `706b5da5` / `9e106128` |
| Week-aware roster INV-1 | PASS | `af37925e` |
| Step 2 v2 / Step 3 | PASS WITH CONDITIONS C-1..C-5; **FROZEN** | `290f548c`; pkg `456134f5` |
| NR-1 | CLOSED MISSING | IMV `5d60ccc0`; report `da5ba6b2` |
| #564 EPA authority + overlays-off remat | accepted engineering | `nfl_epa_authority.py`; packet `3ee91339…` |
| LOCKED_SCORING | frozen scoring equation | `nfl_regression_diagnose.py` |
| Factor freeze 2026-08-25 | no new factor promotion | `docs/NFL_ENTERPRISE_GATES.md` |
| Spread PLAY lock | `spread_play_v2_cap7` | `/NFL_SPREAD_PLAY_LOCKED.md` |
| n=2998 claim | WITHDRAWN t4191u | do not restore |
| Player-production spine | separate surface of the same weekly means | `.cursor/rules/nfl-production-spine.mdc` |

W6 Ryan acceptance file is **EU** (no DECISION file). This spec does not invent one.

---

## 3. Locked scoring (named constants, not unknown defaults)

From `LOCKED_SCORING` / `nfl-handicap-core-v3.1`:

| Name | Value | Role |
|------|-------|------|
| `base_total_points` | 45.3 | League prior total |
| `home_field_points` | 1.05 | Applied **only** when `site_class=HOME` is explicit |
| `base_efficiency_max_total_points` | 5.0 | Certified contribution cap |
| `base_efficiency_max_margin_points` | 6.5 | Certified contribution cap |
| `base_efficiency_total_weight` | 10.5 | Certified weight |
| `base_efficiency_margin_weight` | 16.0 | Certified weight |
| Framework version | `nfl-handicap-core-v3.1` | Decomposition identity |
| Model version stamp | `nfl-v1.5-matchup-sim` | Engine identity |

These are **named certified constants**. They are not substitutes for a missing site, missing EPA, or missing rest. Contribution caps are part of the locked equation; they are not silent clipping of absent inputs.

---

## 4. Required inputs (fail-closed)

A game produces numbers only when **every** required field is present, numeric where required, and not a placeholder.

| Field | Rule |
|-------|------|
| `game_id` | Non-empty string |
| `home_team`, `away_team` | NFL abbreviations; not equal |
| `season`, `week` | Integers; week 1–18 for REG |
| `site_class` | `HOME` only on this spec. `NEUTRAL` → `T7_BLOCKED_NEUTRAL_SITE`. `UNKNOWN` / omitted → `UNKNOWN_HFA_REFUSED` |
| `offense_index_{home,away}` | Explicit number **or** loadable packaged EPA row. Never default `1.0` |
| `defense_index_{home,away}` | Same |
| `rest_days_{home,away}` | Explicit number. `7.0` allowed only as an explicit named value, never a fill |
| `kickoff_utc` | ISO-8601 with timezone |
| `strength_source` | `explicit` or `packaged_epa_prior` |

Missing, empty, NaN, or placeholder (`0` digest, `PLACEHOLDER_*`) → **BLOCKED**. No silent zero, no index `1.0`, no rest `7.0`, no unknown-HFA `1.05`.

### Optional factors (unavailable ≠ zero)

Weather, travel, KAV, personnel, coach, info-velocity, market lines: if absent, the factor is **UNAVAILABLE** and is not applied. Do not write `0.0` as a sourced value.

Injury: overlays **OFF**. Unknown / missing injury is **UNAVAILABLE**, never healthy-zero. Injury-free baseline is a separate IMV scope question — this spec does not treat unknown injury as zero.

---

## 5. Site / HFA / T7 workaround (do not invent Ryan’s answer)

T7 (1A-D B1) is **Ryan-blocked**: option A (expectation → “no site”) vs B (keep frozen + dated exception). This spec does not pick A or B.

| `site_class` | Behavior |
|--------------|----------|
| `HOME` | Apply locked `home_field_points=1.05` (certified named constant) |
| `NEUTRAL` | Refuse. Reason `T7_BLOCKED_NEUTRAL_SITE`. No invented 0.0 HFA |
| `UNKNOWN` / omitted | Refuse. Reason `UNKNOWN_HFA_REFUSED` |

Neutral-site and disputed-site games stay out of the local fair-line slate until Ryan closes T7.

---

## 6. Injury overlays (OFF)

- `force_overlays_off=true`. `unlock_overlays=false`.
- Step 3 frozen. Step 4 blocked. 2024–25 holdout sealed.
- NR-1 CLOSED MISSING — do not repeat that search.
- PR 611 continues the NULL contract **on a separate branch**. This spec path does not enable overlays and does not apply nowcast multipliers.
- Injury weights are forced to 0 for the local run so leftover `or 1.0` / `or 0.0` in the production framework cannot move the line. The stamp is `OVERLAY_OFF_UNAVAILABLE`, not `injury=0 healthy`.

---

## 7. What the engine may not do on this path

- Market blend (`market_spread_home` / `market_total` not passed)
- Linear totals calibration defaults (`apply_linear_totals_calibration=false`)
- ESPN W-L record buckets as persistable strength (#564 refuse)
- Raw `injuries_2026` / nflverse injury maps as sourced zero
- Beat / GitHub cron / Railway deploy
- Holdout open, PLAY/LEAN stake tags, Coming Soon OFF

Monte Carlo seed is required (`seed` integer). Same card + seed ⇒ same fingerprint.

---

## 8. Outputs

On **READY**:

- `fair_spread_home` (home points; negative = home favored)
- `fair_total`
- `home_win_prob`, `away_win_prob`
- `fair_home_ml`, `fair_away_ml`
- `spec_id`, `spec_version`, `spec_sha256`
- `fingerprint` (sha256 of canonical payload)
- `overlays_off: true`
- `injury_status: OVERLAY_OFF_UNAVAILABLE`
- `hfa_status: LOCKED_HOME_1_05` (HOME only)
- `schedule_enabled: false`
- `publication: NFL_NO_GO`

On **BLOCKED**: no numbers. `status=BLOCKED`, `reason_codes=[]`, empty markets.

---

## 9. Weekly pipeline / scheduling

| Surface | State |
|---------|--------|
| GitHub `nfl-weekly-operate.yml` cron | Commented / dispatch-only |
| Local CLI / this spec path | Manual only; refuses to start Beat |
| Railway Beat NFL jobs | Production-owned; this worktree does not deploy; local path does not enable them |
| `NFL_WEEKLY_PIPELINE_SCHEDULE_ENABLED` | Default unset/false for this path |

Platform Reliability owns any future production schedule restore. Engineering Lead does not ungate cron.

---

## 10. Still blocked (Ryan / IMV) — not invented here

| Item | Why blocked | Who |
|------|-------------|-----|
| T7 (1A-D B1) | A vs B site expectation | Ryan |
| ADD141 Q9 (1A-D B2) | 7-name search on Ryan’s Mac, then IMV classification | Ryan + IMV |
| E-9 G-I3 / G-I4 | Eligible only after T7 + Q9 | IMV after R-1/R-2 |
| Full-engine FAIL | Stands until a pre-registered rerun (`f4c61237`) | Alex pre-register; IMV |
| Predictive MAE/bias/calibration/CLV | Not certified | IMV after frozen eval defs |
| Injury Step 4 / 2024–25 holdout | Sealed; reconstructible=0 | IMV + Ryan CLEAR |
| Injury overlays ON | Needs IMV + Ryan CLEAR | Ryan |
| Injury-free baseline as cert scope | IMV must approve scope first | IMV |
| W8 capture | HELD t4196u | IMV |
| W6 acceptance DECISION file | EU — none on file | Ryan |
| Model-service restore / deploy | NO-GO | Ryan |
| Odds API purchase | HOLD t4293u | Ryan |
| Coming Soon OFF / release | Final authorization | Ryan |

---

## 11. Parallel owners (do not duplicate)

- **Alex:** spread compression / market-MAE on ≤2023 only; pre-register full-engine rerun
- **IMV:** gate matrix; frozen eval defs; independent reproduction; injury-free baseline scope
- **DFG:** research-vs-cert eligibility; pass2 odds; prospective injury/roster capture spec
- **Platform Reliability:** restore-readiness; no deploy from this spec
- **Product:** board truth-chain against preview/local; keep NO-GO
- **CoS:** scorecard / registers; submission-readiness before IMV review

---

## 12. Evidence

See `data/ops/nfl_enterprise_green_t4359u/EVIDENCE_PACKAGE_v1.md`.

Pin this spec file’s sha256 in the PR body after each revision.
