# CFB P3 — game + total sim distributions (research only)

**Date:** 2026-08-13  
**Branch:** `feat/cfb-p3-game-total-sim` → `deploy-vercel` (stacked on #233 + #234)  
**Engine:** `cfb-season-engine-v0.11-game-total-sim`  
**Doctrine:** Model = research fair only. `used_in_spread` stays **false**. No KEI. No lock. Separate spread path and total path.

---

## Method (one-liner)

Independent Gaussian **margin** (strength / HFA / coaching mean + research σ) and Gaussian **total** (pace × both-offense environment × explosiveness). Scores = `(total ± margin) / 2`. Weather **not applied**.

Default **N = 5,000** for project-game (was a point estimate + Φ). Season-sim HTTP default raised **15 → 200** (cap 2,000). Densified season paths are still not an official slate.

## Slate coverage

| | |
| --- | --- |
| Official 2026 FBS schedule | **No** |
| What exists | `packaged_sample_densified` seed + synthetic fill |
| Product path | On-demand `project-game(home, away, week, neutral?)` |
| FCS | Games kept in history; non-FBS side widens σ and is labeled — not generic −25 |
| CFP / natty | **Stub.** `season_futures.cfp_make` / `natty` = null. Densified SOS cannot emit honest make rates. |

P3 does **not** claim an ATS fix. W0–1 remains ~47.7% / 8.36 from P2.

---

## Separate total path

```
league_total = 2 * 25.9
off_env = 0.5 * (home_off/away_def + away_off/home_def)
total_mean = league_total * pace * off_env^0.55 * expl_mult
total_sd   = 13.6 * early_mult + open_QB + identity_u   clip [10, 22]
```

Not `total = f(spread)` and not `home_exp + away_exp` from the HFA score path. HFA lives on the margin path only (recovered home score moves ~half the HFA gap).

Key numbers (3, 7, 10, 14 and common totals) are **reported** cover/over probabilities — not an auto-bet rule.

---

## Smoke examples (N=2000, Week 1, research only)

| Matchup | Spread (home) | Total | WP home | Team totals | margin σ | total σ |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| BALL @ OSU | −38.9 | 58.6 | 94% | 48.7 / 9.9 | 24.7 | 15.9 |
| FSU @ UGA (open/open) | −11.7 | 54.5 | 67% | 33.1 / 21.4 | **26.0** | **18.7** |
| OSU @ TEX (neutral, incumbents) | +4.9 | 59.0 | 41% | 27.0 / 31.9 | 21.9 | 15.8 |
| MASS @ MICH (open vs returning) | −27.1 | 52.9 | 86% | 40.0 / 12.9 | 24.7 | 16.1 |
| RICE @ LSU | −28.8 | 50.2 | 87% | 39.5 / 10.7 | **26.0** | 17.0 |
| BALL @ ALA (open camp) | −31.4 | 52.5 | 89% | 41.9 / 10.6 | **26.0** | 17.2 |

Open-QB / dual-chaos games hit the margin-σ cap. Incumbent-vs-incumbent is tighter. Blowout magnitudes (OSU −39) are **ranking-prior theater if published** — that is why `used_in_spread` stays false.

Team totals sum to fair total by construction.

JSON: `data/ops/cfb-p3-smoke-20260813.json`

---

## Integration

- `POST /cfb/season-engine/project-game` returns spread, total, WP, team totals, `distributions`, `n_sims`, `used_in_spread: false`
- Immutable `model_predictions` write unchanged (version + as_of); `used_in_spread=false` on the row
- Status **200** with v0.11; `season_futures` stubbed
- Edge Board CFB still markets-only
- UI: research-only copy; total path labeled; sim N + total σ shown

## Rebuild / smoke

```bash
python scripts/cfb/smoke_p3_project_games.py
```

---

## Remaining blockers

**To P4 (season futures):** official 2026 FBS slate. Until then CFP/natty **must stay stub**. Densified win totals are not conserved futures.

**To `used_in_spread`:** W0–1 ATS still fails; blowout scale is not closer-like; roster holes; no release gate (P5); no KEI.

**Ready for P4 brief:** yes — as a **stub-first** futures brief unless an official slate lands. Do not invent 12% natty.
