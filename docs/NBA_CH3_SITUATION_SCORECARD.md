# NBA Chapter 3 — situation scorecard

**Stamp:** `nba-season-engine-v0.1` · `as_of=2026-09-01`  
**Ch1 shrink (unchanged):** `TEAM_CARRY_SHRINK = 0.85`  
**Residual cap (unchanged):** `TEAM_REBASE_RESIDUAL_CAP = 3.0`  
**Brief:** [`docs/NBA_CH3_SITUATION_BRIEF.md`](./NBA_CH3_SITUATION_BRIEF.md)  
**Schedule SoT:** data.nba.com 2025 RS (`002*`) — 1200 games (2026–27 CDN unpublished in build env)

---

## Chosen coefficients (paper-sim)

| Class                         |             Coefficient (net) | Observed rate | Share-weighted |
| ----------------------------- | ----------------------------: | ------------: | -------------: | ----- | ------ |
| Home                          |                      **+1.5** |         0.500 |         +0.750 |
| B2B / 3-in-4 (rest class)     |                      **−2.0** |         0.316 |         −0.632 |
| Travel (`                     |                           Δtz |        ≥ 2h`) |       **−1.0** | 0.079 | −0.079 |
| Altitude visitor (venue flag) |                      **−1.5** |         0.033 |         −0.050 |
| **Cap**                       | **`SITUATION_NET_CAP = 4.0`** |             — |              — |

Paper-sim mean Δnet across team-games ≈ **−0.01** (league-neutral). Mean `|Δnet|` ≈ **0.99**.

---

## Scenario board (league mean net after apply)

| Scenario            |                      Mean net | Min | Max |
| ------------------- | ----------------------------: | --: | --: |
| Neutral baseline    |                     ~Ch2 mean |   — |   — |
| Home only           |              +1.5 vs baseline |   — |   — |
| Away B2B            |              −2.0 vs baseline |   — |   — |
| Away travel         |              −1.0 vs baseline |   — |   — |
| Away altitude       |              −1.5 vs baseline |   — |   — |
| Away B2B+travel+alt | capped at **−4.0** (raw −4.5) |   — |   — |

ORtg/DRtg move ± half the net delta so `ORtg − DRtg` tracks net. Band stays ~105–125.

---

## Apply-on-read contract

```text
team_line' = Ch2 rebased + Σ(class coefs) clipped to ±SITUATION_NET_CAP
PlayerProjection' = Ch5 copy-through; scale PTS/USG only if |ΣPTS − implied_ppg'| > residual cap
```

- Minutes grid on disk: **untouched**
- `TEAM_CARRY_SHRINK`: **untouched**
- Altitude: `venue.altitude_class` on DEN/UTA arenas — **no** `if team ==`

---

## Gates

| Gate                                 | Result |
| ------------------------------------ | ------ |
| 4 classes + cap registered           | PASS   |
| Venue altitude flag (DEN/UTA venues) | PASS   |
| ORtg/DRtg league-sane after apply    | PASS   |
| Σ PTS within residual cap            | PASS   |
| No name-in-an-if in `situation.py`   | PASS   |
| CFB BALL@OSU −40.5                   | PASS   |
| Zero prop / Edge tags                | PASS   |

---

## Forbidden (honored)

Team if · new player means · Ch2 grid rewrite · shrink retune · Edge PLAY · props tab · CFB/NFL · Ch6

---

## Stop

Coefficients registered + applied on read. Board still untagged.  
Next: **Chapter 4** (team KEI + Edge Board, PASS until trusted Best). Chapter 6 still waits.
