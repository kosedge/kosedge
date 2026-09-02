# NHL Chapter 3 — situation brief

**Phase:** Global modifiers in **goal units**. **No** emit. **No** props.  
**Stamp frozen:** shrink `0.85` · Ch2 TOI + tandem · Ch5 pack  
**Cap:** `NHL_SITUATION_GOAL_CAP = 0.35` (situation ≠ second prior)  
**Scorecard:** [`docs/NHL_CH3_SITUATION_SCORECARD.md`](./NHL_CH3_SITUATION_SCORECARD.md)  
**Leave alone:** blank KEINHL · NBA · WNBA · CFB · NFL · Ch1/Ch2/Ch5 packs

---

## Classes (one coefficient each)

| Class        | Fact                                                                |
| ------------ | ------------------------------------------------------------------- |
| **Home**     | Designated home side                                                |
| **Rest/B2B** | `rest_days == 1` **or** 3 games in 4 calendar days                  |
| **Travel**   | Prior venue ≥ 1000 mi **or** \|Δtz\| ≥ 2 (official schedule metros) |
| **Altitude** | Venue flag (`Ball Arena` / `Delta Center` / `Rice-Eccles Stadium`)  |

`Δ_raw = Σ class_coeff` → `Δ = clip(Δ_raw, ±0.35)` on team `GF/G`.  
Paper-sim on **NHL goals** — does **not** copy NBA `+2.0` or WNBA `+1.5`.

---

## Allowlist

| Item               | Path                                                               |
| ------------------ | ------------------------------------------------------------------ |
| Reader + apply     | `nhl_season_engine/situation.py`                                   |
| Constants          | `priors.NHL_SITUATION_GOAL_CAP`                                    |
| Coeffs + paper-sim | `nhl_situation_coeffs_v0.json`, `nhl_situation_paper_sim_ch3.json` |
| Schedule / venues  | `nhl_situation_schedule_2026.json`, `nhl_venue_flags.json`         |
| Builder            | `scripts/nhl/build_situation_ch3.py`                               |
| Tests / CI         | `test_nhl_situation_ch3.py` (NHL-only)                             |
| Docs               | this brief + scorecard                                             |

Apply-on-read to the team GF/G line. Skater **G** / goalie **SA** copy-through **only when Δ ≠ 0**.

---

## Forbidden

Team if · new means · new TOI grid · filling KEINHL · props · changing `0.85` · NBA/WNBA/CFB/NFL

---

## Gates

- GF/GA league-sane after apply (GF′ band ~2.0–4.5; GA stays Ch1)
- Σ skater G still inside residual cap (disk + after copy-through)
- Goalie shares still ~1.0
- `/edge-board/nhl` KEI still blank
- NBA/WNBA/CFB untouched

---

## Done

Coeffs registered + applied on read. Board still markets-only.  
**Next:** Chapter 4 (first time the KEI column may fill). PASS until trusted Best. **Not** props.
