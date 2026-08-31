# CFB Chapter 2 Phase 1D — talent_from_qb_stats volume

**Stamp:** `cfb-season-engine-v0.15-power-sot` + 1C soft ceiling (τ=0.16)  
**Brief:** `docs/CFB_CH2_TALENT_VOLUME_BRIEF.md`  
**Lever:** attempt term only in `scripts/cfb/package_real_roster_2026.py:355–372`

## Phase 0 — live formula (before)

```355:362:scripts/cfb/package_real_roster_2026.py
# WAS:
base = 42 + min(28, attempts/18) + min(12, ypa*1.1) + min(10, tds*0.35) + (2 if portal)
```

`attempts/18` saturated at **504** attempts (cap 28). Pack did **not** persist `pass_td_2025`; TD term / implied TDs recovered from talent identity for the table.

| team                |     att |  ypa | tds~ | talent now |    attempt term | ypa term | td term |
| ------------------- | ------: | ---: | ---: | ---------: | --------------: | -------: | ------: |
| OSU                 |     391 | 9.23 |   29 |  **83.88** |       **21.72** |    10.16 |   10.00 |
| TCU                 |     338 | 8.49 |   25 |  **78.86** |       **18.78** |     9.34 |    8.75 |
| HAW                 | **430** | 7.22 |   24 |  **82.23** |       **23.89** |     7.95 |    8.40 |
| STAN                |       3 | 7.33 |    1 |      50.58 |            0.17 |     8.07 |    0.35 |
| BALL                |       3 | 4.67 |    0 |      49.30 |            0.17 |     5.13 |    0.00 |
| DEL (G5 high-att)   |     512 | 7.19 |   23 |      85.96 | **28.00** (cap) |     7.91 |    8.05 |
| MICH (P4 lower-att) |      82 | 5.95 |    1 |      53.45 |            4.56 |     6.54 |    0.35 |

HAW attempt term **23.9/28** dominates the 82 talent — not P4 efficiency (ypa 7.22).

## Phase 1 — change

```text
min(28, attempts/18)  →  min(22, attempts/22)
```

Saturates at **484** attempts with max attempt term **22** (was 28). YPA / TD / portal terms unchanged. 1C taper unchanged.

Rematerialized `qb_talent` (+ persisted `pass_td_2025`) in:

- `cfb_fbs_team_priors_2026.json`
- `cfb_real_roster_snapshot_2026.json`

## After

| team |                   talent | published qb_index / score |
| ---- | -----------------------: | -------------------------: |
| OSU  |                **79.93** |         **1.3808 / 80.47** |
| HAW  | **77.89** (↓ from 82.23) |         **1.3625 / 79.00** |
| TCU  |                **75.45** |         **1.3594 / 78.75** |

**OSU > HAW > TCU** still.

## Canaries

| Gate                    | Result                                  |
| ----------------------- | --------------------------------------- |
| Top-7 power order       | **FLAT** OSU…ND (no power pack refit)   |
| OSU qb_index > HAW, TCU | PASS                                    |
| HAW talent ↓ vs 82.23   | **77.89** PASS                          |
| TCU margin ≤ 19.01      | **18.73** PASS                          |
| HAW pts ≤ 31.81         | **30.73** PASS                          |
| BALL@OSU cupcake        | KEI **−42.21** · WP **0.98** PASS       |
| HAW@STAN side           | still wrong (**+10.53** KEI) — reported |
| Utah                    | **6.2%** (futures not rewritten) PASS   |

## Forbidden check

No team if. No clamp haircut. No `WEIGHT_QB` / `MATCHUP_RESPONSE`. No 1C τ edit. No power_sot rematerialize.
