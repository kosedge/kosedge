# t4450u — cover/over RESEARCH_DIAGNOSTIC emit (CERT_CANDIDATE=0)

**Label:** `RESEARCH_DIAGNOSTIC`  
**CERT_CANDIDATE:** `0`  
**`RESEARCH_DIAGNOSTIC` ≠ CERT.** No cert eligibility. No holdout fitting. No CLV. No true-close.  
NFL board **NO-GO**. Coming soon **ON**. No merge / deploy / Odds API.

PR: existing **#638** only (`cursor/t4422u-walkforward-pergame-export-f36b`).  
Does not touch #637 / #639 / #640.

## What changed

`simulate_nfl_game` now emits sample cover/over when a market line is passed:

| Field | Formula |
| --- | --- |
| `markets.cover_prob_home` | `P(margin + market_spread_home > 0)` |
| `markets.over_prob` | `P(total > market_total)` |

No-blend eval flag: `apply_market_blend=False` (default remains `True` for the live path).  
Walk-forward research export passes MS-9 lines **and** `apply_market_blend=False` so the RECORD baseline stays unblended while scoring cover/over against the line.

MS-9 lines are the already-filed `historical_oos_games.csv` columns `market_spread_home` / `market_total` (nflverse close, home-spread convention: negative = home favored). They are **not** owned true-close and are **not** invented EPA.

Integrity vs t4422u seal `6d84bb66`: all 2992 `home_win_prob` / `record_spread_home` / `record_total` identical (unblended baseline unchanged). Cover/over newly populated.

## How to rerun

```bash
python3 data/ops/nfl-team-simulator-calibration-audit/export_walkforward_pergame_2013_2023.py
```

Reuses the sealed nflverse join CSV when present. Engine pin: `nfl-v1.5-matchup-sim` / `nfl-handicap-core-v3.1` / 4000 sims / seed `sha256(game_id|t4422u-unblended-record)[:4]`.

Smell test for the emit path:

```bash
cd services/model-service && python3 -m pytest tests/test_nfl_simulator.py -k "no_blend_eval or cover_over or market_blend" -q
```

## Pins

| Pin | Value |
| --- | --- |
| Code / generation SHA | `f58ff3cd26998fa6239b746ec5879332a10cfc99` |
| Branch tip after artifact seal | `9738b1de61c9023d67c660dc272f91f03e30c6b6` |
| `games.csv` sha256 | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` |
| `manifest.json` sha256 | `9bda93f50f99be227f14dc9004e981ba45d6a9eb86c169a2fab013ac6db0531d` |
| `MISSING.json` sha256 | `45c95f96be7a57924a6334a9818bef98c01a44e3a920adacf49f215c4bcfd51f` |
| `README.md` sha256 | `68a5b02972801abc850bb0216c0258dcd49137fe8d7db96c428e533060015a40` |
| nflverse join sha256 | `97f1c36ce77e9c3952b1ffe8cad3096171c28280cc5d0b48a89f7cceb5cb03a9` (unchanged) |
| Label | `RESEARCH_DIAGNOSTIC` · `CERT_CANDIDATE=0` |
| Seasons | 2013–2023 inclusive; 2024+ not opened |
| n | 2992 (cover 2992 / over 2992 / MS-9 2992) |

See `data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/manifest.json`.

## Remaining gaps (honest)

- EPA win probs still MISSING (rolling features warehouse-only; `DATABASE_URL` unset)
- Owned true-close / CLV still OUT_OF_SCOPE
- 2024+ holdout not opened
- No cert packet, no candidate fitting, no production publish

## Non-actions

- No Odds API
- No merge / deploy / Coming Soon OFF
- No CERT claims
- No #637 / #639 / #640 scope
