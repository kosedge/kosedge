# NFL Depth + Coaching: One Source of Truth — 2026-08-08

Branch: `feat/nfl-depth-coaching-sot` → `deploy-vercel` (+ Railway model-service).

## Goal

One packaged 2026 depth + coaching book feeds season engine (usage / boxes /
injury paths), team intel (Depth Chart, Roster Pulse, Coaching staff), and True
PR continuity / QB context. No false “pending” / “still populating” when the
pack already has rows.

## Sources

| Artifact | Path | Role |
|----------|------|------|
| **Depth pack** | `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json` | `packaged_nflverse_depth_2026` — skill QB/RB/WR/TE depth 1–3 |
| **Coaching pack** | `services/model-service/src/services/nfl_season_engine/data/nfl_coaching_staff_2026.json` | `packaged_nfl_coaching_staff_2026` — HC / OC / DC + continuity flags |
| **Loader** | `nfl_season_engine/loaders.py` → `load_packaged_depth_chart` | Engine universe |
| **Staff module** | `nfl_season_engine/coaching_staff.py` | Intel rows + continuity staff map |
| **Intel APIs** | `GET /nfl/intel/depth-charts`, `/rosters`, **`/coaching`** | DB first; empty/unavailable → packaged depth; coaching is pack-primary |

## Coverage counts (2026-08-08)

| Surface | Count |
|---------|------:|
| Depth teams with skill rows | **32 / 32** |
| Depth skill rows (QB/RB/WR/TE ≤3) | **383** |
| Coaching teams with named HC | **32 / 32** |
| Coaching teams with HC+OC+DC | **31 / 32** |
| Thin DC (honest unknown) | **TB** |
| Missing coaching teams | **0** |

Continuity flags: `new=true/false` only when change is known; `null` = unknown
(never defaulted to “new staff”).

## Smoke — ARI / KC / SF

| Team | Depth QB1 | HC | OC | DC | Continuity |
|------|-----------|----|----|----|------------|
| **ARI** | Jacoby Brissett | Mike LaFleur | Nathaniel Hackett | Nick Rallis | new HC+OC |
| **KC** | Patrick Mahomes | Andy Reid | Eric Bieniemy | Steve Spagnuolo | returning HC; new OC |
| **SF** | Brock Purdy | Kyle Shanahan | Klay Kubiak | Raheem Morris | returning HC; new OC/DC |

Spot-check also clean for MIA / LV (named QB1 + full HC/OC/DC).

Engine alignment: `resolve_season_universe` / game-boxes read the same depth pack;
ARI QB1 in boxes matches Depth Chart / Roster Pulse (`Brissett`).

## Product wiring

- Team hub Overview: Roster Pulse + Coaching staff from shared pack APIs
- Depth Chart view: packaged fallback when weekly DB empty
- Research filters: full **32-team** directory; path team selected on `/teams/{code}`
- Sport-config NFL coaching section: `live` (no hard-coded pending)
- Continuity score: staff factors from packaged book (curated map backfill only)

## Remaining holes

1. **TB DC** — name unknown in pack → UI labels Unknown / Thin (not invented)
2. Some OC/DC **continuity flags** still `null` (HOU/IND/NE/NO/…) — names shown, continuity approximate
3. Depth pack is **skill-only** (no OL/DL/ST) — intentional for engine usage path
4. Weekly injury report still DB-dependent (non-goal for this pass)
5. Standings / situational stats remain separate intel tables (not part of depth SoT)

## Tests

`services/model-service/tests/test_nfl_depth_coaching_sot.py` — pack coverage,
ARI/KC/SF coaching, roster pulse, ARI game-box QB1 alignment.
