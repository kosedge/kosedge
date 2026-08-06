# Historical Calibration Reports — NFL + CFB

**Date:** 2026-08-06  
**Branch:** `feat/historical-calibration-reports`  
**Module:** `services/model-service/src/services/proof_layer/calibration_report.py`

## Purpose

Reproducible historical calibration from the unified proof-layer JSONL lake: how logged projections perform against closes and final results. Built on the proof layer shipped in PR #128 — **not** the CFB SP+ closing-line backtest in `cfb_season_engine/historical_calibration.py`.

## Quick start

### GET report (in-memory)

```bash
curl -sS "$MODEL_SERVICE_URL/proof/calibration-report?sport=nfl" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET"

curl -sS "$MODEL_SERVICE_URL/proof/calibration-report?sport=cfb&engine_version=cfb-season-engine-v0.9-inseason&season=2026" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET"
```

Optional filters: `engine_version`, `season`, `from` / `to` (ISO `projected_at` bounds).

### POST generate artifact

Writes JSON under `services/model-service/data/ops/calibration_reports/` (Railway: `/app/data/ops/calibration_reports/`).

```bash
curl -sS -X POST "$MODEL_SERVICE_URL/proof/calibration-report/generate" \
  -H "Content-Type: application/json" \
  -H "x-kosedge-secret: $INTERNAL_API_SECRET" \
  -d '{"sport": "nfl"}'
```

### Local script

```bash
bash scripts/generate-calibration-reports.sh
```

## Report contents

| Section | Notes |
|---------|-------|
| **Sample** | `n_logged`, `n_with_close`, `n_with_result` |
| **Record** | ATS / O/U / SU from proof-layer grading |
| **Average error** | Margin MAE + bias, total MAE |
| **CLV** | Spread/total CLV (closes required; never invented) |
| **Bias slices** | Home fav/dog (`model_spread_home` sign), model ATS pick home/away, early season (week ≤ 4) |
| **Honesty flags** | `thin_sample` when n_with_result < 30, `no_closes`, `margin_bias_detected`, etc. |

Structured JSON includes `summary_text` (markdown-friendly) and `honesty_flags`.

## Reproducibility

Each report records:

- Filter inputs (`sport`, `engine_version`, `season`, date range)
- Lake path (`inputs.lake_dir`)
- Engine versions and seasons seen in the filtered set
- `generated_at` timestamp

Re-run the same query after logging more closes/results to refresh.

## Example artifacts (2026-08-06 smoke)

Local lake was empty at generation time — artifacts are honest zero-sample baselines:

| Sport | Artifact | Honesty |
|-------|----------|---------|
| NFL | `services/model-service/data/ops/calibration_reports/nfl_all-versions_20260806T142153Z.json` | `no_projections`, `thin_sample` |
| CFB | `services/model-service/data/ops/calibration_reports/cfb_all-versions_20260806T142153Z.json` | `no_projections`, `thin_sample` |

**Sample limitations:** Production Railway lake may have smoke projections from unified proof-layer testing, but meaningful calibration requires sustained logging plus manual (or automated) close/result capture. Do not overclaim until n_with_result ≥ 30 and closes are populated.

## Tests

```bash
cd services/model-service
PYTHONPATH=src python3 -m pytest tests/test_calibration_report.py tests/test_proof_layer.py -q
```

Fixtures cover thin vs adequate samples, bias slices, filters, artifact write, and HTTP endpoints.

## Related

- Unified proof layer: `data/ops/unified-proof-layer-20260806.md`
- API docs: `GET /proof/docs`

## Honesty

- Closes are never invented; CLV requires captured closes.
- Thin samples are flagged explicitly in JSON and summary text.
- Does not change live boards or projection math.
