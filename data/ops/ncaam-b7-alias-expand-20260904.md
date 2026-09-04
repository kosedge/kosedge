# NCAAM B7 alias expand — map_miss cut (#14 CONTINUE GO) — 2026-09-04

**Scope:** Fail-closed ESPN Schedule SoT → B7 `team_id` alias coverage toward D1.
**Base:** `deploy-vercel` @ `198cc7df` (scorecard v1) + ESPN SoT A.
**Not in scope:** Edge Board / PLAY / Odds densify / scorecard retune / fuzzy invent / KenPom-as-SoT / #12 GO-2.

## Paths

| Piece | Path |
| ----- | ---- |
| Alias SoT | `apps/web/lib/ncaam/aliases.json` |
| TS identity | `apps/web/lib/ncaam/identity.ts` |
| Python twin | `apps/web/src/ncaam_identity.py` |
| ESPN→B7 map | `apps/web/src/ncaam_espn_schedule_map.py` |
| College directory | `apps/web/lib/team-research/directories-college.ts` (`NCAAM_TEAM_DIRECTORY`) |
| Packs | `services/model-service/.../ncaam_schedule/data/ncaam_official_schedule_{2022_23,2023_24}.json` |
| Ingest | `scripts/ncaam/ingest_espn_official_schedule.py` |

## Before → after (map_miss_rate)

Event miss = ESPN event with ≥1 unmapped/ambiguous side (fail-closed omit).

| Pack | Window | ESPN events | Before miss | After miss | Mapped both (before → after) |
| ---- | ------ | ----------- | ----------- | ---------- | ---------------------------- |
| 2022-23 | 2022-11-01 → 2023-04-10 | 6261 | **79.2%** (4961 omit) | **9.0%** (562 omit) | 1300 → **5699** |
| 2023-24 | 2023-11-01 → 2024-01-28 | 3954 | **83.3%** (3294 omit) | **13.1%** (516 omit) | 660 → **3438** |

`slate_complete` remains **false** — residual misses are mostly non-D1 / exhibition / transition opponents (correct omit), not invent.

## Coverage grain

- `aliases.json`: ~1127 folded aliases → **~365 unique** KenPom-clean `team_id`s (was ~125 / 326 alias keys).
- Directory: **~360** unique NCAAM slugs (was ~110+); no bare `miami` slug.
- Source: ESPN public teams list + KenPom `power_ratings_ncaam` norms; **no fuzzy / first-token invent**.

## Homonyms (P0 — fail-closed)

| Alias | Result |
| ----- | ------ |
| `Miami Hurricanes` | `miami fl` |
| `Miami (OH) RedHawks` | `miami oh` |
| bare `miami` / `miami university` / `miami redhawks` | **omit** |
| bare `loyola` | **omit** (Chi / LMU / MD stay explicit) |
| bare `southern` | **omit** (Southern U / Southern Miss / SIU stay explicit) |

Pack receipt: miami_fl ≠ miami_oh on both remats (2022-23: 37 vs 29 mapped games; 2023-24: 20 vs 18).

## Residual top misses (honest)

After expand, top unresolved names are **non-D1 exhibitions** or departed programs (e.g. St. Francis Brooklyn, Hartford, Champion Christian, Bethesda). Left **unmapped** on purpose.

## Refresh

```bash
python scripts/ncaam/ingest_espn_official_schedule.py --season 2022-23
python scripts/ncaam/ingest_espn_official_schedule.py --season 2023-24 --end-date 2024-01-28
```

## Explicit non-goals (HOLD)

- Edge Board populate / PLAY / Conf% / props
- Odds densify / invent tips
- Scorecard v1 retune
- Claiming `slate_complete=true` on residual non-D1 gaps
