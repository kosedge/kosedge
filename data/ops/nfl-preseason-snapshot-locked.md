# NFL 2026 pre-season snapshot — LOCKED

**Status:** LOCKED  
**Locked at:** 2026-08-09 (post defensive variance lift v1.20)  
**Web bundle:** `nfl-preseason-sim-2026-20260809T120227Z`  
**Engine:** `nfl-season-engine-v1.20-defense-variance-lift`  
**Research source:** `data/ops/nfl-season-engine-launch-nfl-season-engine-v1.20-defense-variance-lift-Nteam50000-Nplayer1000-20260809T120227Z`

## Lock criteria (all satisfied)

| Gate | Result |
|------|--------|
| League PA = 11,859 | PASS (11,859.2) |
| League sacks = 1,150 | PASS |
| League INTs ≈ 350.3 | PASS (350.27) |
| PA range ≥ 85 | PASS (97.0) |
| Sacks range ≥ 18 | PASS (22.1) |
| INTs range ≥ 6 | PASS (8.2) |
| Wins Σ = 272 | PASS |
| Unit test `test_defensive_production_stack` | PASS |

## Method locked in

Stretch → soft clip → exact renorm → Pythagorean wins from new PA.

- PA: `1 + 0.85 × ((x − 370.6) / 24)`, soft [328, 425]
- Sacks: `1 + 1.4 × ((x − 35.9) / 2.4)`, soft [26, 49]
- INTs: `1 + 1.6 × ((x − 10.95) / 0.65)`, soft [7.0, 15.5]
- Yards allowed: 0.6× PA intensity, same residual direction; renorm to prior category totals

Do not mutate this bundle without opening a new engine version (v1.21+).
