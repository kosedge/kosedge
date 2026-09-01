# CFB Chapter 3 — situation Phase 0 brief

**Phase:** Discovery / register. **No pack write.**  
**Depends on:** Chapter 2 (`ce41aaf9`) · Phase 1 remainder (#357) · grading harness (#360, `a9fa0b9b`)  
**Stamp frozen:** `cfb-season-engine-v0.15-power-sot` + 1C–1E + `EFF_CARRY_SHRINK=0.85`  
**Holdout:** Week 1 is **not** a fit sample. W0 is n=6 and already peeked (motivation only).

---

## Purpose

Name the leftover information layer as **classes**, with gates, before anyone types a coefficient.

2B closed carry. UNC 15–10 (vs KEI −16.34) and STAN 37–27 (vs KEI +5.93) are residuals to **explain or block**, not two team patches.

Companion audit: [`docs/CFB_CH3_SITUATION_AUDIT.md`](./CFB_CH3_SITUATION_AUDIT.md).

---

## Classes (not teams)

| #   | Class                    | Question                                                      | First-look surface                          |
| --- | ------------------------ | ------------------------------------------------------------- | ------------------------------------------- |
| 1   | Year-1 / interim HC      | Does compose know coach tenure?                               | `coaching_continuity.py`                    |
| 2   | Portal / new starting QB | Does 1C–1E consume W1 depth charts?                           | `qb_situation.py` + roster packager         |
| 3   | Neutral + long-haul      | Did Dublin use the same flag W1 neutrals will use?            | slate `neutral_site` → `home_field.py`      |
| 4   | Rebuild-offense group    | Pre-shrink 2025 `off_eff` ≤ 35 as a group residual after 0.85 | `off_eff_pre_shrink` on efficiency snapshot |

No class is Stanford. No class is UNC. No class is Hawaii.

---

## File paths (spine)

| Surface                           | Path                                                                                                                                   |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Engine version / shrink / matchup | `services/model-service/src/services/cfb_season_engine/priors.py` (`ENGINE_VERSION`, `EFF_CARRY_SHRINK=0.85`, `MATCHUP_RESPONSE=1.40`) |
| Compose                           | `…/team_projection.py` (`compose_team_projection`, `expected_team_points`)                                                             |
| Coaching                          | `…/coaching_continuity.py`                                                                                                             |
| QB situation (1C–1E)              | `…/qb_situation.py`; packager `scripts/cfb/package_real_roster_2026.py`; overrides `…/qb_situation_overrides.py`                       |
| HFA / neutral                     | `…/home_field.py` (`resolve_hfa_points`)                                                                                               |
| Efficiency carry pack             | `…/data/cfb_efficiency_snapshot_2025_carry_2026.json` (+ web mirror)                                                                   |
| Official slate                    | `apps/web/lib/data/cfb-official-slate-2026.json`                                                                                       |
| Project Game defaults             | `apps/web/app/(pro)/pro/cfb/project-game/page.tsx`                                                                                     |
| KEI menu (travel gap)             | `…/cfb_kei.py` (`rest_travel` not in stack)                                                                                            |
| Grade store (read-only)           | `data/cfb_grades_2026.jsonl` · schema `docs/CFB_GRADE_SCHEMA.md`                                                                       |
| W1 card (read-only)               | `data/ops/cfb-w1-handicap-card-20260831.json`                                                                                          |

---

## Deliverable this PR

1. This brief — contract + file paths.
2. `docs/CFB_CH3_SITUATION_AUDIT.md` — per class: where it lives, what it already moves, what it does not; **one signed prediction per class** dated before W1 finals.
3. **No** JSON pack. **No** `EFF_CARRY_SHRINK` edit. **No** `MATCHUP_RESPONSE` retune. **No** team `if`. **No** `--kei-only` emit.

---

## Gates before any later fit PR

- OSU #1
- BALL@OSU WP ≥ 0.90
- membership only ORE↔MISS and ND↔TEX
- Utah futures untouched
- no team name in an `if`
- if the fit uses W0, Week 1 is holdout
- situation deltas are capped — not a second power rating
- later emit is `--kei-only` only if a fit is authorized

---

## Blocker rule

If the only specification that “fixes” UNC@TCU and HAW@STAN is two team flags → write **`docs/CFB_CH3_BLOCKER.md`** the same way Utah and 2B-order were blocked.

A blocked honest prior beats a model that finishes Saturday with names.

---

## Forbidden

- inventing `s`
- coupling `STRENGTH_NOISE` to “make STAN cover”
- `WEIGHT_OFF_EFF` / roster blend
- 1C–1E revert or a second QB path
- PBP warehouse as live SoT
- fitting before the audit
- using W1 **results** inside Phase 0
- touching the W1 card or grade store except to **read** them

---

## Done

Brief + audit merged. Published KEI unchanged.

**Fit PR does not exist** until this Phase 0 names **one** global lever and the holdout. That is after W1 grades exist — not tonight.
