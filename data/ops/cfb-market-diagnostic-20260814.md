# CFB Market Diagnostic (pure vs open/close — no KEI)

**Date:** 2026-08-14  
**Branch:** `feat/cfb-p3d-market-diagnostic` → `deploy-vercel` (stacked on #233–#238)  
**Diagnostic id:** `cfb-market-diagnostic-v0.14.1-20260814`  
**Engine fair:** still `cfb-season-engine-v0.14-efficiency-backbone` (not blended)  
**Doctrine:** Model stays pure research fair. `used_in_spread` stays **false**. No KEI. No Edge tags. No “bet this.” Report only.

Script: `python scripts/cfb/run_market_diagnostic.py`  
Tables: `data/ops/cfb-market-diagnostic-20260814.json`

---

## Bias one-liner

**Cold / short-favorite.** Mean error vs close is **+2.04** overall and **+4.13** in Week 0–1: the program-prior fair is systematically *less home/favorite* than the market. Same bias vs open (+2.11). Not a hot dog-fader. Not an HFA sign error.

Hist harness is **not** the live 2026 tanh path. Do not read these MAE numbers as v0.14 project-game skill.

---

## A. Historical (2020–25, leakage-safe)

Close = last owned lake snap strictly before kickoff (**not lock**). Open = first owned snap. Fair = program EPA prior (W0–1 100% prior; W2+ blends entering-week EPA with `feature_week < W`). No 2026 roster on hist games.

### vs close and vs open

| Window | n close | vs close mean / MAE / med\|err\| | vs open MAE | ATS | CLV-side rate (n) |
| --- | ---: | ---: | ---: | ---: | ---: |
| **W0–1** | 439 | **+4.13 / 8.36 / 6.53** | 8.08 | **47.7%** | 49.3% (280) |
| W2–4 | 763 | +4.41 / **10.36** / 8.31 | 10.31 | 51.0% | 49.2% (539) |
| W5–9 | 1,416 | +1.18 / 6.54 / 5.16 | 6.57 | 52.1% | 54.6% (959) |
| W10+ | 1,539 | +1.07 / 6.66 / 5.22 | 6.59 | 48.9% | 49.3% (832) |
| Overall | 4,157 | +2.04 / 7.48 / 5.69 | 7.42 | 50.3% | 51.2% (2,610) |

CLV-side = model sat on the side open→close moved (\|move\| ≥ 0.25). Coin-flip. Thin-move games excluded. Not lock CLV. Not PnL.

σ slice: **skipped** — hist walk-forward rows do not store model σ.

### \|close\| buckets

| Bucket | n | mean err | MAE | ATS | CLV-side |
| --- | ---: | ---: | ---: | ---: | ---: |
| pick’em \|c\|<3 | 568 | −0.76 | **2.22** | 49.5% | 74.0% |
| 3–7 | 1,174 | −0.18 | **3.21** | 52.4% | 59.3% |
| 7–14 | 1,184 | +0.10 | 6.48 | 48.8% | 48.0% |
| **14+** | 1,231 | **+7.31** | **14.94** | 50.1% | **36.7%** |

Mid-range lines are usable as a *scale* check. Blowouts are where the prior is theater vs market (too short). ATS still coin even when MAE is small — we are not beating closes.

### Home / favorite

| Slice | n | mean err | MAE | ATS |
| --- | ---: | ---: | ---: | ---: |
| Home favorite | 2,558 | **+7.61** | 7.81 | 50.4% |
| Home dog | 1,599 | **−6.87** | 6.96 | 50.0% |

Both signs say the same thing: **short the favorite** (not “too much HFA”). An HFA retune would not fix this.

### Conference tier (2026 map, labeled approximate)

| Tier | n | mean err | MAE | ATS |
| --- | ---: | ---: | ---: | ---: |
| P4–P4 | 1,813 | +0.86 | 6.62 | 50.0% |
| G5–G5 | 983 | +0.51 | **6.03** | 50.0% |
| **P4–G5** | 451 | **+10.04** | **14.20** | 49.2% |
| Indep mix | 807 | +2.16 | 7.48 | 51.6% |

Error concentrates in **Week 0–1 / Week 2–4** and **P4 vs G5 cupcakes / \|close\|≥14**. G5–G5 is not the problem. High-σ QB: not measurable on hist rows.

---

## B. 2026 Week 0–2 (research, no market)

Official FBS–FBS slate: **96** games. Warehouse `closing_lines` has **zero 2026 rows**. Odds lake `snapshots-2026.parquet` is **9 futures snaps** for MISS–LSU on 2026-11-21 (captured 2025-12-01) — not Week 0–2.

**n_with_market = 0.** Market column is null on purpose. Not invented.

| Matchup | Wk | Model | σ | Market | Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
| UNC @ TCU (n) | 0 | −14.4 | 18.6 | — | — |
| SJSU @ USC | 0 | −21.7 | 18.5 | — | — |
| NCSU @ UVA | 0 | −5.1 | 18.4 | — | — |
| HAW @ STAN | 0 | +6.1 | 18.5 | — | — |
| NMSU @ FSU | 0 | −12.6 | 18.6 | — | — |
| MEM @ UNLV | 0 | −4.6 | 21.1 | — | — |
| BALL @ OSU | 1 | −24.5 | 24.7 | — | — |
| UTEP @ OU | 1 | −21.8 | 26.0 | — | — |
| UAB @ ILL | 1 | −16.8 | 24.6 | — | — |
| TOL @ MSU | 1 | −4.0 | 21.9 | — | — |

Research only. No Edge/Tag. Open-QB / early-week σ stays wide (18–26). Scale still compressed (no −35).

---

## C. Answers

1. **Still cold vs close?** Yes. +4.1 W0–1, +2.0 overall. Underdog-heavy / short-favorite.
2. **Blowouts after tanh?** Hist path has **no tanh**. Live 2026 tanh already capped W0–2 max \|spread\| at 23.6. Hist \|close\|≥14 MAE 14.9 is the *prior* being short, not a live −35 return.
3. **Where does error concentrate?** Week 0–4 and P4–G5 / 14+ favorites. Not G5–G5. QB-σ unmeasured on hist.
4. **Single next lever:** **Accept pure model as research-only through Week 3.**  
   HFA retune: no. QB σ: no data. Open-line prior: highest-value *later build*, but **we have no 2026 Week 0–2 opens to blend against**. Designing KEI now would be rank=market theater.

---

## D. Before any market-blend KEI layer

Required, not optional:

1. Ingest **2026 open/consensus** into the warehouse (Week 0–2 is empty today).
2. Keep the blend **labeled** (`source=open_line_prior`) — never silent rank=market.
3. Holdout that is **not** this diagnostic file. Close ≠ lock until densify is honest.
4. Specify the knob the hist slices demand: **favorite magnitude**, especially P4–G5, not HFA.
5. `used_in_spread` stays false until a later gate. No PLAY/LEAN. No Edge Board CFB population.

---

## Safety

- Status 200 may expose `market_diagnostic` as read-only docs (`used_in_spread=false`, `kei=false`, `blend=false`).
- Fair line unchanged. No KEI column.
- Engine version not bumped (diagnostic-only).
