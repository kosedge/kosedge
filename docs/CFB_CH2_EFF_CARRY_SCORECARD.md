# CFB Chapter 2 Phase 2B — 2025 SP+ carry shrink

**Stamp:** `cfb-season-engine-v0.15-power-sot` + 1C–1E QB path  
**Brief:** `docs/CFB_CH2_EFF_CARRY_BRIEF.md`  
**Pack write:** **none** (this revision = operator canary rewrite + re-read only)

---

## Phase 0 — off_eff table (no edits)

Live universe = packaged final-2025 SP+ carry (`cfb_efficiency_snapshot_2025_carry_2026.json`).

| team | off_eff | def_eff |
| ---- | ------: | ------: |
| OSU  |   76.01 |   95.00 |
| BALL |   15.40 |   30.51 |
| TCU  |   64.74 |   56.29 |
| UNC  |   24.92 |   53.13 |
| HAW  |   50.21 |   47.78 |
| STAN |   28.18 |   44.37 |
| ORE  |   81.02 |   85.97 |
| MISS |   84.02 |   71.86 |
| MIA  |   68.49 |   81.35 |
| IU   |   83.02 |   92.29 |
| TAMU |   77.51 |   74.54 |
| ND   |   82.02 |   74.78 |

**Baseline top-7 set:** `{OSU, ORE, MISS, MIA, IU, TAMU, ND}`  
**Documented near-ties:** ORE 1.5481 / MISS 1.5479 (Δ 0.0002); ND 1.4927 / TEX 1.4897 (Δ 0.003). ND off_eff 82.02 vs TEX ~64.5.

**Blend target:** league **50**. Roster blend rejected (double-count with `WEIGHT_ROSTER_STRENGTH`).

**Baseline games (1E) + W0 finals (corpse test — not Ch3 parking):**

| Game     | 1E KEI / WP              | Final            |
| -------- | ------------------------ | ---------------- |
| UNC@TCU  | −17.68 / 0.90 TCU        | **UNC 15–10**    |
| HAW@STAN | +7.62 HAW / STAN WP 0.34 | **STAN 37–27**   |
| BALL@OSU | −42.05 / 0.98            | (cupcake canary) |

---

## Paper-sim (unchanged numbers) — `eff' = 50 + s*(eff−50)`

|        s |  STAN |   UNC |   TCU |   HAW |   OSU | BALL@OSU WP | TCU margin | HAW@STAN KEI | live top-7 list                  |
| -------: | ----: | ----: | ----: | ----: | ----: | ----------: | ---------: | -----------: | -------------------------------- |
| **0.70** | 34.73 | 32.44 | 60.32 | 50.15 | 68.21 |       0.973 |  **13.70** |        +5.08 | OSU,MISS,ORE,MIA,TAMU,**TEX**,IU |
| **0.80** | 32.54 | 29.94 | 61.79 | 50.17 | 70.81 |       0.977 |  **14.64** |        +5.63 | OSU,MISS,ORE,MIA,TAMU,IU,**TEX** |
| **0.85** | 31.45 | 28.68 | 62.53 | 50.18 | 72.11 |       0.979 |  **15.11** |        +5.90 | OSU,MISS,ORE,MIA,TAMU,IU,**TEX** |

No new sims. No s outside the set.

---

## Operator canary rewrite (2026-08-31)

### Dropped

Exact top-7 **order**. ORE↔MISS and ND↔TEX moving under global shrink is the experiment working on the two tightest pairs — not a ratings failure. Exact order made 2B unsatisfiable inside {0.70, 0.80, 0.85} (report-only: even s=0.98 still swaps ORE/MISS). **Canary bug, not s bug.**

### Kept

OSU #1 · BALL@OSU WP ≥ 0.90 · polarity (STAN/UNC ↑, TCU ↓, TCU margin &lt; 16.48) · forbidden list · s ∈ {0.70, 0.80, 0.85} only.

### New power gate

Membership vs `{OSU, ORE, MISS, MIA, IU, TAMU, ND}` may change **only** via:

- **ORE↔MISS** (order within set), and/or
- **ND↔TEX** (TEX replaces ND).

Any other enter/leave → **BLOCKER**.

Allowed sets: baseline **or** `{OSU, ORE, MISS, MIA, IU, TAMU, TEX}`.

### Rejected forks

| #            | Proposal                           | Why dead                                                                                                                            |
| ------------ | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **1**        | OSU #1 + same seven membership     | Still fails every paper-sim s (TEX in). Relabel does not open the set; allowing TEX is a **different** gate (the near-tie rewrite). |
| **3**        | Leave corpses; Chapter 3 situation | W0 finals already falsified “matchup noise.” Parking STAN 28 / UNC 25 / TCU 65 after those scores turns corpses into doctrine.      |
| **Invent s** | 0.40 / 0.98                        | Forbidden.                                                                                                                          |

**Chosen: path 2** — rewrite canary, then lever under that gate.

---

## Re-read under rewritten gate (existing paper-sim only)

| Gate                                                | 0.70                                                    | 0.80        | 0.85        |
| --------------------------------------------------- | ------------------------------------------------------- | ----------- | ----------- |
| OSU #1                                              | PASS                                                    | PASS        | PASS        |
| BALL@OSU WP ≥ 0.90                                  | PASS                                                    | PASS        | PASS        |
| STAN off_eff > 28.18                                | PASS                                                    | PASS        | PASS        |
| UNC off_eff > 24.92                                 | PASS                                                    | PASS        | PASS        |
| TCU off_eff < 64.74                                 | PASS                                                    | PASS        | PASS        |
| TCU raw margin < 16.48                              | PASS                                                    | PASS        | PASS        |
| HAW ~50                                             | PASS                                                    | PASS        | PASS        |
| Exact top-7 **order**                               | _(dropped)_                                             | _(dropped)_ | _(dropped)_ |
| Membership except near-ties (ORE↔MISS, ND↔TEX only) | **PASS** — set `{…, TEX}` = ND↔TEX only; ORE↔MISS order | **PASS**    | **PASS**    |

Membership diffs at every allowed s: **ND out, TEX in** — documented near-tie only. No third name. IU/TAMU/MIA stay.

**Conclusion:** under the rewritten canary, **s=0.85 alone is eligible** (also 0.70 / 0.80). Prefer **0.85** (weakest pull in the set that still moves STAN/UNC). Coupled early `STRENGTH_NOISE` / year-shock is **not required** by this re-read; reserve it only if a later fit PR fails a kept gate.

---

## Status this PR

| Item                      | Status                                                                  |
| ------------------------- | ----------------------------------------------------------------------- |
| Exact-order BLOCKER       | **Superseded** by operator canary rewrite                               |
| Pack / `EFF_CARRY_SHRINK` | **Still not written**                                                   |
| Invented s                | **No**                                                                  |
| Next fit PR               | **s=0.85 alone** under rewritten canaries; scorecard + pack write there |

### Still not done here

- No write to `cfb_efficiency_snapshot_2025_carry_2026.json`
- No `EFF_CARRY_SHRINK` in `priors.py` / `efficiency.py`
- No KEI re-emit
- No `MATCHUP_RESPONSE` / `WEIGHT_OFF_EFF` / team if / QB revert / PBP SoT swap / roster blend

---

## Forbidden check

No `if team == Stanford/UNC/Hawaii/TCU`. No `MATCHUP_RESPONSE=1.00`. No 1C/1D/1E revert. No warehouse PBP as live KEI SoT. No Utah / NFL/CBB/MLB. No invented shrink outside {0.70, 0.80, 0.85}.
