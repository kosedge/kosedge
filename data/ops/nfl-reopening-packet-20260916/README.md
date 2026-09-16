# NFL reopening packet artifacts — 2026-09-16

Ryan-facing document: [`docs/ops/NFL_PRODUCTION_REOPENING_PACKET_2026-09-16.md`](../../../docs/ops/NFL_PRODUCTION_REOPENING_PACKET_2026-09-16.md)

**NO-GO CLEAR** — SYSTEM INTEGRITY PASS; PREDICTIVE VALIDATION FAIL; CURRENT SLATE SANITY/PROVENANCE PASS (flags).

| File | What |
| --- | --- |
| `summary.json` | Folded three-section packet + NO-GO CLEAR |
| `predictive_validation.json` | Frozen eval on SHA `153b6a884a8e` — FAIL |
| `customer_view_slate.json` | Complete 17-game customer-view (internal) |
| `slate_sanity.json` | Slate sanity/provenance audit — PASS with flags |
| `live_window_17.json` | Live `/nfl/fair-lines` 17-row capture |
| `alex_live_receipts.json` | Alex live receipts (cited, not recomputed) |
| `gate1_integrity.json` | ATL@PIT / W-L refuse / July-31 filter |
| `shadow_slate.json` | Research W2–W4 shadow (supporting) |
| `numerical_audit.json` | Research absurdity / flag / provenance |
| `frozen_eval.json` | Raw W1 OOS numbers (graded in predictive_validation) |
| `live_stamps.json` | Earlier Railway capture (pre-Alex remat attest) |

`production_promote=false`. Boards stay Coming soon. KE #570 out of scope. No tuning.
