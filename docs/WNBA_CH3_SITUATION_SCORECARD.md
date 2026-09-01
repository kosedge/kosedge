# WNBA Chapter 3 — situation scorecard

**Stamp:** `wnba-season-engine-v0.1` · as_of `2026-09-01`  
**Cap:** `SITUATION_TEAM_PTS_CAP = 3.0`  
**Brief:** [`docs/WNBA_CH3_SITUATION_BRIEF.md`](./WNBA_CH3_SITUATION_BRIEF.md)

---

## Chosen coefficients (WNBA-point paper-sim)

| Class    |                                           Coeff |
| -------- | ----------------------------------------------: |
| home     |                                        **+1.5** |
| b2b      |                                        **−1.5** |
| travel   |                                        **−0.5** |
| altitude | **+0.5** (venue list empty at v0 — never fires) |

Paper-sim schedule: **2025 RS** (`gid 102*`, 286 games / 572 team-games).  
2026 CDN schedule 403 in build env — noted on pack.  
Score = clip_rate + mean \|Δ\| (no NBA mid-magnitude anchors). Chosen clip_rate **0**.

PPG′ after Δ on Ch2 lines: **81.55 – 92.10** (within after-situation band 72–94).

---

## Formula

```text
Δ_raw = Σ class_coeff
Δ     = clip(Δ_raw, ±SITUATION_TEAM_PTS_CAP)   # 3.0
team_ppg' = implied_ppg_ch2 + Δ
if Δ ≠ 0: PlayerProjection PTS × (ppg' / Σ PTS)   # copy-through only
```

ORtg / DRtg / pace stay Ch2 — situation is **not** a second net prior.

---

## Frozen (untouched)

| Constant                        |                  Value |
| ------------------------------- | ---------------------: |
| `WNBA_TEAM_CARRY_SHRINK`        |                   0.85 |
| `WNBA_TEAM_REBASE_RESIDUAL_CAP` |                    3.0 |
| `MINUTE_GRID_SUM`               |                    200 |
| Ch5 `PlayerProjection` means    | on disk, not rewritten |

---

## Cross-sport gates

| Gate             | Status                          |
| ---------------- | ------------------------------- |
| Leftover KEI ids | `401857105`, `401857106` listed |
| CON@ATL market   | untouched (no board write)      |
| NBA HOU@OKC      | `kei_spread_home ≈ −4.16`       |
| CFB BALL@OSU     | **−40.51**                      |

---

## Next

Chapter 4 team KEI emit. **Not** props.
