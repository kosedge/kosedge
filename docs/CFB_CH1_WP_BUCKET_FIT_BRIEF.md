# Chapter 1 Phase 1 — bucket map fit (power frozen)

**Repo:** `kosedge/kosedge`  
**Base:** `deploy-vercel` after #345 Chapter 1 Phase 0 audit  
**Engine start:** `cfb-season-engine-v0.15-power-sot` · `as_of=2026-08-31`  
**Utah / band 12 / tag cuts:** do not change.

Phase 0 locked:

- Published KEI = `project_game` raw spread + early bias guard (~1.2 pt).
- Sim path uses `margin_calibration` (`USED_IN_SPREAD=False`). Do not slam tanh onto the live line as a shortcut.
- Closes exist **2020–2025** (4,994). **2019 = PBP only.** Train 2020–24 / hold out 2025.
- Mid vs cupcake residuals flipped. Hawaii is **wrong side** (compose/expected points), not a 2-pt SD miss.

---

## Hard constraint from Phase 0

A **monotonic** margin→spread map can shrink mid-band favorites and rescale cupcakes as a class. It **cannot** flip Hawaii’s side unless `expected_team_points` already has Stanford ahead. Hawaii flip is **not** required to merge.

---

## Phase 1A — Replay (must exist before fit)

```bash
python3 scripts/cfb/cfb_ch1_wp_bucket_discovery.py --json
python3 scripts/cfb/cfb_ch1_replay_v015_vs_close.py --seasons 2024,2025 --json
```

Commit `data/ops/cfb-ch1-replay-2024-2025.json`. Do not fit on the n=50 hist-cal sample.

---

## Phase 1B — Fit shape (only after 1A)

**Target:** `published_spread_home = g(raw_margin_home, bucket)`  
Bucket from **|raw_margin|** (Chapter 0 edges).

- Fit in `scripts/cfb/cfb_ch1_bucket_map_fit.py` first
- Named map in `project_game` after raw margin / named table in `priors.py`
- WP on mapped margin; cupcake sat stays
- Do **not** enable `USED_IN_SPREAD` tanh as the map
- Do **not** stretch `WIN_PROB_MARGIN_SD` alone to fake TCU −8.5
- No team ifs; top-7 frozen

Train 2020–2024; holdout 2025.

## Scorecard

| Canary                   | Pass if                                        |
| ------------------------ | ---------------------------------------------- |
| Top-7 power order        | Unchanged                                      |
| BALL@OSU KEI             | Cupcake; WP 90s                                |
| UNC@TCU KEI              | Residual vs −7.5 smaller than 12.9, or blocker |
| HAW@STAN side            | Report; flip not required                      |
| USF E[wins]              | Still below OSU                                |
| Holdout 2025 mid MAE     | Down vs 1A                                     |
| Holdout 2025 cupcake MAE | Not exploded                                   |
