# CFB totals-guard unused holdout (20260903)

**Branch:** `cursor/cfb-totals-guard-holdout-2896` → `deploy-vercel`
**Script:** `scripts/cfb/run_totals_guard_holdout.py`
**Artifacts:** `data/ops/cfb-totals-guard-holdout-20260903/`
**Design SoT:** `docs/CFB_KEI_CALIBRATOR_DESIGN.md` (Task 5; may land via PR 441)
**Spine:** `scripts/cfb/run_spread_tag_close_holdout.py` · `data/ops/cfb-spread-tag-close-holdout-20260903.md`
**Product change:** none (read-only harness). Flag **OFF**. No `apply_cfb_kei` edit,
no pack remat, no `kei_total` divergence enabled, no PLAY flip.

## CoS locks (signed)

1. **No PLAY unsat on ATS-vs-close alone.** NFL totals hit ~61% ATS with ~35% CLV — CFB PLAY stays sat until movement-CLV or a second unused year. `CFB_TOTALS_PLAY_ELIGIBLE` stays **false** even if unused ATS clears 52.4%.
2. **W0–2 is the first enable window only.** Proxy λ under-corrects live 2026 roster ratios — do **not** retune λ on W1 street.
3. **(b) primary**, **(a) fallback**, **(c) exploratory** (mismatch-bucket offsets; not fit here). **No global `MATCHUP_RESPONSE` cut.**

## Honesty

- Join = hist-cal proxy model totals + SDV close (same honesty as spread Tag holdout).
- Fit **2023–2024** only; eval **unused 2025**. Do **not** retune λ / offset from 2025.
- CLV **unavailable** (close-only SDV). Labeled; not minted.
- Proxy KEI understates live 2026 Over-drunk (league-avg roster/QB).
- If (b) GREEN on §4 divergence bars → **STOP and report** — do **not** implement into `apply_cfb_kei`.
- MAE cupcake rule: if (b) kills Over bias but cupcake MAE worsens >0.3 vs identity → report peer vs cupcake split; do **not** auto-kill (b); do **not** silently loosen the bar.
- Mapped games projected: **2384**. Margin preserved under (b) even-split on all rows: **True**.

## STOP report — candidate (b)

- **b_all_green (W0–2):** `False`
- **stop:** `False`
- **implement_apply_cfb_kei:** `False` (always false from this harness)
- **message:** (b) not all-GREEN on W0-2 — continue research; still no apply_cfb_kei edit, flag OFF, no pack recut, no PLAY flip.

## Coefficients (locked from fit 2023–2024 W0–2)

| Candidate | Coefficient | fit n |
| --- | ---: | ---: |
| (b) λ matchup-inflation dampen (**primary**) | 0.542555 | 253 |
| (a) level offset (**fallback**) | 0.515771 | 253 |
| (c) mismatch-bucket offsets | exploratory only — **not fit** | — |

W0–4 tables reuse these locked coefficients (no retune on the wider window / W1).

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

### Peer vs cupcake MAE split (unused 2025 W0–2)

| Slice | n | mean(KEI−close) | MAE |
| --- | ---: | ---: | ---: |
| peer (|s|<10) · identity | 119 | 0.0947 | 5.0307 |
| peer (|s|<10) · (b) | 119 | 1.1192 | 4.6628 |
| cupcake (|s|≥17) · identity | 5 | 3.08 | 5.532 |
| cupcake (|s|≥17) · (b) | 5 | 1.8236 | 4.2072 |

**Cupcake MAE rule triggered:** `False` — no cupcake-MAE exception triggered

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

W0–4 GREEN (b): `True` · (a): `True` (still not a PLAY unlock; coefficients not retuned; flag OFF).

## Reproduce

```bash
PYTHONPATH=services/model-service \
  python3 scripts/cfb/run_totals_guard_holdout.py --seasons 2023,2024,2025 --stamp 20260903
```

Requires SportsDataverse HTTP fetch (`espn_cfb_betting` / `team_box` / `linescores` + `cfb_ratings`) or a populated `--cache-dir` from a prior run.

## CoS one-liner

**Harness only: identity vs (b)/(a) on unused 2025 W0–2; λ locked on 2023–24; flag OFF; if (b) GREEN → STOP/report (no apply_cfb_kei); PLAY stays sat until CLV/second year; no W1 λ retune; no global MATCHUP_RESPONSE cut.**
