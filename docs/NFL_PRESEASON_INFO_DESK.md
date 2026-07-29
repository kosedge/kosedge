# NFL Preseason Info Desk (separate from season model)

**Rule:** Preseason is a different game. Starters sit or play limited snaps.
Do **not** run `nfl-v1.5-matchup-sim` / KAV selective PLAY as if it were Week 10.

## Season book (REG / POST)
- Engine: KAV + Monte Carlo + `spread_play_v2_cap7`
- Tags: PLAY / PASS (YELLOW gate)
- Graded into enterprise ATS/CLV gates

## Preseason book (PRE)
- Engine: **information / process** only
- Tags: `INFO` | `WATCH` | `PASS` (priced PLAY is rare and never auto-staked)
- Focus: who plays Q1 vs Q3, camp battles, cuts, injury → Week 1 readiness
- **Never** mix preseason ATS into 2024–25 PLAY confirmatory holdout

## Product
- Hub / Edge Board should label preseason rows as research / Week‑1 prep
- Env: `NFL_PRESEASON_MODE=info` (default) — blocks season PLAY tags on PRE games

## What we do not do
- Full EPA/KAV fair lines sold as subscription PLAY in August exhibitions
- Feeding preseason results into season factor promotion
