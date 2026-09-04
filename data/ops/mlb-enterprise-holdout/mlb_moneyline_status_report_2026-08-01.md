# MLB Moneyline Status Report — 2026-08-01

**Audience:** ops / product / research  
**Branches:** web production `deploy-vercel` · model research on feature branches  
**Odds densify:** not run (credit floor)  
**Unused holdout:** frozen `2026-07-18 → 2026-08-10` — train-excluded; stake OFF  

---

## 1. Edgeboard product status (shipped)

| Item | Status |
|------|--------|
| Market | **Moneyline** (Odds `h2h,totals`) — not run line / spread |
| Columns | Best Moneyline · Best O/U · Our Moneyline · Our O/U |
| Edge | Model home win prob − book no-vig home, in **percentage points** |
| ML tags | **LEAN ≥ 1.5pp · PLAY ≥ 3.0pp** |
| O/U tags | Still **run-point** LEAN ≥ 1.0 · PLAY ≥ 2.5 (not probability %) |
| Footer copy | Live on www: “ML PASS / LEAN (≥1.5pp) / PLAY (≥3.0pp)” |
| PR | [#61](https://github.com/kosedge/kosedge/pull/61) merged → `deploy-vercel` (`cc78bd34`) |
| Live | Production deploy completed; `/edge-board/mlb` serves ML Americans + 1.5/3.0pp footer |
| Prior branch | `mlb-edgeboard-moneyline` (unmerged PR #47 era) was cherry-picked + threshold update |

**Note:** Public `/api/edge-board/mlb/today` returns `Unauthorized` without session — board page still hydrates via server path / fallback. Smoke used HTML/RSC payload on `www.kosedge.com/edge-board/mlb`.

---

## 2. Model production stance

| Knob | Production |
|------|------------|
| Stack | **S0** — HFA 1.025, matchup ON, wind-dir ON, ERA/WHIP quality |
| Stuff proxy / lineup timing | OFF |
| Pitch matchup / true arsenal (team-family) | OFF (`MLB_PITCH_MATCHUP_ENABLED=false`) |
| Batter-level arsenal | **OFF** — densify graded **no-ship** (`MLB_PITCH_MATCHUP_BATTER_LEVEL=false`) — see §5 |
| Optional ML head | Next research path (PA-mul graveyard closed) |

---

## 3. Ablation graveyard (intersection densify, n≈476)

Fixed closing-line intersection unless noted. Leakage **0** on all densify ablations below.

| Trial | Inter ML CLV | Inter RL CLV | Inter Tot CLV | WF Brier | Notes | Ship? |
|-------|-------------:|-------------:|--------------:|---------:|-------|:-----:|
| Pre-HFA subscription (confounded) | +0.023 | +0.230 | +0.332 | 0.252 | Sample confound | — |
| HFA 1.035 (PR #48) | +0.007 | +0.112 | +0.093 | 0.251 | Leakage 11 | no |
| **HFA 1.025** (prod) | +0.007 / densify ~+0.004 | +0.025–0.075 | ~+0.002 | ~0.250 | Winner vs HFA-off | **yes (HFA)** |
| HFA off | +0.006 | +0.047 | +0.091 | 0.249 | Worse CLV | no |
| S1 matchup OFF | +0.0045 | +0.051 | +0.002 | 0.250 | No CLV unlock | no |
| S2 + wind-dir OFF | +0.0039 | **0** | +0.002 | 0.250 | RL torched | no |
| S3 K-BB quality | +0.0043 | +0.038 | +0.002 | 0.250 | No unlock | no |
| T1 FIP proxy | +0.0042 | +0.038 | +0.004 | 0.250 | No unlock | no |
| T2 xFIP proxy | +0.0043 | +0.038 | +0.002 | 0.250 | No unlock | no |
| B1 bullpen role | +0.0040 | +0.038 | +0.002 | 0.249 | No unlock | no |
| T3 stuff_proxy | +0.0041 | +0.051 | +0.002 | 0.251 | No unlock | no |
| L1 lineup timing sharp | +0.0039 | +0.013 | +0.002 | 0.250 | No unlock | no |
| H1 stamp −3h | +0.0037 | +0.025 | +0.002 | 0.250 | Late-info densify n=0 | no |
| H2 stamp −1h | +0.0036 | **0** | +0.006 | 0.249 | RL→0 | no |
| M1 stuff-shape pitch (BOM bug) | +0.0044 | +0.063 | +0.002 | 0.250 | Contaminated | no |
| W1 park-rel totals wind | +0.0039 | +0.025 | +0.004 | 0.250 | MAE worse | no |
| **M1t true arsenal × team-family** | **+0.0039** | **0** | +0.002 | 0.250 | ΔML +0.00009 vs M0; RL dead | **no** |
| **M1b batter-level lineup contact** | **+0.00364** | +0.013 | +0.002 | 0.251 | ΔML −0.00019 vs M0; leak 0 | **no** |

Detail artifacts: `stack_ablation_*`, `sp_talent_v2_*`, `statcast_stuff_*`, `lineup_nowcast_timing_*`, `late_info_stamp_*`, `pitch_matchup_*`, `totals_park_wind_*`, `true_arsenal_*`, `batter_level_arsenal_*`, `live_late_info_clv_*` under this folder.

---

## 4. Current densify grade (S0 / honest bar)

| Metric | Current | Gate | Pass? |
|--------|--------:|------|:-----:|
| Intersection ML CLV | **~+0.004** (n=476) | ≥ +0.010 (stretch +0.015) | **NO** |
| Prod full-n ML CLV | ~+0.005–0.007 | — | weak |
| WF Brier | **~0.2496–0.251** | ≤ 0.24 | **NO** |
| ECE | **0.017–0.027** | ≤ 0.06 | YES |
| Leakage | **0** | 0 | YES |
| Totals MAE | **~3.47–3.52** | improve vs ~3.3 prior | soft |
| RL CLV | **+0.01–0.06** (S0); 0 when torched | do not torch | hold on S0 |

---

## 5. Batter-level arsenal track — **no-ship**

**Hypothesis:** Team-family contact was too coarse; lineup-ID batter contact × pitcher pitch-type mix could move ML without killing RL.

**Graded:** Railway force-resim densify task `b52bf4c4-bd7c-42d7-ae80-3bbfa5f41c3c` (M0/M1/M1b), window `2026-05-20→2026-07-17`, `max_games=1200`, no Odds densify. PR [#63](https://github.com/kosedge/kosedge/pull/63) wiring stays OFF.

| Config | Inter ML | Inter RL | Inter Tot | WF Brier | ECE | Leak | Sim |
|--------|---------:|---------:|----------:|---------:|----:|-----:|----:|
| M0 | +0.00383 | +0.051 | +0.004 | 0.25047 | 0.0233 | 0 | 628 |
| M1t | +0.00392 | 0 | +0.002 | 0.24997 | 0.0229 | 0 | 628 |
| M1b | **+0.00364** | +0.013 | +0.002 | 0.25131 | 0.0238 | 0 | 628 |

**Decision:** keep `MLB_PITCH_MATCHUP_ENABLED` / `MLB_PITCH_MATCHUP_BATTER_LEVEL` **false**. M1b fails +0.010 gate and is slightly worse than M0. **Stop PA-mul research**; pivot to architecture (see §8).

Detail: `batter_level_arsenal_2026-08-01.md` + `.json`.

---

## 6. Unused-holdout / stake gates

| Item | Result |
|------|--------|
| Train exclusion | Enforced |
| Eval n (walkforward unused) | **51** ≪ 120 |
| Stake marketing | **OFF** |
| Props PLAY stake | **OFF** / `research_only` |

Do **not** market “proven +EV” or open stake flags. See `unused_holdout_stake_verdict_2026-08-01.md`.

---

## 7. Provable profitability — honest verdict

**We are not there.**

- Intersection ML CLV stuck ~**+0.004** after a full graveyard of levers — including **batter-level M1b (+0.00364, no-ship)**.  
- Brier fails the 0.24 sharpness gate (~0.250–0.251).  
- Prior +0.023 CLV was **sample-confounded** — do not cite it for subscription.  
- Edgeboard correctly *displays* ML edge in prob points with tighter tags; that is a **product** win, not a model edge win.  
- PA-mul / Statcast contact research is exhausted for subscription CLV.  
- Subscription / stake marketing remains **no-go** until unused-holdout + CLV/Brier clear.

**Blocking:** model sharpness vs close (architecture), not UI.

---

## 8. Ranked “what we can still do” (EV vs sunk-cost traps)

| Rank | Move | Expected value | Trap risk |
|:----:|------|----------------|-----------|
| 1 | **Architecture change** — optional calibrated ML head / market-prior blend with frozen holdout | Medium–High if designed with leakage discipline | High if it becomes “fit the close” |
| 2 | **Live ≤3h late-info CLV** once lake has confirms (infra ready; n=0 today) | Medium for ops measurement | Low sunk cost — already wired |
| 3 | Totals park×weather with CV MAE (not as ML lever) | Low–Medium for totals product | High if sold as ML fix |
| 4 | More quality / Statcast PA muls (incl. batter-level) | **Low** — graveyard closed (M1b no-ship) | **Sunk-cost trap — stop** |
| 5 | Odds densify for sharper closes | Measurement only | Credits; does not create edge |

---

## 9. Letter grades

| Area | Grade | Notes |
|------|:-----:|-------|
| Edgeboard ML product | **B+** | Moneyline live; tags 1.5/3.0pp; labels correct |
| Moneyline sharpness (Brier) | **D+** | ~0.25 vs ≤0.24 |
| Moneyline CLV | **D** | ~+0.004 intersection |
| Calibration (ECE) | **B** | Clean |
| Leakage hygiene | **A** | 0 |
| Totals / RL research | **C / C-** | Not subscription drivers |
| Stake / subscription readiness | **D / no-go** | Fail CLV + Brier + holdout n |

---

## 10. Top 3 remaining moves

1. Design a **market-aware ML head** (or stop mul research) with unused holdout frozen — batter-level densify **failed** the ship gate.  
2. Grow live ≤3h late-info lake and grade when n>0.  
3. Do **not** open stake marketing; do **not** flip pitch-matchup / batter-level flags.

Companion: `../mlb-model-enterprise-grade-report.md` (refreshed same day).
