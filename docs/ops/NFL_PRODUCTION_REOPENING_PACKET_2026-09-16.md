# NFL production reopening packet — 2026-09-16

**Read this file.** Machine twin: [`data/ops/nfl-reopening-packet-20260916/summary.json`](../../data/ops/nfl-reopening-packet-20260916/summary.json).  
**Ryan:** STOP here for CLEAR. This PR does not reopen anything.

| Field | Value |
| --- | --- |
| Recommendation | **HOLD** |
| `production_promote` | `false` |
| Coming soon / public flags | stay dark (`NFL_EDGE_BOARD_PUBLIC_ENABLED = false`) |
| Edge Board | **not flipped** |
| KE Football R&D (#570 PARTIAL v1) | **out of scope** — frozen; not used as Team Strength |
| CFB | **separate** — do not bless CFB from this packet |
| Candidate `run_id` | `nfl-reopening-packet-20260916-shadow` |
| Overlays | personnel / injury **OFF** (fail-closed) |
| Scoring equation | **unchanged** (prior 45.3 / HFA 1.05 / caps ±5 total ±6.5 margin) |

If Ryan later CLEARs fair numbers only, the controlled order is: **model/fair (internal) → overview → Edge Board last**. Totals stay separable from spreads. This packet does **not** authorize that sequence.

---

## Recommendation

**HOLD** — not GO, not NO-GO.

- Candidate path is coherent: packaged EPA, overlays OFF, W-L refuse, July-31 stamps rejected as fair inputs, no −37 / ~81 absurdities.
- Live Railway is **not** that candidate. 47/48 upcoming fairs are still `projection_created_at=2026-07-31`. `active_run_id` is null. One unauthorized DET@BUF remat (2026-09-15, `run_id=null`, model −2.5) is also not the candidate.
- Frozen eval is thin (W1 n=16) and does not clear protocol min N. Pre-repair Lab influence remains LIMITED. No coefficient hunt.

Customer boards stay Coming soon until Ryan CLEAR.

---

## Gate 1 — integrity

| Slice | Result | Evidence |
| --- | --- | --- |
| Candidate path | **PASS** | [`gate1_integrity.json`](../../data/ops/nfl-reopening-packet-20260916/gate1_integrity.json) sha `3e9b4a8a…` |
| Live production isolation | **FAIL** | 47 July-31 upcoming + 16 July-31 W1; `active_run_id=null` |
| Reopen Gate 1 | **FAIL** | Live book is not the candidate |

### What was still HOLD after #564 — resolved on the candidate

| Item | #564 leftover | This packet |
| --- | --- | --- |
| ATL@PIT `remat_spread_home` | `null` (W1 not rematted) | **−0.7631** (EPA, overlays 0) |
| CHI@CAR remat | `null` | **+1.2736** |
| Multi-matchup overlays OFF | pass on 4 keys | still **pass**; no overlay leak |
| W-L vs EPA ≥0.75 on ≥2 | ATL@PIT / CHI@CAR (+ CAR@ATL) | still material; W-L ATL@PIT **−7.55** vs EPA **−0.76** |
| W-L persist refuse | tests only | **re-proved**: ad-hoc uses packaged EPA; missing EPA → `packaged_epa_unavailable`; `refused_win_loss=true` |
| July-31 leak | not filtered | candidate filter **rejects all 48 live rows** |

Focus keys DET@BUF / CAR@ATL / ATL@PIT / CHI@CAR: packaged EPA authoritative, personnel/injury margin 0. Scoring equation not edited.

### Live attest (2026-09-16T14:55:38Z)

Captured: [`live_stamps.json`](../../data/ops/nfl-reopening-packet-20260916/live_stamps.json).

| Probe | Result |
| --- | --- |
| www `/api/nfl/fair-lines` | **503** `nfl_edge_board_unavailable` |
| Railway `/health` | ok, `git_sha=c4ead605` (#564/#567/#568; **not** #570 KE) |
| Railway readiness | **503** no-go; `sample_size=20`; `last_game_date=2026-09-15`; `current_week` on fair-lines **2**; `total_mae=12.49` |
| Fair-lines upcoming | 48 rows: **47× 2026-07-31**, 1× 2026-09-15 DET@BUF (`run_id` null) |
| Fair-lines W1 past | 16/16 July-31; completed-game markets still garbage (SF@LAR mkt +15.5, BAL@IND +17.5) |

July-31 **can still leak if someone painted live rows**. It **cannot** enter this candidate: authorization requires `run_id=nfl-reopening-packet-20260916-shadow` and rejects `2026-07-31` plus null-run remats.

---

## Gate 2 — slate sanity

| Slice | Result |
| --- | --- |
| W2 coverage | **16/16** |
| W3+W4 appendix | 32 games (same remat, same provenance) |
| Absurdities (−37, totals ~81, non-finite) | **none** |
| Provenance | every row → packet `run_id`; overlays OFF; live July-31 **not** used as fair |
| Sanity | **PASS** with flags |

Market join is live Odds attach (`odds_as_of=2026-09-16T14:55:38Z`). Fair is research EPA remat, **not** live `model_spread_home`.

### Week 2 — Market → KE fair (candidate)

Home-oriented. Projected score is away @ home.

| Game | Market spread | KE fair spread | Market total | KE fair total | Projected score | Flag |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| DET@BUF | −4.5 | −1.58 | 54.5 | 46.10 | DET 22.3 @ BUF 23.8 | total vs market −8.4 |
| CAR@ATL | +2.5 | −2.90 | 44.0 | 44.53 | CAR 20.8 @ ATL 23.7 | **favorite flip** |
| CIN@HOU | −2.5 | −4.94 | 46.5 | 44.61 | CIN 19.8 @ HOU 24.8 | |
| CLE@TB | −8.5 | −1.63 | 41.5 | 42.08 | CLE 20.2 @ TB 21.9 | spread vs market +6.9 |
| GB@NYJ | +3.5 | +5.25 | 44.5 | 46.41 | GB 25.8 @ NYJ 20.6 | |
| JAX@DEN | −2.5 | −1.90 | 45.5 | 44.01 | JAX 21.1 @ DEN 23.0 | |
| LV@LAC | −6.5 | −3.89 | 43.5 | 42.01 | LV 19.1 @ LAC 23.0 | |
| MIA@SF | −13.5 | −3.96 | 45.5 | 47.67 | MIA 21.9 @ SF 25.8 | spread vs market +9.5 |
| MIN@CHI | −5.5 | −1.85 | 48.0 | 42.70 | MIN 20.4 @ CHI 22.3 | |
| NO@BAL | −8.5 | −1.59 | 47.5 | 43.52 | NO 21.0 @ BAL 22.6 | spread vs market +6.9 |
| PHI@TEN | +7.0 | +4.03 | 39.5 | 44.02 | PHI 24.0 @ TEN 20.0 | |
| PIT@NE | −5.0 | −2.88 | 41.5 | 45.00 | PIT 21.1 @ NE 23.9 | |
| SEA@ARI | +3.5 | +3.80 | 41.0 | 44.68 | SEA 24.2 @ ARI 20.4 | |
| WSH@DAL | −4.0 | −1.09 | 50.5 | 50.27 | WSH 24.6 @ DAL 25.7 | |
| IND@KC | −6.5 | −0.80 | 46.5 | 46.05 | IND 22.6 @ KC 23.4 | spread vs market +5.7 |
| NYG@LAR | −7.0 | −6.44 | 48.0 | 46.71 | NYG 20.1 @ LAR 26.6 | |

**W2 flagged:** CAR@ATL, CLE@TB, DET@BUF, IND@KC, MIA@SF, NO@BAL.  
Injury/personnel status: **OFF** on every row. Model-input freshness: packaged EPA priors `as_of=2026-08-08`. Data timestamp + `run_id` on [`shadow_slate.json`](../../data/ops/nfl-reopening-packet-20260916/shadow_slate.json).

Flags are market disagreement / compressed totals — not −37 / 81. CHI@CAR W1 actual 96 vs EPA ~45 remains the known compressed-model residual. Do not raise the prior.

W3/W4 remat is in the same artifact (same `run_id`). Later-week flags listed in `summary.json` `gate2.flagged_later_weeks`.

---

## Gate 3 — frozen evaluation

Protocol: [`docs/lab/NFL_SPREAD_VALIDATION_PROTOCOL_v1.md`](../lab/NFL_SPREAD_VALIDATION_PROTOCOL_v1.md) v1.0 (`cos_signed`). Historical replay stamp `nfl-historical-replay-v1-20260809`. **No ATS fitting. No coefficient changes.**

### Pre-repair (inherited — equation not retuned)

| Source | Grade |
| --- | --- |
| Lab scorecard 2026-09-04 Predictive Quality | YELLOW |
| Lab Market Edge (confirmatory 2024–25 PLAY band) | GREEN |
| Lab Evidence Quality | GREEN |
| Subscriber Influence | **LIMITED** |
| Enterprise gates 2026-07-28 overall | **RED** (full-slate ATS); selective PLAY ready true |

Repair did not touch 45.3 / 1.05 / caps. Historical ATS/CLV is **inherited**, not a new fit.

### Current-season OOS — W1 2026 actuals (n=16)

Priors are 2025 packaged EPA (`as_of=2026-08-08`) — no W1 2026 leakage. Below protocol min N=200 → **cannot PASS**.

| Book | Margin MAE | Margin bias | Total MAE | Total bias |
| --- | ---: | ---: | ---: | ---: |
| EPA candidate | 12.60 | +0.84 | 13.25 | −4.49 |
| July-31 live stamps | 12.19 | +2.20 | 13.51 | −6.28 |
| Post-game W-L (refused path) | 7.70 | +1.86 | 13.44 | −3.92 |

**Do not read W-L MAE as a win.** W-L indices are 1-0 / 0-1 **after the same game** — circular. That is why ad-hoc persist is refused. EPA vs July-31 is the honest pair: totals slightly better, margin MAE slightly worse, bias improved. Not a license to retune.

CHI@CAR 96 vs ~45 and other 60+ totals sit in the locked compressed band. Leave the equation.

Gate 3 verdict: **IN_PROGRESS_THIN** — not PASS.

---

## What this packet does not do

- No customer-facing reopen
- No `NFL_EDGE_BOARD_PUBLIC_ENABLED` flip
- No KE Team Strength / scoring rewrite / PFF / new architecture / coefficient hunt
- No overlay CLEAR (`unlock_overlays` still Ryan-only)
- No CFB blessing
- No Release PASS on the tracker

---

## Reproduce

```bash
PYTHONPATH=services/model-service python3 scripts/nfl/nfl_reopening_packet_20260916.py
PYTHONPATH=services/model-service python3 -m pytest \
  services/model-service/tests/test_nfl_reopening_packet.py \
  services/model-service/tests/test_nfl_564_remediation.py \
  -q
```

---

**STOP for Ryan CLEAR.**
