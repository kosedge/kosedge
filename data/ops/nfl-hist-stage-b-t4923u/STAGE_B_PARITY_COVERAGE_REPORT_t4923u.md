# t4923u Stage B — parity + coverage report

Labels: **RETRO_FIT** / **DEV_RESEARCH**. CERT=0. NFL NO-GO. Stage C **NOT** authorized.

| pin | value |
|---|---|
| Order | `COS_ORDER_CURSOR_t4923u_STAGE_B_EXEC.md` tip **62ca041c** (supersedes ce807d95) |
| Step 0 selection | `STAGE_B_GAME_SELECTION_t4923u.md` sha256 **ce10ae5f**… (full in sidecar) |
| Selection JSON | `SELECTION_HASH_SEAL.json` **2e338a1e**… |
| Eligible combined | N=55 hash `448946a2a825f82f238bff0aea04a740c7a03c363b17f1e17e4452df0486e915` |
| Rebuild matrix | `RECON_MATRIX.csv` sha256 `cd9af2858e21fac5247a489051f0cc61b9490cb97ffdec9ac41a31a2d224d810` |
| Filed UTC | 2026-10-31T15:16:00Z |
| Alex RO next | **ba1c89f5** |

## Verdict

**PASS_STAGE_B_PARITY_COVERAGE** (reconstruction / as-of / season-handling only).

- W2 14 vs RECON content **708513db**: index 56/56 at \|Δ\|=0 (< 1e-6); 5g EPA/success 140/140 at \|Δ\|=0 (< 1e-9). Tolerances were sealed **before** rebuild; not changed.
- 2017 W7–W8: 28/28 eligible produced; 22/28 complete 27/27; 6/28 retain `MISSING_RECORD` on the bye side at exact `rating_week` (no substitute).
- 2016 REG W8 (season-hardcode check): 13/13 eligible produced; 11/13 complete; 2/13 same bye `MISSING_RECORD` pattern. Builder ran 2016 PBP pin **95eba04e** without the 2017-only path.
- Leakage **PASS**. Index 1ee90fac **PILOT-ONLY** (gate 83646d78).
- No outcomes, no scores, no 2024–25, no touch of 02197f58 / SCORE_RESULTS 2b9f302e.

## 1. Complete-game coverage

27 fields / game (20 efficiency + 7 context), same as t4893u.

| Slice | Source | Eligible | Selection MISSING retained | Complete 27/27 | Partial (bye T2) |
|---|---:|---:|---:|---:|---:|
| 2017 W2 parity | 16 | 14 | 2 (Irma TB/MIA) | 14 | 0 |
| 2017 W7 | 15 | 15 | 0 | 11 | 4 |
| 2017 W8 | 13 | 13 | 0 | 11 | 2 |
| 2016 W8 | 13 | 13 | 0 | 11 | 2 |
| **Total** | **57** | **55** | **2** | **47** | **8** |

Cells: 1485 = 55×27. **DERIVED_PREGAME 1397** (94.0741%). **MISSING_RECORD 88** = 8 games × 11 fields (5 T1 side + 6 T4 diffs). Identity / rest / T5 / opposite-side T1 stay DERIVED.

Partial games (retained; not replaced):

| game_id | bye side | rating_week |
|---|---|---|
| 2017_07_TB_BUF | BUF home | 6 |
| 2017_07_DAL_SF | DAL away | 6 |
| 2017_07_CIN_PIT | CIN away | 6 |
| 2017_07_SEA_NYG | SEA away | 6 |
| 2017_08_HOU_SEA | HOU away | 7 |
| 2017_08_PIT_DET | DET home | 7 |
| 2016_08_ARI_CAR | CAR home | 7 |
| 2016_08_PHI_DAL | DAL home | 7 |

Same fail-closed rule as W3–W6 (cdff0115 lineage): exact `lookup_t2(rating_week)`; no last-played fill.

## 2. Parity findings (tolerances pre-registered)

Locked in Step 0 at 15:10:13Z: index \|Δ\| < 1e-6; 5g EPA/success \|Δ\| < 1e-9.

| Compare | N | Pass | max \|Δ\| | Bar |
|---|---:|---:|---:|---|
| W2 14 index vs 708513db | 56 | 56 | **0** | 1e-6 |
| W2 14 EPA/success/matchup vs 708513db | 140 | 140 | **0** | 1e-9 |
| W7–W8 + 2016 W8 index vs games.csv 4fe1cdd7 (finite cells) | 164 | 164 | < 1e-6 | 1e-6 |

W2 RECON rehashed this run: `708513db885fe362aca9446578154d58e9d8265857ec2385e475323b24f24182` (content hash, **not** filename tip 440314e4).

**cdff0115** cited as pin/lineage only — W3–W6 games are not in this sample; no field compare invented.

## 3. Leakage / point-in-time

| Check | Result |
|---|---|
| T1 consume weeks 1–7 of **that season** only | PASS |
| Target week (W8 / W2) game_ids absent from T1 | PASS |
| Per-target window week ≤ rating_week; all consumed kickoffs < target | PASS |
| Week-gap max(Wk) < min(W{k+1}) for 2016 and 2017 W1–W8 | PASS |
| T2 rolling **per-season** (2016 does not roll into 2017) | PASS |
| Cross-season / 2024–25 / new acquisition | not opened |

Consumed: 2016 W1–W7 = 107 games / 13540 pass-run plays (pin 95eba04e). 2017 W1–W7 = 106 games / 13279 plays (pin 84eacd96). Receipt family **6ee24b44**.

## 4. Season handling (2016 W8)

W2 builder 7e77c57f hardcoded 2017 / week==1 consume / PBP 2017 only. Stage B wrapper parameterized:

- PBP path + pin per season (2016 and 2017 only)
- T1 weeks = 1 .. (max target week − 1) per season
- `matchup_season` written from the row, not `"2017"`
- T1/T2 frames isolated by season (`rolling_5g` groups by team only — concatenating seasons would leak)

**Identity join (not a semantics change):** 2016 restage PBP uses modern `LAC`; games.csv 4fe1cdd7 uses `SD`. Mapped `LAC→SD` in the 2016 plays frame only, same class as W2 `LA→LAR` / `WAS→WSH` / `LV→OAK`. Documented in `T1_TRANSFORM.json`. No T1/T4 formula edit.

Season-hardcode test **PASS**: 2016 W8 matrix rows exist with season=2016, 13 eligible, 11 complete.

## 5. Reusable components

| Component | sha8 / pin | Reuse |
|---|---|---|
| T1–T4 port `t1_from_plays` / `rolling_5g` / `lookup_t2` / T5 / rest_days | builder **7e77c57f** | unchanged; import |
| Selection as-of (games.csv + OOS counts, pandas-free) | seal script this packet | copied transforms |
| games.csv | **4fe1cdd7** | schedule / as-of keys / index |
| OOS | **1ee90fac** PILOT-ONLY 83646d78 | T5 W-L |
| PBP restage 2012–22 | receipt **6ee24b44** | 2016/2017 opened only |
| Sealed RECON W2 | **708513db** | parity target |
| Contract map | **b41f4b43** | field names / T4 signs (RETRO_FIT) |

Not reusable without CLEAR: 2023 (no PBP), 2024–25, SCORE_RESULTS, control tip 02197f58.

## 6. Engineering time (actual)

**0.23 h** wall (15:02–15:16Z). Breakdown in `HOURS_LOG.md`. Far below the ~1 d Stage A assumption because the 5g engine already existed.

## 7. Prohibited / not done

Outcome analysis · scoring · fit/tune · Stage C · Q2 Phase B · merge/deploy/publish · 2024–25 · 02197f58 · SCORE_RESULTS 2b9f302e.

Feature semantics were not changed. Mapping-only identity remap for 2016 SD/LAC is documented; any further semantics question escalates.

NFL NO-GO · CERT=0
