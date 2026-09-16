# NFL reopening packet artifacts — 2026-09-16

Ryan-facing document: [`docs/ops/NFL_PRODUCTION_REOPENING_PACKET_2026-09-16.md`](../../../docs/ops/NFL_PRODUCTION_REOPENING_PACKET_2026-09-16.md)

**HOLD public / NO CLEAR** — SYSTEM INTEGRITY PASS; PREDICTIVE VALIDATION PARTIAL (fail-closed); CURRENT SLATE SANITY/PROVENANCE PASS (16/17).

| File | What |
| --- | --- |
| `summary.json` | Folded three-section packet |
| `alex_predictive_customer_receipts.json` | Alex W2 freeze + 16/17 customer-view (cited) |
| `predictive_validation.json` | PARTIAL + supporting W1 historical OOS |
| `customer_view_slate.json` | Supporting live remat rows (not Alex stage2 file) |
| `slate_sanity.json` | 16/17 coverage + no cited absurdities |
| `historical-oos/` | Filed frozen historical OOS diagnostic — **MODEL_SIGNAL_WEAK** (research only) |
| `alex_live_receipts.json` | Earlier Alex remat/integrity receipts |
| `gate1_integrity.json` | ATL@PIT / W-L refuse / overlays OFF |
| `live_window_17.json` | Supporting live `/nfl/fair-lines` capture |

`production_promote=false`. Coming soon ON. No tuning. stage2/ not in this checkout.
