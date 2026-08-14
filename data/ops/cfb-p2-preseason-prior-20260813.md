# CFB P2 — 2026 preseason prior (program + roster/portal + QB σ + coaching)

**Date:** 2026-08-13  
**Branch:** `feat/cfb-p2-preseason-prior` → `deploy-vercel` (stacked on PR #233)  
**Engine:** `cfb-season-engine-v0.10-preseason-prior`  
**Prior:** `cfb-preseason-prior-v2-20260813`  
**Doctrine:** Model = research fair only. `used_in_spread` stays **false**. No KEI. No lock. Uncertainty is first-class.

Depends on P0/P1 warehouse spine. Do not claim Week 0 publish.

---

## Official 2026 FBS universe

| | |
| --- | --- |
| Source | NCAA Division I FBS program list (Wikipedia / NCAA Directory, 2026-08-13) + engine ESPN name map |
| Full members locked | **136** |
| Independents | Notre Dame, UConn |
| Wikipedia 2026 program count | 138 = 136 full + NDSU + Sacramento State (transition begins 2026, full membership 2028) |
| Transitioning | Listed, not deleted, **not** generic FCS −25. Not in the 136 prior. |
| Excluded from prior | FCS/alias junk: ACU, CHAT, IDHO, FAY, SOUTH, FAU2, OLE, OREST, TA&M, TXAM, ULL |
| Conference homes | Curated 2026 (Pac-12 rebuild approximate). Not an NCAA membership feed. |
| Official game slate | **Still no.** Schedule remains densified. This lock is the **team list**. |

File: `services/model-service/src/services/cfb_season_engine/data/cfb_fbs_universe_2026.json`

11 official FBS teams are missing from the ESPN roster pack (ARST, CSU, ECU, JVST, MIZZ, NEV, ODU, TOL, UAB, UNM, UNT). They stay in the universe with **program net + neutral roster + missing labels**. Missouri is not dropped.

---

## Formula / components

```
program_net_epa = Σ w_s * (off_epa_adj_s − def_epa_adj_s) / Σ w_s
w_s = era_mult(s) * 0.70^(Y − s − 1)     # 0 if s ≥ Y
era_mult: 2010–17=0.45, 2018–21=0.75, 2022+=1.20
program_points = program_net_epa * 28
off/def points from the same weighted EPA split when HD finals exist;
otherwise stored program net (label: stored_program_net_no_hd)

roster_points = (roster_strength − 50) * 0.12
  returning by unit = position-group experience (OL / skill / front7 / secondary)
  — not measured SNAP%. Missing unit → 50 + label.
  portal in/out = prior production × role proxies (pack). Not “N transfers = upgrade”.
  recruiting = secondary depth signal.

qb_points / qb_σ (then supporting-cast nudge):
  incumbent +1.2 / 3.4
  portal    −0.4 / 5.6
  open      −1.8 / 7.2
  freshman  −2.2 / 7.6
  unknown   −0.6 / 6.0
  cast_adj = ((OL+weapons)/2 − 50) / 50
  qb_points += 0.60 * cast_adj
  qb_σ     *= (1 − 0.12 * cast_adj)

coach: new HC −0.8 / +1.4σ; new OC −0.25 / +0.7σ; new DC −0.35 / +1.0σ
ST: (special_teams − 50) * 0.04  (approximate)

mean = program + roster + qb + coach + ST
σ    = hypot(program_σ, qb_σ, churn_σ, coach_σ, missing_roster_σ) clip [3.2, 9.5]
```

Leakage: seasons `< Y` only. 2026 PBP/results never enter. Historical walk-forward does **not** apply the 2026 roster/QB pack.

---

## QB class examples (camp SoT)

Overrides: `cfb_qb_situation_overrides_2026.json` (news → note → class). Do not invent ESPN-missing names.

| Team | Class | Pack QB1 | Public / override | σ | Notes |
| --- | --- | --- | ---: | ---: | --- |
| OSU | incumbent | — | returning starter | 4.28 | Tight blue-blood control |
| TEX | incumbent | Arch Manning | pack name real | 4.26 | |
| UGA | **open** | Ryan Puglisi | Stockton absent from ESPN — not invented | **7.40** | Camp / missing identity |
| MICH | **open** | Fowler-Nicolosi | Underwood absent — not invented | **7.46** | |
| FSU | **open** | DeNobile heuristic | Ashton Daniels (ESPN-present, unconfirmed) | **7.59** | |
| LSU | **open** | Clark heuristic | Sam Leavitt (ESPN-present, unconfirmed) | **7.39** | |
| ALA | open | Austin Mack | Mack vs Russell camp | 7.31 | |
| ORE | portal | — | portal QB | 6.06 | Wider than incumbent, tighter than open |
| BALL | open | — | G5 rebuild | 7.69 | |
| MIZZ | unknown | — | **roster pack missing** | 6.84 | Neutral roster + labels |

Veteran returning ≠ freshman/open σ. UGA/MICH/FSU/LSU are no longer fake incumbents at 4.3σ.

---

## Walk-forward before / after (W0–1)

| | ATS | MAE | n |
| --- | ---: | ---: | ---: |
| P0 baseline | 47.7% | 8.36 | 439 |
| P2 re-run (HD, program prior only) | **47.71%** | **8.362** | 415 ATS / 439 close |

**Flat.** Diagnosis: 2026 roster/QB/coaching cannot be applied to 2020–25 without leaking a future overlay. Program EPA weights were not retuned in-sample. Overall 2020–25 ATS 50.3% / MAE 7.48 is still a coin flip vs close.

`used_in_spread` stays false. Do not publish KEI.

---

## Integration

- Project-game attaches `research_prior` (mean ± σ) and writes an **immutable** `model_predictions` row (`model_version` + `as_of` + `game_id`). Injury = new `as_of`, never UPDATE.
- Status `GET /cfb/season-engine/status` returns **200** with `cfb-season-engine-v0.10-preseason-prior` even if universe load fails (degraded payload + error).
- Edge Board CFB unchanged (markets-only). No fake KEI.
- UI: research prior card on `/pro/cfb/project-game`.

## Rebuild

```bash
python scripts/cfb/rebuild_preseason_prior_p2.py
python scripts/cfb/rebuild_preseason_prior_p2.py --from-hd   # if HD season finals mounted
python scripts/cfb/run_p2_walkforward_compare.py
```

---

## Remaining blockers to `used_in_spread` / Week 0 publish

1. Walk-forward W0–1 still fails ATS (~47.7%). Need a closer, not a ranking prior.
2. Official **2026 FBS slate** (densified ≠ product schedule).
3. Roster-pack holes (MIZZ + 10). Missing ≠ silent 0, but DNA is thin.
4. Camp QB still open for UGA/MICH (names absent from ESPN). FSU/LSU unconfirmed.
5. Release gate + pin (P5). No CFB lock tag.
6. Separate totals model / game-distribution sim (P3).
7. KEI only after a trustworthy pure fair exists.

**Ready for P3 brief (game/total sim distributions): yes**, as research. Not ready to publish lines.

## Honesty

- Not lock quality.
- Rank ≠ market.
- PASS > invented PLAY.
- FCS games kept in history; transitioning teams labeled.
