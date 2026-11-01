# Appendix O — one Q2s comparison (t5033u)

**RETRO_FIT / DEV_RESEARCH · CERT=0 · NFL NO-GO · research-consumed only · DRAFT.**

Cite t5033u · fdf91ff5 · d7e0a6bc · 2db90f76 · 2b9f302e · 03a4dd90 CLOSED.
#684 ACCEPT `9982d42f` undisturbed. Guardrails `52c79ee6`.

Frozen before this look. **One look only.** No market/edge/CERT claim.
w=0.5 is a predeclared research candidate — NOT fitted or proven optimum.

## Primary (paired ΔMAE)

- n = **70** (2017 REG W2–W6 sealed 70; no subset)
- MAE baseline (IF.margin_mu) = **10.744702**
- MAE candidate (research.q2s.margin_mu_q2s) = **10.418372**
- ΔMAE = mean(|cand−act| − |base−act|) = **-0.326329**
- 95% paired game-bootstrap CI (B=10000, seed=20261101): **[-0.699989, 0.049333]**
- CI crosses zero: **True**

Negative Δ = point improvement; CI crossing zero = inconclusive, NOT FQ PASS

**Verdict:** INCONCLUSIVE — CI crosses zero; NOT FQ PASS

## Descriptive

- RMSE baseline = 14.170851
- RMSE candidate = 13.774489

| week | n   | MAE base | MAE cand | ΔMAE    | RMSE base | RMSE cand |
| ---- | --- | -------- | -------- | ------- | --------- | --------- |
| 2    | 14  | 11.6604  | 11.1723  | -0.4882 | 14.0871   | 13.4391   |
| 3    | 16  | 11.8037  | 11.5046  | -0.2990 | 15.9424   | 15.5935   |
| 4    | 16  | 12.4824  | 12.2368  | -0.2456 | 17.0928   | 16.4450   |
| 5    | 14  | 8.1177   | 7.8262   | -0.2916 | 10.9541   | 11.0703   |
| 6    | 10  | 8.6658   | 8.3445   | -0.3213 | 9.2604    | 9.0544    |

## Limitations

- Paired game-bootstrap treats games as exchangeable; repeated-team and same-week dependence is not modeled.
- Research-consumed exposure: this 70-game SCORE_RESULTS tip is now used for one Q2s look.
- w=0.5 was not selected on these outcomes; a failed or inconclusive result does not authorize another weight.
- Baseline IF mus/sigma/MC draws were not redrawn; no candidate win/ATS/OU probabilities are claimed.
- Original Q2 EVAL 03a4dd90 remains CLOSED.
- No market/edge/CERT claim.
- RETRO_FIT / DEV_RESEARCH

## Isolation

Baseline IF.margin_mu / total_mu / sigma / MC draws unchanged.
No candidate win/ATS/OU probabilities or coherence claims.
Amends #681 §4 + H6 for this comparison only.
