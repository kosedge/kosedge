# EXEC FREEZE t4910u — Bounded Diagnostic Score (70)
NFL NO-GO · CERT=0 · Binds OWNER_ACCEPT_t4910u on card 27b2bb7c. Any change → escalate Ryan; no silent edit.

```yaml
if_tip: 6ca03716fe52930332d5ffba302c312a651980cc
market_blend: 0
contract: b41f4b43
as_of: cf514078
pbp: 84eacd96
lineage: {w2: {tip: 440314e4, ro: 91e2d7db}, w3w6: {tip: f92aaea3, ro: af30adba}}
epa_success_label: RETRO_FIT / DEV_RESEARCH
simulations: 4000
seed_base: 201710            # hist-specific; Cursor must not change without escalate
seed_formula: "seed = seed_base + (int(sha256(game_id.encode('utf-8')).hexdigest()[:12], 16) % 1000003)"
tie_treatment: "margin == 0 -> away (IF fair ML path)"
rest_days: BIND_PACKET_ONLY  # sealed ET DOW (155d3ca0); W8 eval caller re-derive FORBIDDEN
sample_manifest_rule: "union of complete rows from W2 tip 440314e4 + W3-W6 tip f92aaea3; exclude DET_NO, MIA_ATL, SF_WAS, NYG_DEN"
expected_n: 70
replacement: forbidden   # failed/ineligible remain visible
metrics:
  - margin/spread/total/WP vs realized
  - MAE/RMSE margin and total
  - Brier/log-loss on WP
  - WP calibration bins (EXPLORATORY, N=70)
  - straight-up outcome accuracy (ties separate; no line)
  - dispersion: forecast-mean SD vs realized SD, envelope, realized-on-forecast slope (interpret forecast-mean variation vs outcome noise)
  - predictive-distribution coverage (e.g. 50/80/90% margin/total intervals) if sims support
  - NO CLV / NO 2017 market
benchmarks:
  naive_wl: "WP from pregame W-L record (win% diff), margin per frozen mapping in implementation; pregame-only"
  pickem: "margin 0, WP 0.5"
  constant_total: 45.3
deliverables_path: data/ops/nfl-hist-diag-score-70-t4910u/
deliverables: [SAMPLE_MANIFEST_70, SCORE_RESULTS, METRICS_TABLE, COMPRESSION_HIST_DIAG, ASSUMPTIONS, CALL_AUDIT, SHA256SUMS]
executions_allowed: 1
review: "Alex RO → PASS_DIAG_SCORE | CONDITIONAL | RETURN before interpretation"
not_authorized: [fit, tune, weight/feature/math change, sample swap, T2 last-played, 2024-25 sealed access, odds acquire, historical market claims, edge claim, publish, betting, merge, E1, CERT, re-run]
```

Prose: score-only diagnostic of frozen IF baseline at tip 6ca03716 on 70 verified 2017 REG games, quantifying compression (t4902u cb0992e2). Implementer must seal the exact naive W-L formula code in ASSUMPTIONS before the run; seed formula above is binding.
