# CFB Chapter 2 Phase 1C — qb_situation soft ceiling

**Stamp:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Brief:** `docs/CFB_CH2_QB_SOFT_CEILING_BRIEF.md`  
**Function:** `apply_qb_situation_soft_ceiling` in `qb_situation.py`

## Phase 0 — named function + paper table

```text
raw = talent_index * class_mult * cast_mult
if raw <= KNEE(1.25):  published = raw
else:                  published = KNEE + TAU*(1 - exp(-(raw-KNEE)/TAU))
index = clamp(published, 0.62, 1.55)   # rail only — not flatten-to-1.38
score = 50 + (index-1)*80
```

Constants (`priors.py`): `QB_SITUATION_SOFT_KNEE=1.25`, `QB_SITUATION_SOFT_TAU=0.16`, rail `(0.62, 1.55)`.

| Team | Unclamped raw | Old published |     Soft published |     Score |
| ---- | ------------: | ------------: | -----------------: | --------: |
| OSU  |        1.5771 |   1.38 / 80.4 | **1.3893 / 81.14** |     Sayin |
| HAW  |        1.5024 |   1.38 / 80.4 | **1.3770 / 80.16** |   Alejado |
| TCU  |        1.4806 |   1.38 / 80.4 | **1.3721 / 79.77** |     Craig |
| STAN |        0.8996 |          0.90 |     0.8996 / 41.97 | unchanged |
| BALL |        0.8672 |          0.87 |     0.8672 / 39.37 | unchanged |

**OSU > HAW > TCU** in published index. Sayin ≠ Alejado.

Linear retain from 1.25 (no asymptote) reordered top-7 (TEX↔ND / ORE↔MISS). Exponential taper at τ=0.16 keeps **top-7 flat**.

## Canaries (before → after)

|                            | Before          | After                                        | Gate                          |
| -------------------------- | --------------- | -------------------------------------------- | ----------------------------- |
| OSU qb_index               | 1.38            | **1.3893** (> TCU, > HAW)                    | PASS                          |
| TCU qb_index               | 1.38            | **1.3721**                                   | PASS                          |
| HAW qb_index               | 1.38            | **1.3770**                                   | PASS                          |
| STAN qb_index              | ~0.90           | 0.8996                                       | PASS                          |
| TCU home margin (Dublin)   | 19.19           | **19.01** (≤ 19.19)                          | PASS                          |
| HAW away expected pts      | ~31.8 / 31.06   | **31.00** (≤ 31.81)                          | PASS                          |
| Top-7 power (live compose) | OSU…ND          | **unchanged**                                | PASS                          |
| Power pack refit           | —               | **not done**                                 | PASS                          |
| BALL@OSU KEI               | −42.2 · WP 0.98 | **−42.32 · WP 0.98**                         | PASS (cupcake)                |
| UNC@TCU KEI                | −20.39          | **−20.21**                                   | reported (not forced to −7.5) |
| HAW@STAN side              | wrong           | **still wrong** (kei_spread_home **+10.84**) | reported, not forced          |
| Utah natty%                | 6.2%            | **6.2%** (futures not rewritten)             | PASS                          |
| USF vs OSU E[wins]         | pack untouched  | pack untouched                               | PASS                          |

## What changed

- `qb_situation.py`: `apply_qb_situation_soft_ceiling` + wire into `compute_qb_situation_index` / index overrides
- `priors.py`: named knee / tau; rail raised to **1.55** (safety only — not a 1.20 haircut)
- KEI W0/W1 packs re-emitted (model spreads moved)
- Futures packs **reverted** (Utah stays 6.2)
- Tests: soft-ceiling unit + web KEI expectations

## Forbidden check

No `talent_from_qb_stats` edit. No `WEIGHT_QB` / `MATCHUP_RESPONSE` cut. No team if. No power_sot rematerialize.
