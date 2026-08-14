# CFB Phase 1 — Power SoT + research season projections

**Date:** 2026-08-14  
**Branch:** `feat/cfb-phase1-projections-power-sot` → `deploy-vercel` (stacked on #240)  
**Engine:** `cfb-season-engine-v0.15-power-sot`  
**Power:** `cfb-power-sot-v0.15-20260814` · **as_of** `2026-08-14`  
**Projections:** `cfb-season-projections-v0.15-n10000-20260814` · **N = 10,000**  
**Doctrine:** Model = research fair only. `used_in_spread` stays **false**. No KEI. No PLAY/LEAN. No invented CFP%.

---

## SoT contract

One composed strength table feeds every research surface.

| Consumer | Reads |
| --- | --- |
| Team DNA `/pro/cfb/teams` | Packaged `cfb_power_sot_2026.json` only |
| Project-game | `universe.teams[code].offense_index / defense_index` — same compose the pack snapshots |
| Season projections `/pro/cfb/projections` | Packaged frozen-SoT artifact (not a 20-path live sim) |
| Status API | `power_version`, `power_as_of`, `n_teams=136`, `projection_artifact_id` |

Formula: `power_index = 0.5 * (offense_index + defense_index)` from the v0.14 efficiency backbone + roster/QB prior. **No parallel demo rating.**

Thin-sample / warehouse-fill labels stay on the pack. No silent 50/50.

Immutable snapshot. Regenerate with:

```bash
python scripts/cfb/package_power_sot_and_projections.py
```

Writes:

- `services/model-service/src/services/cfb_season_engine/data/cfb_power_sot_2026.json`
- `services/model-service/src/services/cfb_season_engine/data/cfb_season_projections_2026.json`

---

## Season projections — N and method

- **N = 10,000**
- **Slate:** official ESPN 2026 only (889 games). Densified seed is never used.
- **Method:** frozen-SoT independent Bernoulli. `P(home)` comes from the same `expected_team_points` + v0.13 tanh calibration + HFA path as `realize_game_scores`. In-path strength evolution is **off** so the published table stays on one power snapshot.
- **Bands:** E[wins], p10 / p50 / p90, σ, optional P(bowl) at 6+ wins.
- **Conservation:** each scored game awards one win. Σ FBS E[wins] is below `n_games_scored` when FCS sides take wins.
- **CFP / natty:** omitted (`null`). Not product numbers.
- Path-coherent `simulate_full_season` remains on the API for research; it is not the desk artifact (too slow for N≥5k on the official slate).

---

## In-season update rules (September SoT)

Ops here override the old “early weeks move more” foundation.

| Games played / week | Behavior |
| --- | --- |
| 0–2 (W0–W2) | **Prior-heavy.** Small `week_weight` (0.16–0.28). Continuity / QB class still dominate. Wide σ. |
| 3–8 | Blend ramp toward observed efficiency (`week_weight` 0.40–0.62). games/N shrinkage via `alpha = 0.32 / (1+n)^0.70`. |
| 9+ | Still shrink. Do **not** fully replace the prior. |

Guards already in code:

- Per-game residual clamp (`MAX_GAME_MOVE=3.5`, `MAX_RESIDUAL=28`)
- Cumulative delta clamp (`MAX_CUMULATIVE_DELTA=12`)
- Preseason baseline always inspectable

**No Week-1 cliff.** One noisy opener cannot rewrite DNA or project-game.

**Injury / QB inactive:** full-strength vs current path when a live feed exists. **Stub** — no live injury API in this phase.

Module: `src.services.cfb_season_engine.in_season_update`.

---

## Power vs E[wins] (not a bug)

Power is talent/prior. E[wins] is power × official SOS. They must not be forced equal.

- OSU is #1 power and #6 E[wins] (8.88)
- ND / MIA lead E[wins] on easier paths
- USF (#43 power) and UNT (#38) sit high in E[wins] because of SOS, not a second rating
- UGA / ALA sit ~#16–19 power (open-QB honesty on the v0.14 prior) and ~7.2 E[wins] on a hard SEC slate

Do not “fix” G5 win totals up to look like a poll.

---

## Smoke checklist

| # | Check |
| --- | --- |
| 1 | `/pro/cfb/teams` 136 rows from Power SoT; warehouse fills labeled |
| 2 | `/pro/cfb/projections` loads from artifact, N=10000, research banner, no CFP% |
| 3 | `/pro/cfb/model` version strip shows power + artifact ids |
| 4 | Week 0 UNC@TCU project-game favorite agrees with SoT power order |
| 5 | `used_in_spread=false` on status / project-game / any prediction write |
| 6 | No new KEI CTAs |

---

## Recommendation

**Stop CFB product invention until 2026 opens exist.** Hist model is cold vs close (W0–1 ATS 47.7% / MAE 8.36). Lake still has **n=0** Week 0–2 books.

Do **not** start KEI or `used_in_spread=true`.

Optional later: a thin open-ingest scaffold **only after** books post Week 0 numbers we can join. Not this PR.

---

## Explicit non-goals (held)

KEI / market blend / used_in_spread flip · CFP selection · new efficiency features · live injury API · conference writers · NFL work
