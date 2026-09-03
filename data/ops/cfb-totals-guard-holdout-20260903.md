# CFB totals-guard unused holdout (20260903)

**Branch:** `cursor/cfb-totals-guard-holdout-2896` → `deploy-vercel`
**Script:** `scripts/cfb/run_totals_guard_holdout.py`
**Artifacts:** `data/ops/cfb-totals-guard-holdout-20260903/`
**Design SoT:** `docs/CFB_KEI_CALIBRATOR_DESIGN.md` (Task 5; may land via PR 441)
**Spine:** `scripts/cfb/run_spread_tag_close_holdout.py` · `data/ops/cfb-spread-tag-close-holdout-20260903.md`
**Product change:** none (read-only harness). No `apply_cfb_kei` edit, no pack remat,
no `kei_total` divergence enabled, no PLAY unsat.

## Honesty

- Join = hist-cal proxy model totals + SDV close (same honesty as spread Tag holdout).
- Fit **2023–2024** only; eval **unused 2025**. Do **not** retune λ / offset from 2025.
- W0–2 is the first GREEN window — do **not** retune λ on live W1 street.
- CLV **unavailable** (close-only SDV). Labeled; not minted.
- Proxy KEI understates live 2026 Over-drunk (league-avg roster/QB). Unused GREEN on
  proxy is a necessary gate, not a claim live W1 will match.
- This harness does **not** enable `kei_total` divergence or unsat PLAY.
- GREEN bars below are design §4 divergence gates only. PLAY unsat needs CLV or a
  second unused year (ATS-only vs close is insufficient).
- Mapped games projected: **2384**. Margin preserved under (b) even-split on all rows: **True**.

## Coefficients (locked from fit 2023–2024 W0–2)

| Candidate | Coefficient | fit n |
| --- | ---: | ---: |
| (b) λ matchup-inflation dampen | 0.542555 | 253 |
| (a) level offset | 0.515771 | 253 |

W0–4 tables reuse these locked coefficients (no retune on the wider window).

## Results — unused 2025 W0–2 (PRIMARY)

| Path | n | mean(KEI−close) | MAE | Over-sign bias | CLV+ |
| --- | ---: | ---: | ---: | ---: | --- |
| identity (`kei=model`) | 146 | 0.2028 | 4.9047 | 0.0616 | unavailable |
| (b) λ dampen | 146 | 1.0558 | 4.6064 | 0.1507 | unavailable |
| (a) level offset | 146 | 0.7186 | 4.9445 | 0.1096 | unavailable |

### GREEN bars (divergence only — not PLAY)

| Candidate | abs(mean)≤1 | MAE not worse >0.3 | mean not >+2 | all GREEN |
| --- | --- | --- | --- | --- |
| (b) | False | True | True | False |
| (a) | True | True | True | True |

Proxy note: identity mean gap on unused W0–2 is already near zero (0.2028). Live 2026 roster path is hotter; do not ship divergence from this proxy table alone.

## Results — contaminated 2023–2024 W0–2 (fit / confirmatory)

| Path | n | mean(KEI−close) | MAE | Over-sign bias | CLV+ |
| --- | ---: | ---: | ---: | ---: | --- |
| identity | 253 | -0.5158 | 5.6173 | -0.0514 | unavailable |
| (b) λ dampen | 253 | 0.4571 | 5.2621 | 0.0751 | unavailable |
| (a) level offset | 253 | 0.0 | 5.6041 | 0.004 | unavailable |

## Results — unused 2025 W0–4 (optional confirmatory)

| Path | n | mean(KEI−close) | MAE | Over-sign bias | CLV+ |
| --- | ---: | ---: | ---: | ---: | --- |
| identity | 245 | 0.026 | 4.8387 | 0.0408 | unavailable |
| (b) λ dampen | 245 | 0.923 | 4.4659 | 0.1755 | unavailable |
| (a) level offset | 245 | 0.5418 | 4.871 | 0.0939 | unavailable |

W0–4 GREEN (b): `True` · (a): `True` (still not a PLAY unlock; coefficients not retuned).

## Reproduce

```bash
PYTHONPATH=services/model-service \
  python3 scripts/cfb/run_totals_guard_holdout.py --seasons 2023,2024,2025 --stamp 20260903
```

Requires SportsDataverse HTTP fetch (`espn_cfb_betting` / `team_box` / `linescores` + `cfb_ratings`) or a populated `--cache-dir` from a prior run.

## CoS one-liner

**Harness only: identity vs (b)/(a) on unused 2025 W0–2; coefficients locked on 2023–24; no product KEI path change; PLAY stays sat until CLV/second-year bar.**
