# NFL production reopening packet — 2026-09-16

**Read this file.** Machine twin: [`data/ops/nfl-reopening-packet-20260916/summary.json`](../../data/ops/nfl-reopening-packet-20260916/summary.json).  
**Ryan:** STOP here for CLEAR. This PR does not reopen anything.

| Field | Value |
| --- | --- |
| Recommendation | **CONDITIONAL** |
| Remat + integrity evidence | **GO** (Alex live + #564 sha `3ee91339…` STILL_VALID) |
| Board reopen | **NO-GO** — no Ryan CLEAR |
| `production_promote` | `false` |
| Coming soon / public flags | stay dark (`NFL_EDGE_BOARD_PUBLIC_ENABLED = false`) |
| Edge Board | **not flipped** |
| KE Football R&D (#570 PARTIAL v1) | **out of scope** — frozen; not used as Team Strength |
| CFB | **separate** — do not bless CFB from this packet |
| Overlays | personnel / injury **OFF** (fail-closed; dampened @ `completed_reg=16`) |
| Scoring equation | **unchanged** (prior 45.3 / HFA 1.05 / caps ±5 total ±6.5 margin) |

If Ryan later CLEARs: **fair numbers → overview → Edge Board last**. Totals stay separable from spreads. This packet does **not** authorize that sequence.

Alex `stage2/nfl-regression-2026-09-15/reopen/` (README, GO_NO_GO, INTEGRITY_ATL_PIT_MULTI, FULL_SLATE_SHADOW, PROVENANCE_SANITY, FROZEN_EVAL) was **not in this checkout**. Live remats are **not reinvented**. Receipts: [`alex_live_receipts.json`](../../data/ops/nfl-reopening-packet-20260916/alex_live_receipts.json). Read-only confirm: Railway `/health` `git_sha=153b6a884a8e`; www fair-lines **503**.

---

## Recommendation

**CONDITIONAL** — remat+integrity GO; **board reopen NO-GO**.

Customer boards stay Coming soon until Ryan CLEAR.

---

## Gate 1 — integrity **PASS**

| Proof | Value |
| --- | --- |
| ATL@PIT EPA fair spread | **−0.76** |
| ATL@PIT W-L (refused) | **−7.55** |
| Δ W-L − EPA | **−6.79** (≥0.75 material; refuse holds) |
| Overlay zero | **yes** |
| #564 multi-matchup integrity sha | `3ee913394af5a8a9c5fdee5d880f39b1c8541d8641938952772158b369ed0190` **STILL_VALID** |
| Double-count | **pass** |
| Alex remat+integrity | **GO** |
| Board reopen | **NO-GO** |

Focus set still DET@BUF / CAR@ATL / ATL@PIT / CHI@CAR. Packaged EPA authoritative. Scoring equation not edited.

This PR’s local candidate remat (no Railway write) matches the same ATL@PIT EPA −0.7631 and W-L refuse. July-31 stamps are rejected as candidate inputs. Live book paint is a Release question, not an integrity miss.

---

## Gate 2 — slate shadow **PASS** (17 games)

Alex live W2 remat — **cited, not rerun**:

| Field | Alex receipt |
| --- | --- |
| Dates | 2026-09-17 / 2026-09-20 / 2026-09-21 |
| Status | **SUCCESS** |
| Games | **17** |
| Strength | packaged EPA |
| Dampening | on @ `completed_reg=16` |
| Overlays | OFF |

Coming soon untouched. This PR’s research shadow (16 locked W2 + W3/W4 appendix, `run_id=nfl-reopening-packet-20260916-shadow`) is supporting only — no −37 / ~81. W2 research flags (market disagreement / compressed totals): CAR@ATL, CLE@TB, DET@BUF, IND@KC, MIA@SF, NO@BAL. Do not raise the prior.

---

## Gate 3 — frozen eval

| Slice | Status |
| --- | --- |
| Alex live FROZEN_EVAL | **NOT_STARTED** |
| This PR research W1 OOS (n=16) | **IN_PROGRESS_THIN** — not the freeze |
| Protocol v1.0 inherited | Predictive YELLOW; confirmatory Market Edge GREEN; Influence LIMITED |
| ATS fitting | **none** |
| Coefficient changes | **none** |

W1 research (not a PASS): EPA margin MAE 12.60 / total 13.25 vs July-31 12.19 / 13.51. W-L’s better margin MAE is circular (post-game 1-0/0-1) and stays refused. n=16 < protocol min 200.

---

## Gate 4 — Release / website **BLOCKED** (pending CLEAR)

| Gate | Status |
| --- | --- |
| Website verification | **BLOCKED** — Coming soon is not this gate |
| Release — spread | **BLOCKED** — no Ryan CLEAR |
| Release — total | **BLOCKED** — own bar; totals PLAY sat |

www `/api/nfl/fair-lines` remains **503** `nfl_edge_board_unavailable`. Flags stay false.

---

## What this packet does not do

- No customer-facing reopen
- No `NFL_EDGE_BOARD_PUBLIC_ENABLED` flip
- No live remat rewrite (Alex receipts folded as-is)
- No KE Team Strength / scoring rewrite / PFF / new architecture / coefficient hunt
- No overlay CLEAR
- No CFB blessing
- No Release PASS on the tracker

---

## Reproduce (research fold only — no live remat)

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/nfl_reopening_packet_20260916.py
PYTHONPATH=services/model-service python3 -m pytest \
  services/model-service/tests/test_nfl_reopening_packet.py -q
```

---

**STOP for Ryan CLEAR.**
