# t4910u control pins (read-only)

Sealed copies from draft [#672](https://github.com/kosedge/kosedge/pull/672)
`data/ops/nfl-hist-diag-score-70-t4910u/` (ops-box path
`ops/nfl_enterprise_green_t4359u/nfl-hist-diag-score-70-t4910u/`).

| File | Role |
| --- | --- |
| `SCORE_RESULTS.json` | sealed baseline IF forecasts + realized. sha256 **`2b9f302e097183ef275185a4edb100ab206565a087ca1ce78dbe8062524e877a`** |
| `SCORE_RESULTS.md` | human table (not re-scored) |
| `SAMPLE_MANIFEST_70.json` | exact frozen 70-game 2017 REG manifest |
| `SHA256SUMS` | packet digests from control |
| `EXEC_FREEZE_*` / `OWNER_ACCEPT_*` / `PINS.json` | authority, not re-opened |

`f_margin` = `forecast_margin` (IF forecast margin, home−away).
`r_margin` = `realized_margin`.

Original control unchanged. Do not edit `score_t4910u.py`.
Do not re-invoke Independent Fair. MC draws stay sealed and unused.

**RETRO_FIT / DEV_RESEARCH** on every consume.

#684 2013 REG W2 demo fixtures are mechanical-only and are **not** in this pin set.
