# NFL production reopening packet — 2026-09-16

**Read this file.** Machine twin: [`data/ops/nfl-reopening-packet-20260916/summary.json`](../../data/ops/nfl-reopening-packet-20260916/summary.json).  
Customer-view: [`customer_view_slate.json`](../../data/ops/nfl-reopening-packet-20260916/customer_view_slate.json).  
Predictive: [`predictive_validation.json`](../../data/ops/nfl-reopening-packet-20260916/predictive_validation.json).

| Field | Value |
| --- | --- |
| CLEAR | **NO-GO** |
| Coming soon / public flags | **ON / dark** (`NFL_EDGE_BOARD_PUBLIC_ENABLED = false`) |
| Edge Board / fair / Overview | **not painted** |
| `production_promote` | `false` |
| Candidate | live SHA `153b6a884a8e` / packaged EPA / overlays **OFF** |
| Tuning / ATS fit / coeff change | **none** |
| KE #570 PARTIAL v1 | **out of scope** |
| CFB | **separate** |

**STOP for Ryan CLEAR.** This packet does not reopen anything.

---

## SYSTEM INTEGRITY — PASS

Ryan accepted this gate. Evidence stands; not re-litigated.

| Proof | Value |
| --- | --- |
| ATL@PIT EPA fair spread | **−0.76** |
| ATL@PIT W-L (refused) | **−7.55** |
| Δ W-L − EPA | **−6.79** (material; refuse holds) |
| Multi-matchup integrity sha | `3ee913394af5a8a9c5fdee5d880f39b1c8541d8641938952772158b369ed0190` **STILL_VALID** |
| Double-count | **pass** |
| Overlay zero | **yes** (fail-closed OFF; dampened @ `completed_reg=16`) |
| W-L refuse | **holds** — post-game 1-0/0-1 is not a candidate input |
| Scoring equation | **unchanged** (45.3 / HFA 1.05 / ±5 total ±6.5 margin) |

July-31 stamps are rejected as candidate fair. Live book paint remains a Release question, not an integrity miss.

---

## PREDICTIVE VALIDATION — FAIL

Frozen eval on the **exact** production candidate that generated the 17-game window (SHA `153b6a884a8e` / packaged EPA / overlays OFF). **No tuning, refitting, coefficient changes, feature additions, or market fitting.**

Protocol: `nfl-spread-validation-protocol-v1.0`. Supervised floors from enterprise gates (margin ≤ 9.5, total ≤ 10.5). Calibration **N/A** (candidate remat does not publish WP / Brier).

| Slice | n | Margin MAE | Margin bias | Total MAE | Total bias |
| --- | ---: | ---: | ---: | ---: | ---: |
| Candidate EPA (W1 2026 OOS) | 16 | **12.60** | +0.84 | **13.25** | −4.49 |
| July-31 previous production | 16 | 12.19 | +2.20 | 13.51 | −6.28 |
| W-L (circular — **refused**) | 16 | 7.70 | +1.86 | 13.44 | −3.92 |
| Market-implied (W1 joined books) | 16 | 5.69 | — | — | — |

| Check | Result |
| --- | --- |
| Protocol GREEN (n≥200 + market-relative MAE) | **cannot** — n=16 |
| Protocol YELLOW (n≥100) | **cannot** — n=16 |
| Supervised margin floor ≤9.5 | **miss** (12.60) |
| Supervised total floor ≤10.5 | **miss** (13.25) |
| Margin bias \|ε\|≤2.0 | pass (+0.84) |
| Total bias | −4.49 (compressed totals residual; CHI@CAR 96 known) |
| Market-relative (EPA MAE ≤ market MAE) | **miss** (12.60 vs 5.69) |
| Model vs close MAE (report only) | 8.15 |

**Regression checks**

| Comparator | Margin | Total | Read |
| --- | --- | --- | --- |
| vs July-31 previous production | +0.41 worse | −0.26 better | Margin **regressed**. Total not enough to clear 10.5. |
| vs inherited historical production | hist supervised 7.48 / spread 9.55 | hist 9.20 | W1 OOS does not meet inherited floors. No new fit. |
| vs W-L 7.70 | — | — | **Refuse.** Circular post-game 1-0/0-1. Not a win. |

Inherited frozen baseline (2026-09-04 protocol fill / 2026-07-28 enterprise): Predictive **YELLOW**, Market Edge **GREEN** (confirmatory), Influence **LIMITED**, enterprise overall **RED**. Repair did not retune, so those grades are inherited — they do **not** carry this candidate’s W1 OOS to PASS.

**FAIL reasons (blocks CLEAR):** n=16 thin; margin MAE 12.60 > 9.5; total MAE 13.25 > 10.5; does not beat market-implied 5.69; margin worse than July-31.

---

## CURRENT SLATE SANITY/PROVENANCE — PASS

Internal 17-game customer-view shadow. **Not a public paint.** Coming soon stays ON.

Window = **16 rematted W2** (2026-09-17 / 20 / 21, projection `2026-09-16T14:57Z`, SHA `153b6a884a8e`, packaged EPA, dampened @ 16) **+ 1 W3 ATL@GB**. Canonical W2 is 16. Live API `run_id` is null on every row — stamped `nfl-prod-candidate-153b6a884a8e` for W2. ATL@GB live stamp is **July-31 and is rejected as fair**; filled from the same packaged-EPA / overlays-OFF candidate (`run_id=nfl-prod-candidate-153b6a884a8e-atl-gb-research-fill`, fair −2.27 / 46.07 vs live July-31 −4.59 / 43.16). Odds as-of `2026-09-16T15:07:08Z`. Overlays **OFF**. No −37 / ~81 absurdities.

Flags (do not FAIL): live `run_id` null; ATL@GB is W3; market disagreement on CAR@ATL, CIN@HOU, CLE@TB, DET@BUF, IND@KC, MIA@SF, MIN@CHI, NO@BAL, ATL@GB. Compressed totals are a known residual — do not raise the prior.

| Game | Wk | Market Spread → Fair Spread | Market Total → Fair Total | Projected Score | Edge spr / tot | run_id | input timestamp | overlay |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| DET@BUF | 2 | −4.5 → −2.48 | 54.5 → 45.60 | DET 21.6 @ BUF 24.0 | +2.02 / −8.90 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:29Z | OFF |
| CAR@ATL | 2 | +2.5 → −3.86 | 44.0 → 43.52 | CAR 19.8 @ ATL 23.7 | −6.36 / −0.48 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:29Z | OFF |
| CIN@HOU | 2 | −2.5 → −7.76 | 46.5 → 41.56 | CIN 16.9 @ HOU 24.7 | −5.26 / −4.94 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:29Z | OFF |
| CLE@TB | 2 | −8.5 → −3.47 | 41.5 → 38.56 | CLE 17.5 @ TB 21.0 | +5.03 / −2.94 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:29Z | OFF |
| GB@NYJ | 2 | +3.5 → +2.57 | 44.5 → 41.53 | GB 22.1 @ NYJ 19.5 | −0.93 / −2.97 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:29Z | OFF |
| IND@KC | 2 | −6.5 → −2.43 | 46.5 → 43.25 | IND 20.4 @ KC 22.8 | +4.07 / −3.25 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| JAX@DEN | 2 | −2.5 → −4.62 | 45.5 → 40.54 | JAX 18.0 @ DEN 22.6 | −2.12 / −4.96 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| LV@LAC | 2 | −6.5 → −4.35 | 43.5 → 40.00 | LV 17.8 @ LAC 22.2 | +2.15 / −3.50 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| MIA@SF | 2 | −13.5 → −6.50 | 45.5 → 44.94 | MIA 19.2 @ SF 25.7 | +7.00 / −0.56 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| MIN@CHI | 2 | −5.5 → −3.15 | 48.0 → 38.15 | MIN 17.5 @ CHI 20.6 | +2.35 / −9.85 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| NO@BAL | 2 | −8.5 → −3.57 | 47.5 → 38.77 | NO 17.6 @ BAL 21.2 | +4.93 / −8.73 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| PHI@TEN | 2 | +7.0 → +4.44 | 39.5 → 41.72 | PHI 23.1 @ TEN 18.6 | −2.56 / +2.22 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| PIT@NE | 2 | −5.0 → −4.23 | 41.5 → 42.56 | PIT 19.2 @ NE 23.4 | +0.77 / +1.06 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| SEA@ARI | 2 | +3.5 → +2.35 | 41.0 → 41.22 | SEA 21.8 @ ARI 19.4 | −1.15 / +0.22 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| WSH@DAL | 2 | −4.0 → −4.15 | 50.5 → 46.72 | WSH 21.3 @ DAL 25.4 | −0.15 / −3.78 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| NYG@LAR | 2 | −7.0 → −7.14 | 48.0 → 47.36 | NYG 20.1 @ LAR 27.2 | −0.14 / −0.64 | `nfl-prod-candidate-153b6a884a8e` | 2026-09-16T14:57:30Z | OFF |
| ATL@GB | 3 | −6.5 → −2.27 | 45.5 → 46.07 | ATL 21.9 @ GB 24.2 | +4.23 / +0.57 | `nfl-prod-candidate-153b6a884a8e-atl-gb-research-fill` | live July-31 **rejected**; fill from candidate | OFF |

Alex `stage2/nfl-regression-2026-09-15/reopen/` was not in this checkout. Live remats cited, not reinvented.

**STOP for Ryan CLEAR.** Coming soon stays ON. No fair numbers, Overview numbers, or Edge Board.
