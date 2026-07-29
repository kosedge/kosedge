# NFL Narrow Second-Order Path — Report

Generated: 2026-07-29T05:55:00Z  
Branch: `nfl-second-order-edge`  
Parent baseline: `nfl-path-to-95-report.md` (score **7.6 / 10**, selective PLAY GREEN)

## Verdict

Narrowed the Grok-scale A–H build into a **holdout-safe, additive** slice: **E (priority) + H + B + thin A + light D**. Stripped unfinished OTC/Spotrac/PFF. **Did not re-run full PLAY/holdout warehouse** in this session (unit pure-fn coverage green; materializer dry-run required before promoting weights). Product gates unchanged until confirmatory holdout.

| Gate | Status |
| --- | --- |
| `selective_play_ready` | **true** (unchanged claim; v2 PLAY band) |
| `betting_product_ready` | **false** (full-slate still RED) |
| Honest model score | **7.7 / 10** (+0.1 provisional for shipping E/H/D wiring; **not** a holdout-confirmed bump) |

---

## 1) Reverted / stripped vs kept vs shipped

### Stripped (this session)
- **OTC / Spotrac / PFF** client skeletons removed from `external_sources.py` (deferred markers only).
- CLI status no longer advertises OTC/PFF as live paths.
- Fancy multi-signal coach latent **slimmed** to 4th-down residual + tempo only (PROE / pass-state tilt ignored).

### Kept from prior Grok commits (hardened)
- Migration **043** tables: PBP personnel/wp cols, VC weather cache, external cache, participation, personnel efficiency, sub elasticity, coach aggression weekly, matchup pack cols.
- **B** Personnel efficiency materializer + framework factor (elasticity weight default **lowered** 0.35 → 0.15).
- **H** Visual Crossing overlay with graceful skip → Open-Meteo / climatology.
- Participation / draft ingest CLI (nflverse; not PFF).

### Newly shipped (narrow path)
| ID | Module | What landed |
| --- | --- | --- |
| **E** | Info velocity | Week-over-week upgrade/downgrade + hours since change; factor `info_velocity` in decomposition; wired through nowcast → sim/tasks/routes |
| **H** | Travel×weather | Factor `travel_weather_interaction` (bounded; skips if weather or travel missing) |
| **B** | Personnel | Kept + light `usage_elasticity_tilt` helper for player usage |
| **A** | Coach thin | `coach-agg-v1-thin`; smaller default caps/weights |
| **D** | Error regime | Factor `error_regime`: **stdev widen + confidence penalty only** (0 point shift) |

### Deferred entirely
- PFF scraping, OTC/Spotrac org belief, scheme-fit interactions, SGP/parlay correlation upgrades.

---

## 2) Migrations

| File | Purpose |
| --- | --- |
| `043_nfl_second_order_edge.sql` | Foundation (already on branch) |
| `044_nfl_narrow_second_order.sql` | Injury WoW index + `nfl_dp_injury_info_velocity_weekly` + matchup velocity cols |

---

## 3) Leakage / degrade rules

- Personnel / coach: join **week = game.week − 1** (existing `assert_no_future_leakage`).
- Info velocity live path: latest week vs prior week listings (same pattern as live nowcast; historical supervised joins should use `nfl_dp_injury_info_velocity_weekly` as_of W−1 when materializer is run).
- Disabled factors mark `available=True` with 0 points (no coverage penalty).
- VC / travel×weather: graceful skip → 0 contribution when feeds missing.

---

## 4) Tests

`tests/test_nfl_second_order_edge.py` — pure fns for personnel, thin coach, info velocity, travel×weather, error regime, decomposition wiring, VC-only status.  
Also green: `test_nfl_injury_nowcast.py`, `test_nfl_handicapping_framework.py`.

---

## 5) Holdout / PLAY metrics

**Not re-run this session** (no warehouse materialize + full-slate re-sim).

| Metric | Status |
| --- | --- |
| PLAY confirmatory ATS/CLV (v2) | Prior GREEN — assume held until re-grade |
| Supervised v3 holdout | Prior GREEN — new factors **not** in supervised FEATURE_KEYS yet |
| Full-slate ATS/CLV | Prior RED |

### Dry-run grading note (ops)
1. Apply `043` + `044`.
2. `python -m data_platform_nfl.cli --normalize-pbp-from-raw --replace-normalized --seasons=2023,2024,2025`
3. `--materialize-personnel-efficiency --materialize-coach-aggression --seasons=...`
4. Board sim; inspect `decomposition.factor_contributions` for `info_velocity`, `travel_weather_interaction`, `error_regime`, `personnel_efficiency`, `coach_aggression`.
5. Ablation: disable new factors via env → compare PLAY ATS/CLV on confirmatory window. **Promote weights only if holdout does not worsen** (same discipline as ST KAV / QB).
6. If holdout worsens: set `NFL_FRAMEWORK_INFO_VELOCITY_ENABLED=false` (etc.) — do not leave broken imports.

---

## 6) Model health

| Area | Light |
| --- | --- |
| KAV v3 + selective PLAY gates | **GREEN** (untouched product path) |
| Simulator / Railway-safe degrade | **GREEN** (new factors optional / skip) |
| Info velocity (E) | **YELLOW** — shipped + unit tested; needs live board + holdout ablation |
| Weather VC (H) | **YELLOW** — code path ready; needs `VISUAL_CROSSING_API_KEY` |
| Personnel / coach materializers (B/A) | **YELLOW** — code ready; needs PBP normalize + materialize |
| Error regime (D) | **YELLOW** — widens uncertainty only; monitor PASS rate |
| OTC/PFF/Spotrac / scheme / SGP | **RED** — deferred by design |
| Full-slate product readiness | **RED** |

---

## 7) Gaps to 9.5

1. Confirmatory holdout ablation for E/H/B/A/D before raising weights.
2. Materialize personnel/coach + optional info-velocity weekly cache for 2023–25.
3. Live 2026 paper→stake under locked v2 as scores land.
4. Supervised FEATURE_KEYS only if chronological holdout improves.
5. Keep ST KAV / QB continuity **unpromoted**.

---

## 8) Env keys needed from user

| Var | Required? | Purpose |
| --- | --- | --- |
| `VISUAL_CROSSING_API_KEY` (or `VISUALCROSSING_API_KEY`) | Optional | Prefer VC weather (~1000/day free); else Open-Meteo |
| `NFL_VC_WEATHER_ENABLED` | Optional (default true) | Toggle VC preference |
| `NFL_FRAMEWORK_INFO_VELOCITY_ENABLED` | Optional (default true) | Kill-switch for E |
| `NFL_FRAMEWORK_TRAVEL_WEATHER_ENABLED` | Optional (default true) | Kill-switch for H interaction |
| `NFL_FRAMEWORK_ERROR_REGIME_ENABLED` | Optional (default true) | Kill-switch for D |
| `NFL_FRAMEWORK_PERSONNEL_ENABLED` / `NFL_FRAMEWORK_COACH_AGGRESSION_ENABLED` | Optional | Kill-switches for B/A |
| `NFL_PRODUCT_GATE_STATUS=YELLOW` | Product | Surface selective PLAY tags |

**Not needed now:** `OTC_*`, `SPOTRAC_*`, `PFF_*`.

---

## 9) Framework version

`nfl-handicap-core-v3.1` — additive factors; MC loop untouched.
