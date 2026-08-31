# CFB Chapter 2 Phase 2A — efficiency pack (DISCOVERY ONLY)

**Stamp:** `cfb-season-engine-v0.15-power-sot` · snapshot `as_of=2026-08-04`  
**Brief:** `docs/CFB_CH2_EFF_PACK_BRIEF.md`  
**Base:** after #352 (1E low-sample blend)  
**This PR:** **no** writes to efficiency JSON, packager, compose weights, `MATCHUP_RESPONSE`, QB path, or KEI.

---

## Outline (where the four numbers come from)

```text
public final-2025 SP+ (cfbupdate / ESPN)
        │
        ▼
scripts/cfb/package_efficiency_2025_carry.py
  fetch_sp_plus_public / optional CFBD :191–272
  z_off = (sp_offense − μ) / σ                    :291
  z_def = (μ_def − sp_defense) / σ_def            :292  (invert so higher=better)
  off_eff = clamp(50 + 18*z_off, 5, 95)           :187–188, :302
  def_eff = clamp(50 + 18*z_def, 5, 95)           :303
        │
        ▼
…/data/cfb_efficiency_snapshot_2025_carry_2026.json
  prior_year=2025 · carry_to_season=2026 · fidelity=approximate
  source=packaged_sp_plus_final_2025 · pbp=not_used
        │
        ▼
efficiency.build_efficiency_profile(:75–156)
  load snapshot row → EfficiencyProfile
  optional in_season_update deltas (none present for W0)
        │
        ▼
loaders._team_state_from_payload(:168–172)
        │
        ▼
team_projection.compose_team_projection(:104–142)
  WEIGHT_OFF_EFF=0.34 · EFF_OFF_INDEX_BLEND=0.12
```

**Not on the compose path:** warehouse PBP opponent-adj (`cfb_warehouse/efficiency_adj.py` + garbage weights). That feeds packaged `research_prior` only (`team_projection.py:717–718` — “Does not change spread / WP / KEI”).

---

## Greps (locked)

| Needle                       | Hit                                                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `off_eff` / `def_eff` values | `cfb_efficiency_snapshot_2025_carry_2026.json` team rows                                                           |
| Packager                     | `scripts/cfb/package_efficiency_2025_carry.py`                                                                     |
| Loader                       | `efficiency.py:75–156`, `loaders.py:168–172`                                                                       |
| Compose use                  | `team_projection.py:104–142`, `priors.py:187`, `:215`                                                              |
| Garbage-time                 | **warehouse only** (`cfb_warehouse/garbage.py` via `efficiency_adj.py`); **not** in SP+ packager (`pbp: not_used`) |
| In-season Δ                  | `in_season_update.py` — no `data/ops/cfb_inseason_state/state.json` in tree → W0 = pure pack                       |

---

## Required four-team eff table

| team     |   off_eff | def_eff | source year(s)                                                      | opponent-adjusted?                                 | sample (plays/drives)                                                                        | known shock (coordinator/portal)                                                                                                                                                                                       |
| -------- | --------: | ------: | ------------------------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **UNC**  | **24.92** |   53.13 | **2025 only** (SP+ offense #124 / defense #59; overall #92, −6.8)   | **Yes** — SP+ is opponent-adjusted by construction | **Not stored.** Season-long 2025 SP+ rating, not PBP play/drive counts. Pack `pbp=not_used`. | Pack coaching = `default_returning` placeholder (not curated). Roster: portal QB **Billy Edwards Jr.** (16 att), `open_competition`; portal_in=4. **off_eff itself ignores portal/HC** — frozen 2025 SP+ offense 17.2. |
| **TCU**  | **64.74** |   56.29 | **2025 only** (SP+ offense #29 / defense #50; overall #36, +8.5)    | **Yes**                                            | Same — full-season SP+, no play sample in pack                                               | Coaching placeholder returning. QB **Jaden Craig** incumbent 338 att (QB path, not eff). portal_in=3. Eff = frozen 2025 SP+ offense 33.1.                                                                              |
| **HAW**  | **50.21** |   47.78 | **2025 only** (SP+ offense #66 / defense #69; overall #67, +1.7)    | **Yes**                                            | Same                                                                                         | Coaching placeholder. QB **Micah Alejado** incumbent 430 att. portal_in=2. Eff ≈ league mean (z_off ≈ 0.01).                                                                                                           |
| **STAN** | **28.18** |   44.37 | **2025 only** (SP+ offense #117 / defense #80; overall #112, −12.0) | **Yes**                                            | Same                                                                                         | Coaching placeholder returning. QB pack: **Charlie Mirer** `open_competition` (3 att). portal_in=3. **off_eff ignores 2026 QB/roster** — frozen 2025 SP+ offense 18.5.                                                 |

### Z-score check (pack normalization μ_off=27.2147 σ=7.1878; μ_def=26.486 σ=7.3995)

| team | sp_offense |  z_off | → off_eff | sp_defense |  z_def | → def_eff |
| ---- | ---------: | -----: | --------: | ---------: | -----: | --------: |
| UNC  |       17.2 | −1.393 | **24.92** |       25.2 | +0.174 |     53.13 |
| TCU  |       33.1 | +0.819 | **64.74** |       23.9 | +0.349 |     56.29 |
| HAW  |       27.3 | +0.012 | **50.21** |       27.4 | −0.124 |     47.78 |
| STAN |       18.5 | −1.212 | **28.18** |       28.8 | −0.313 |     44.37 |

Exact match to live compose inputs from Phase 1A audit.

---

## Verdict: frozen 2025 corpses or live 2026?

**STAN 28.18 and UNC 24.92 are last-year collapsed offenses with no 2026 update.**

Evidence:

1. Snapshot meta: `prior_season=2025`, `carry_to_season=2026`, `as_of=2026-08-04`, notes: _“Preseason 2026 carry — no 2026 games yet.”_ / _“Do not treat as live in-season SP+ updates.”_
2. Every row: `prior_year=2025`, `source=packaged_sp_plus_final_2025`, `fidelity=approximate`.
3. No in-season state file → `apply_efficiency_deltas` is a no-op.
4. Warehouse PBP opponent-adj + garbage-time **exists** but is **not** the compose `off_eff` SoT (`research_prior` only).
5. 2026 roster/QB/portal shocks update **other** layers; they do **not** rematerialize `off_eff`/`def_eff`.

TCU **64.74** and HAW **50.21** are the same frozen-2025 carry (strong / average), not live 2026 EPA.

---

## Garbage-time / opponent adjustment (explicit)

| Question                                 | Answer for compose `off_eff`/`def_eff`                                                                                                  |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Opponent-adjusted?                       | **Yes** — Bill Connelly SP+ offense/defense ratings.                                                                                    |
| Garbage-time filtered in our packager?   | **No.** Packager never reads PBP. SP+’s own methodology may downweight garbage; we do not re-apply `cfb_warehouse.garbage.weight_play`. |
| Own PBP adj used in project-game scores? | **No.**                                                                                                                                 |

---

## Why these four numbers still polarize after QB work

From Phase 1A leave-one-out (unchanged by 1C–1E on the eff axis):

- **STAN** scoring prior is dragged by **off_eff 28.18** (ablate → 50 lifts STAN pts ~+4.7). HAW off_eff ≈ 50 → eff is **not** Hawaii’s lever.
- **UNC** off_eff 24.92 matched the board (~15 scored); **TCU** off_eff 64.74 is part of the inflated home prior (~+4.1 pts vs avg), twin of the STAN corpse on the other side of the ledger.

Remaining HAW@STAN wrong-side after 1E is therefore still **partly an efficiency-carry problem on Stanford**, not a Hawaii SP+ miss.

---

## Recommendation

**rebuild eff source**

Not leave it (STAN/UNC are explicitly stale 2025 corpses feeding Week 0/1 compose).  
Not Chapter 3 situation only (situation/QB already shipped 1C–1E; residual polarity is the eff axis on STAN vs HAW and the TCU twin).

Fit PR (operator-gated, separate): global rematerialize or shrink/blend of prior-year SP+ carry toward 2026 identity / warehouse season-final adj — **no** `if team == STAN|HAW|UNC|TCU`, **no** `MATCHUP_RESPONSE=1.00`, **no** QB revert.
