# CFB Chapter 3 — situation Phase 0 audit

**Phase:** Discovery. No pack write. No KEI emit.  
**Stamp frozen:** `cfb-season-engine-v0.15-power-sot` + 1C–1E + `EFF_CARRY_SHRINK=0.85`  
**Audit as_of:** `2026-08-31` (before W1 finals)  
**Brief:** [`docs/CFB_CH3_SITUATION_BRIEF.md`](./CFB_CH3_SITUATION_BRIEF.md)

W0 may **motivate**. Week 1 is **holdout** — predictions below are signed **before** W1 finals and must not be rewritten from W1 results inside Phase 0.

---

## Cross-cutting (compose hygiene)

| Item                      | Finding                                                                                                                 |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Team-name `if` in compose | **None** in `compose_team_projection` / `efficiency.py` for STAN/UNC/HAW/TCU                                            |
| `EFF_CARRY_SHRINK`        | `priors.py` = **0.85**; stamped on efficiency snapshot `carry_shrink=0.85`                                              |
| `MATCHUP_RESPONSE`        | `priors.py` = **1.40** (week-softened W1–W4); already on spine — not a Ch3 invent                                       |
| Power SoT                 | `cfb_power_sot_2026.json` · `engine_version=cfb-season-engine-v0.15-power-sot` · `power_as_of=2026-08-31` · `kei=false` |
| KEI pack                  | `cfb_kei_w0_w1_2026.json` · `as_of=2026-08-31` · QB/coaching/HFA logged `in_model` (not restacked)                      |

### W0 residuals (motivation only — from grade store)

| Game               | KEI (home) | Final | `signed_error_kei` | ATS vs KEI |
| ------------------ | ---------- | ----- | ------------------ | ---------- |
| UNC @ TCU (Dublin) | −16.34     | 15–10 | −21.34             | miss       |
| HAW @ STAN         | +5.93      | 27–37 | +15.93             | cover      |
| SJSU @ USC         | −31.61     | 26–42 | −15.61             | miss       |
| NCSU @ UVA         | −4.50      | 8–34  | +21.50             | cover      |
| NMSU @ FSU         | −13.34     | 17–34 | +3.66              | cover      |
| MEM @ UNLV         | +1.54      | 27–21 | −4.46              | miss       |

These are **not** fit targets. They are why the four classes exist.

---

## Class 1 — Year-1 / interim HC

### Where it lives

- `services/model-service/src/services/cfb_season_engine/coaching_continuity.py`
  - Booleans: `new_hc` / `new_oc` / `new_dc`
  - Curated map `CURATED_STAFF` (~10 teams); else placeholder “all returning”
- Wired into compose via loaders → `compose_team_projection` notes (`coaching_new_hc`, …)
- Week-decayed point penalties into `expected_team_points`

### What it already moves

- Offense/defense **index multipliers** for new HC (e.g. `NEW_HC_OFF_INDEX=0.965`)
- Week-decayed **scoring penalties** (W1-scale HC offense penalty `NEW_HC_OFFENSE_PENALTY=1.35`)
- Early-season **uncertainty boost**
- KEI driver menu: coaching logged `in_model=true`, not restacked

### What it does not move

- **Interim** HC (no symbol / no fidelity)
- Continuous **tenure** (years as HC) — only binary new vs returning
- Live coaching DB (`db_coaching_changes` still not wired)

### Signed prediction (before W1 finals)

**P1 — 2026-08-31:** Through Week 2, mean `|signed_error_kei|` on games where either side has curated `new_hc=True` will exceed the mean for games where both sides are all-returning (same `wp_bucket`) by **≥ 1.5 pts**.  
If not, the HC lever is too thin/curated to be Chapter 3’s global situation lever — do **not** invent tenure coefficients tonight.

---

## Class 2 — Portal / new starting QB (1C–1E)

### Where it lives (one path — do not fork)

1. Packager `scripts/cfb/package_real_roster_2026.py` — heuristic depth, QB1 pick, `classify_qb`, **1D** attempt talent, **1E** low-sample blend → `cfb_real_roster_snapshot_2026.json`
2. Optional overrides `qb_situation_overrides.py` + JSON (named programs only as data, not compose `if team ==`)
3. Runtime `qb_situation.py` — class multipliers + **1C** soft ceiling
4. Compose weights `WEIGHT_QB_SITUATION` / `QB_INDEX_BLEND` in `team_projection.py`

### Does 1C–1E consume W1 depth charts?

- **Offline:** heuristic ESPN roster depth (snapshot notes: camp battles unresolved; official depth charts still listed as a gap).
- **Runtime compose:** **no** re-read of `depth[]` / playing-time shares — only packaged `qb` / roster / position groups.

### What it already moves

- Single `qb_situation_index` into offense compose → power / project-game / KEI-in-model
- Class mults (incumbent / portal / open_competition / true_freshman) under 1C ceiling

### What it does not move

- Live Week 1 official depth or snap shares
- A second QB path (forbidden)

### Signed prediction (before W1 finals)

**P2 — 2026-08-31:** Through Week 2, mean `signed_error_kei` for games featuring a **portal-class QB1** (packaged class) will stay within **±2.0 pts** of the mean for **incumbent-class QB1** games in the same `wp_bucket`.  
If the gap is larger, the missing surface is **depth/playing-time** (not on the path) — document a join; **do not** fork 1C–1E.

---

## Class 3 — Neutral + long-haul

### Where it lives

- Slate: `cfb-official-slate-2026.json` field `neutral_site` (+ `venue` display)
  - W0 Dublin: UNC@TCU · `neutral_site=true` · `venue=Aviva Stadium` · final 15–10
  - W1 neutrals (same flag): BAY@AUB (Mercedes-Benz), LOU@MISS (Nissan), WIS@ND (Lambeau)
- Load: `official_schedule.games_from_blob` → `neutral_site=bool(...)`
- HFA: `home_field.resolve_hfa_points` — if `neutral_site` → **`hfa_points=0.0`**, `reason=neutral_site`
- Project Game: bare page defaults UNC@TCU Week 0 + neutral from slate (#357)
- KEI menu: `rest_travel` always `applied=false`, `in_model=false` (“no current-path fact”)

### What it already moves

- **HFA → 0** for every `neutral_site=true` game (Dublin and W1 neutrals share one flag)

### What it does not move

- Long-haul / travel / rest points (absent from stack)
- Venue string is metadata, not a travel delta

### Signed prediction (before W1 finals)

**P3 — 2026-08-31:** W1 neutral games will stamp project-game / KEI HFA drivers with `reason=neutral_site` and `hfa_points=0` (same as Dublin). Mean `|signed_error_kei|` on those three W1 neutrals will be **&lt; 12 pts** (below Dublin’s 21.3).  
If W1 domestic neutrals still print Dublin-scale errors, the candidate class is **missing long-haul** — still a **global** travel fact, never `if team == UNC`.

---

## Class 4 — Rebuild-offense group (`off_eff_pre_shrink` ≤ 35)

### Where it lives

- Pack: `cfb_efficiency_snapshot_2025_carry_2026.json` fields `off_eff_pre_shrink` / `off_eff` / `carry_shrink=0.85`
- Apply: `efficiency.apply_eff_carry_shrink` — **global** toward 50

### Group membership (audit as_of 2026-08-31)

Pre-shrink ≤ 35 → **24 unique team codes** (+ `OREST` alias of ORST):

`MASS, NIU, BALL, CHAR, WYO, SHSU, BGSU, OKST, ULM, ORST, KENT, UNC, AKR, WIS, CMU, BUFF, RICE, STAN, GAST, SYR, EMU, NMSU, UTEP, MTSU`

| Focal |   pre | post (s=0.85) | In group? |
| ----- | ----: | ------------: | --------- |
| UNC   | 24.92 |         28.68 | **yes**   |
| STAN  | 28.18 |         31.45 | **yes**   |
| HAW   | 50.21 |         50.18 | **no**    |
| TCU   | 64.74 |         62.53 | **no**    |

### What it already moves

- Uniform corpse regression via **one** global shrink into `off_eff` → compose for every team

### What it does not move

- A post-shrink **group residual** layer
- Team-specific rebuild ifs (none on spine; scorecard forbids STAN/UNC/HAW/TCU ifs)

### Signed prediction (before W1 finals)

**P4 — 2026-08-31:** Through Week 1 (holdout grades, read-only), mean `|signed_error_kei|` for games involving **≥1** rebuild-offense team (`off_eff_pre_shrink≤35`) will exceed games with **neither** side in the group by **≥ 2.0 pts**.  
If not, s=0.85 already absorbed the corpse residual — Chapter 3 must **not** add a rebuild-group knob on top of shrink.

---

## One-line class summaries

| #         | Already moves                                                 | Does not move                                |
| --------- | ------------------------------------------------------------- | -------------------------------------------- |
| 1 HC      | Curated new HC/OC/DC indices + week pts + uncertainty         | Interim / tenure years / live coaching feed  |
| 2 QB      | Single 1C–1E `qb_situation` from packaged ESPN QB1            | Live W1 official depth / playing-time shares |
| 3 Neutral | HFA=0 via shared `neutral_site` (Dublin = W1 neutrals)        | Long-haul / travel / rest                    |
| 4 Rebuild | Global s=0.85 on all low-2025 offenses (UNC/STAN in; HAW out) | Post-shrink group residual; team ifs         |

---

## Lever register (Phase 0 — no fit)

Phase 0 **does not** authorize a coefficient. Candidates for a **later** single global lever (after W1 grades), each with a holdout:

| Candidate                                                   | Would touch                          | Holdout              |
| ----------------------------------------------------------- | ------------------------------------ | -------------------- |
| A. Tenure/interim fidelity on existing coaching path        | `coaching_continuity` only           | W1                   |
| B. Depth/playing-time join into existing QB path (no fork)  | roster depth → `qb_situation` inputs | W1                   |
| C. Long-haul / travel fact into HFA or rest stack           | new current-path fact; shared flag   | W1 neutrals          |
| D. Rebuild-group residual **after** s=0.85 (global, capped) | efficiency compose only              | W1; never team names |

**Tonight:** register only. **Fit PR does not exist** until one of A–D is chosen with caps and W1 holdout, and the grade table speaks.

---

## Blocker trigger

If a proposed “fix” for UNC@TCU and HAW@STAN is only two team flags → stop and write `docs/CFB_CH3_BLOCKER.md`. Same pattern as Utah and 2B-order.

---

## Done criteria (this PR)

- [x] Brief with file paths
- [x] Audit per class + four signed predictions dated before W1 finals
- [x] No pack / no shrink edit / no team `if` / no KEI emit

Published KEI unchanged. Grade store and W1 card read-only.
