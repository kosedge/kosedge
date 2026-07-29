# NFL KAV Enterprise Next Steps Report

Generated: 2026-07-28T17:09:29.829353+00:00  
Branch: `nfl-kav-sharpen`  
DB: `127.0.0.1:5432/kosedge`

## 1. Supervised retrain (schema v3 / KAV features)

| Item | Value |
| --- | --- |
| Module | `services/model-service/src/services/nfl_supervised_retrain.py` |
| Task | `src.tasks.run_nfl_supervised_retrain` |
| Runner | `scripts/nfl/retrain_supervised_kav_v3.py` |
| Artifact | `data/ops/nfl-kav-supervised-retrain-v3.json` |

| | Before (active v2) | After (v3 + KAV) | Δ |
| --- | --- | --- | --- |
| Schema / features | 2 / 34 (kav=False) | 3 / 41 (kav=True) | — |
| Train / test | 2513 / 479 | 2992 / 570 | — |
| Test Brier | 0.1831 | 0.1482 | -0.0349 |
| Test margin MAE | 8.255 | 7.48 | -0.7749 |
| Test total MAE | 9.932 | 9.203 | -0.7291 |

Chronological holdout preserved. KAV features: `home/away_kav_{offense,defense,net}_5g`, `diff_kav_net_5g`.

## 2. Board re-sim (KAV-wired market path)

| Item | Value |
| --- | --- |
| Path | `src.tasks.run_nfl_market_simulations` |
| Runner | `scripts/nfl/resim_kav_season_boards.py` |
| Window | season_year=2025 from 2025-09-01 |
| Sims/game | 500 |
| Days / games | 97 / 370 |
| Inserted | 370 (deleted prior: 341) |
| Elapsed | 750.2s |
| Artifact | `data/ops/nfl-kav-resim-summary.json` |

## 3. Odds grading before → after (DB-first)

Before = pre-KAV-wired sprint artifact (`kosedge_nfl_restore`). After = post retrain+resim on local `kosedge`.

| Metric | Before | After | Δ |
| --- | --- | --- | --- |
| Spread MAE | 9.6127 | 9.5513 | -0.0614 |
| Total MAE | 10.1226 | 10.086 | -0.0366 |
| ML Brier | 0.1995 | 0.1933 | -0.0062 |
| ATS hit | 0.4932 | 0.495 | 0.0018 |
| CLV spread avg / +rate (n) | 2.022 / 0.6604 (n=159) | 1.0466 / 0.5092 (n=601) | OC coverage ↑ |
| CLV total avg / +rate (n) | 1.2863 / 0.6325 (n=117) | 0.6772 / 0.5212 (n=378) | OC coverage ↑ |

Owned OC games: 724 → 1931 (warehouse denser now; **no Odds API pull in this run**). MAE/Brier on n=1693 are the primary board signal.

Grading fix: prefer `pipeline_run_at` over backdated `created_at` (`scripts/nfl/odds_open_close_grading.py`).

## 4. Odds densify decision

DB-first grading coverage is complete (1693/1693 projection join). **No Odds API densify performed.**

## 5. What you must do for prod / PR

1. **PR open:** https://github.com/kosedge/kosedge/pull/15 (`nfl-kav-sharpen` → `deploy-vercel`). Compare: https://github.com/kosedge/kosedge/compare/deploy-vercel...nfl-kav-sharpen
2. Local warehouse cutover done: `kosedge_nfl_restore` → `kosedge` (wiped partial kept as `kosedge_wiped_partial_20260728t124723z`).
3. Promote **prod** DB: migration 041 + KAV materialization + matchup KAV columns.
4. Prod retrain: `DATABASE_URL=<prod> .venv/bin/python scripts/nfl/retrain_supervised_kav_v3.py`
5. Prod re-sim: `NFL_KAV_RESIM_SIMS=500 NFL_KAV_RESIM_SEASON=2025 .venv/bin/python scripts/nfl/resim_kav_season_boards.py`
6. Prod grade: `DATABASE_URL=<prod> .venv/bin/python scripts/nfl/odds_open_close_grading.py`
7. Densify owned OC via Odds API only if prod coverage collapses.

## Scripts

- `scripts/nfl/retrain_supervised_kav_v3.py`
- `scripts/nfl/resim_kav_season_boards.py`
- `scripts/nfl/run_kav_enterprise_next_steps.py`
- `scripts/nfl/odds_open_close_grading.py` (pipeline_run_at preference)
