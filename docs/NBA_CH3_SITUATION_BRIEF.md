# NBA Chapter 3 — situation brief

**Phase:** Global modifiers. **No** tags, **no** props.  
**Stamp frozen:** Ch1 shrink `0.85` · Ch2 grids · Ch5 `PlayerProjection`  
**Cap:** `SITUATION_TEAM_PTS_CAP = 3.0` (situation ≠ second prior)  
**Scorecard:** [`docs/NBA_CH3_SITUATION_SCORECARD.md`](./NBA_CH3_SITUATION_SCORECARD.md)

---

## Classes (one coefficient each)

| Class        | Fact                                                                 |
| ------------ | -------------------------------------------------------------------- |
| **Home**     | Designated home side                                                 |
| **B2B**      | `rest_days == 1` **or** 3 games in 4 calendar days (schedule has it) |
| **Travel**   | Prior venue ≥ 1000 mi **or** \|Δtz\| ≥ 2 (same schedule)             |
| **Altitude** | Venue flag (`Ball Arena` / `Delta Center`) — **not** `if team ==`    |

`Δ_raw = Σ class_coeff` → `Δ = clip(Δ_raw, ±3.0)` on team `implied_ppg`.

---

## Allowlist

| Item               | Path                                                |
| ------------------ | --------------------------------------------------- |
| Reader + apply     | `situation.py`                                      |
| Constants          | `priors.SITUATION_TEAM_PTS_CAP`                     |
| Coeffs + paper-sim | `nba_situation_coeffs_v0.json`, `…paper_sim…`       |
| Schedule / venues  | `nba_schedule_2025_26.json`, `nba_venue_flags.json` |
| Builder            | `scripts/nba/build_situation_ch3.py`                |
| Tests / CI         | `test_nba_situation_ch3.py` (NBA-only path)         |
| Docs               | this brief + scorecard                              |

Apply-on-read to the team line. PlayerProjection PTS copy-through **only when Δ ≠ 0**.

---

## Forbidden (honored)

Team if · new player means · new minute grid · Edge PLAY · props tab · CFB/NFL · changing `0.85`

---

## Gates

- League-sane ORtg/DRtg (unchanged Ch2) + PPG′ after Δ in ~100–130
- Σ PTS still inside ±3.0 of the situation-adjusted team total
- CFB BALL@OSU **−40.5**
- No team name in an `if`

---

## Done

Applied on read. Board still untagged.  
**Next:** Chapter 4 (team KEI, PASS until trusted Best). **Not** Ch6.
