# WNBA Chapter 3 — situation brief

**Phase:** Global modifiers. **No** Ch4 emit. **No** props.  
**Stamp frozen:** Ch1 shrink `0.85` · Ch2 grids (200) · Ch5 `PlayerProjection`  
**Cap:** `SITUATION_TEAM_PTS_CAP = 3.0` (situation ≠ second prior)  
**Scorecard:** [`docs/WNBA_CH3_SITUATION_SCORECARD.md`](./WNBA_CH3_SITUATION_SCORECARD.md)

---

## Classes (one coefficient each)

| Class        | Fact                                                           |
| ------------ | -------------------------------------------------------------- |
| **Home**     | Designated home side                                           |
| **B2B**      | `rest_days == 1` **or** 3 games in 4 calendar days             |
| **Travel**   | Prior venue ≥ 1000 mi **or** \|Δtz\| ≥ 2                       |
| **Altitude** | Venue flag only — **not** `if team ==` (none registered at v0) |

`Δ_raw = Σ class_coeff` → `Δ = clip(Δ_raw, ±3.0)` on team `implied_ppg`.

Coeffs from **WNBA-point paper-sim** — **forbidden** to copy NBA `+2.0 / −1.5`.

---

## Allowlist

| Item               | Path                                                                 |
| ------------------ | -------------------------------------------------------------------- |
| Reader + apply     | `situation.py`                                                       |
| Constants          | `priors.SITUATION_TEAM_PTS_CAP`                                      |
| Coeffs + paper-sim | `wnba_situation_coeffs_v0.json`, `wnba_situation_paper_sim_ch3.json` |
| Schedule / venues  | `wnba_schedule_2025.json`, `wnba_venue_flags.json`                   |
| Builder            | `scripts/wnba/build_situation_ch3.py`                                |
| Tests / CI         | `test_wnba_situation_ch3.py` (WNBA-only path)                        |
| Docs               | this brief + scorecard                                               |

Apply-on-read to the team line. PlayerProjection PTS copy-through **only when Δ ≠ 0**.

---

## Forbidden (honored)

Team if · new player means · new minute grid · Ch4 KEI emit · props PLAY · copying NBA coeffs · changing `0.85` · NBA/CFB/NFL packs

---

## Gates

- PPG′ after Δ in WNBA-sane band (~72–94)
- Σ PTS still inside ±3.0 of the situation-adjusted team total
- Leftover fair-line ids listed, not blended
- NBA HOU@OKC ~−4.2 · CFB BALL@OSU **−40.5**
- No team name in an `if`

---

## Done

Applied on read. Board leftover still leftover.  
**Next:** Chapter 4 (team KEI emit). **Not** props.
