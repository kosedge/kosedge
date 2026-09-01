# CFB Chapter 3 — confirmation join audit

**Phase:** Info-loop wiring. No pack write. No KEI emit.  
**Stamp frozen:** `cfb-season-engine-v0.15-power-sot` + 1C–1E + `EFF_CARRY_SHRINK=0.85`  
**As of:** `2026-09-01`  
**Brief:** [`docs/CFB_CH3_CONFIRMATION_JOIN_BRIEF.md`](./CFB_CH3_CONFIRMATION_JOIN_BRIEF.md)  
**Phase 0:** [`docs/CFB_CH3_SITUATION_AUDIT.md`](./CFB_CH3_SITUATION_AUDIT.md) Class 2

---

## 1. Where 1C–1E reads roster/QB today

| Step                     | Path                                                                    | Role                                                                           |
| ------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Offline pack             | `scripts/cfb/package_real_roster_2026.py`                               | Heuristic ESPN depth → QB1, `classify_qb`, 1D talent, 1E low-sample → snapshot |
| Snapshot                 | `…/data/cfb_real_roster_snapshot_2026.json`                             | Per-team `qb` (+ inspectable `depth[]` / `players[]`)                          |
| Expert class overlay     | `qb_situation_overrides.py` + `cfb_qb_situation_overrides_2026.json`    | Honesty class / named QB1 (UGA/MICH/FSU/LSU/ALA/UF)                            |
| **W1 confirm (this PR)** | `qb_confirmed_starters.py` + `cfb_qb_confirmed_starters_w1_2026.json`   | Week-scoped identity lock into the **same** path                               |
| Runtime index            | `qb_situation.build_qb_situation`                                       | Single 1C–1E index                                                             |
| Compose                  | `team_projection.compose_team_projection`                               | `WEIGHT_QB_SITUATION` / `QB_INDEX_BLEND`                                       |
| Wire                     | `loaders._team_state_from_payload` · `cfb_warehouse/preseason_prior.py` | pack → override → **confirm** → build                                          |

Runtime still does **not** re-read live ESPN depth charts each request. Confirmation is the week SoT join Phase 0 asked for — not a second talent path.

---

## 2. Sample — OSU (unchanged starter)

**Packaged `teams.OSU.qb`:** Julian Sayin · `starter_key=5079712` · `qb_class=incumbent` · `qb_talent=79.93`

**W1 confirm row:** same name/key · `matched_1c1e_input=true` · `via=pack_qb1`

**Flow:**

```text
pack Sayin/incumbent
  → override (none)
  → confirm Sayin (matched)
  → build_qb_situation → qb_situation_index ≈ 1.38 (soft ceiling)
```

Index-driving fields (`qb_class`, `qb_talent`, cast) are untouched by confirmation when keys match.

---

## 3. FSU / LSU (identity already on path)

| Team | Pack heuristic | Override + confirm                                  |
| ---- | -------------- | --------------------------------------------------- |
| FSU  | Dean DeNobile  | Ashton Daniels `4838679` · class `open_competition` |
| LSU  | Landen Clark   | Sam Leavitt `5078810` · class `open_competition`    |

Confirmation locks the **same** keys the expert override already baked. `unconfirmed_starter` cleared to `false` (notes only). Talent remains pack-composite — **not** rematerialized this PR (would be a ratings move).

Open camps **without** a confirmation row: UGA, MICH, ALA, UF.

---

## 4. Diff gate / emit

| Check                                     | Result                       |
| ----------------------------------------- | ---------------------------- |
| Seeded confirmations vs prior 1C–1E input | **all `matched_1c1e_input`** |
| Identity moves                            | **zero**                     |
| `--kei-only` emit                         | **not run**                  |
| Published `cfb_kei_w0_w1_2026.json`       | **unchanged**                |

PR description: **zero moves, no emit**.

---

## 5. `rest_travel` (later class — not this PR)

KEI menu still stamps `rest_travel` with `applied=false` / `in_model=false` (“no current-path fact”). Neutral sites already share `neutral_site` → HFA=0. Long-haul coefficients are **forbidden** here; they remain Chapter 3 Class 3 for a later authorized pass after W1 grades.

---

## 6. Gates (frozen artifacts)

| Gate               | Expectation                                            |
| ------------------ | ------------------------------------------------------ |
| OSU #1             | power SoT unchanged                                    |
| BALL@OSU WP ≥ 0.90 | live project-game gate in tests                        |
| Membership         | only ORE↔MISS / ND↔TEX (Ch2)                           |
| Utah               | 6.2% untouched                                         |
| No team `if`       | confirmation is data-driven JSON, not compose branches |

---

## Done

Join is live. Stop until Sat 9/5 harness step 4. Fit is still not next.
