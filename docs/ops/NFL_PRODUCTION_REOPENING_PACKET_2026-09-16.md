# NFL production reopening packet — 2026-09-16

**Read this file.** Machine twin: [`data/ops/nfl-reopening-packet-20260916/summary.json`](../../data/ops/nfl-reopening-packet-20260916/summary.json).

| Field                        | Value                                                     |
| ---------------------------- | --------------------------------------------------------- |
| Recommendation               | **HOLD public / NO CLEAR**                                |
| Coming soon / public flags   | **ON / dark** (`NFL_EDGE_BOARD_PUBLIC_ENABLED = false`)   |
| Edge Board / fair / Overview | **not painted**                                           |
| `production_promote`         | `false`                                                   |
| Candidate                    | live SHA `153b6a884a8e` / packaged EPA / overlays **OFF** |
| Tuning                       | **none**                                                  |
| KE #570                      | **out of scope**                                          |
| CFB                          | **separate**                                              |

Alex filings cited, not reinvented (`stage2/nfl-regression-2026-09-15/reopen/` not in this checkout): `CUSTOMER_VIEW_SLATE_W2`, `PREDICTIVE_EVAL_FROZEN_W2`, README / GO_NO_GO / FROZEN_EVAL. Receipts: [`alex_predictive_customer_receipts.json`](../../data/ops/nfl-reopening-packet-20260916/alex_predictive_customer_receipts.json).

**STOP for Ryan.** This packet does not reopen anything.

---

## SYSTEM INTEGRITY — PASS

| Proof                   | Value                                                                              |
| ----------------------- | ---------------------------------------------------------------------------------- |
| ATL@PIT EPA fair spread | **−0.76**                                                                          |
| ATL@PIT W-L (refused)   | **−7.55**                                                                          |
| Δ W-L − EPA             | **−6.79** (material; refuse holds)                                                 |
| Overlay zero            | **yes** — overlays **OFF** (fail-closed; dampened @ `completed_reg=16`)            |
| W-L refuse              | **holds** — post-game 1-0/0-1 is not a candidate input                             |
| Multi-matchup sha       | `3ee913394af5a8a9c5fdee5d880f39b1c8541d8641938952772158b369ed0190` **STILL_VALID** |
| Double-count            | **pass**                                                                           |
| Scoring equation        | **unchanged** (45.3 / HFA 1.05 / ±5 total ±6.5 margin)                             |

---

## PREDICTIVE VALIDATION — PARTIAL (fail-closed)

Alex `PREDICTIVE_EVAL_FROZEN_W2` is **PARTIAL**. W2 has **no settled outcomes and no closing grades**. **Cannot PASS.** This packet does **not** invent W2 grades.

Do not wait for this weekend to score the candidate: a historical/OOS protocol already exists. The same SHA `153b6a884a8e` / packaged EPA / overlays OFF was run on **settled W1 2026 actuals** (n=16). No retune. Unsettled W2 games were not graded.

| Settled historical OOS (W1 only — supporting, not a W2 grade) |   n | Margin MAE | Margin bias | Total MAE | Total bias |
| ------------------------------------------------------------- | --: | ---------: | ----------: | --------: | ---------: |
| Candidate EPA                                                 |  16 |      12.60 |       +0.84 |     13.25 |      −4.49 |
| July-31 previous production                                   |  16 |      12.19 |       +2.20 |     13.51 |      −6.28 |
| W-L (circular — **refused**)                                  |  16 |       7.70 |       +1.86 |     13.44 |      −3.92 |
| Market-implied                                                |  16 |       5.69 |           — |         — |          — |

W1 supporting cannot carry PASS: n=16 < protocol YELLOW/GREEN; floors 9.5 / 10.5 missed; market-relative miss; margin vs July-31 +0.41 worse. Calibration N/A (no WP). Inherited lab Predictive YELLOW / enterprise RED is not a new fit.

Filed research-only historical OOS (not recomputed; not a CLEAR): [`historical-oos/HISTORICAL_OOS_DIAGNOSTIC.md`](../../data/ops/nfl-reopening-packet-20260916/historical-oos/HISTORICAL_OOS_DIAGNOSTIC.md). Candidate SHA `153b6a88`, packaged EPA, overlays OFF. Verdict **`MODEL_SIGNAL_WEAK`**. Pooled 2024–2026 n=586 packaged spread MAE **10.9463** vs market **9.7474** (Δ +1.20, CI excludes 0). Public **HOLD**.

**PARTIAL / fail-closed — cannot PASS.** HOLD public / NO CLEAR. NO-GO CLEAR stands.

---

## CURRENT SLATE SANITY/PROVENANCE — PASS (16/17 fair coverage)

Alex `CUSTOMER_VIEW_SLATE_W2`: **17 rows / 16 unique games**. **Fair coverage 16/17.** The extra row is an **IND@KC duplicate that lacks exact canonical fair**. Overlays **OFF**. Live SHA `153b6a884a8e`. Board NO-GO. Coming soon ON.

| Coverage                                      | Value      |
| --------------------------------------------- | ---------- |
| Rows                                          | 17         |
| Unique games                                  | 16         |
| Fair coverage                                 | **16/17**  |
| Dup without exact canonical fair              | **IND@KC** |
| Alex absurdity flags cited                    | **none**   |
| Supporting live remat absurdities (−37 / ~81) | **none**   |

Supporting live remat market-delta flags (not Alex absurdities; compressed totals are a known residual — do not raise the prior): CAR@ATL, CIN@HOU, CLE@TB, DET@BUF, IND@KC, MIA@SF, MIN@CHI, NO@BAL. Live API `run_id` null on the supporting capture (stamped candidate id in this PR).

**STOP for Ryan.** Coming soon stays ON. No fair numbers, Overview numbers, or Edge Board.
