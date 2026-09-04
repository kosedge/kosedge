# NCAAM identity — B7 acceptance (#14 Phase E) — 2026-09-04

**Scope:** Identity build slice only. No fair remat, no Edge Board populate, no props/PLAY/Conf%.

**Canonical sport key:** `ncaam` only. `cbb` / `ncaab` retired as API/DB sport keys.

## Artifacts

| Piece             | Path                                                                      |
| ----------------- | ------------------------------------------------------------------------- |
| Alias SoT         | `apps/web/lib/ncaam/aliases.json`                                         |
| TS identity       | `apps/web/lib/ncaam/identity.ts` (`resolveTeamId`, fail-closed)           |
| Python twin       | `apps/web/src/ncaam_identity.py` (`odds_name_to_team_norm`)               |
| B7 sample fixture | `apps/web/lib/ncaam/b7-odds-sample.json` (≥50 odds names)                 |
| Unit tests        | `apps/web/__tests__/lib/ncaam-identity-b7.test.ts`                        |
| Directory         | `apps/web/lib/team-research/directories-college.ts` — Miami FL + Miami OH |

## B7 results

| #    | Criterion                                               | Status                                             | Receipt                                                                                                                                                                       |
| ---- | ------------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B7.1 | Miami FL vs Miami OH never collapse                     | **PASS**                                           | Odds `Miami Hurricanes` → `miami fl`; `Miami (OH) RedHawks` → `miami oh`; bare `miami` → **omit**. Directory: `miami-fl` (ACC) ≠ `miami-oh` (MAC).                            |
| B7.2 | ≥50 odds names → unique team_id OR explicit omit        | **PASS**                                           | `b7-odds-sample.json` has 55 resolve rows with unique team_ids + explicit omit rows for bare Miami.                                                                           |
| B7.3 | Zero production publish paths call `odds_team_to_short` | **PASS**                                           | Cutover: `project_future_kei_lines.py`, `merge_games_ensemble.py`, `build_schedule_from_odds.py`, `build_actual_margins.py`, `join_and_backtest.py`. Source-lock in B7 tests. |
| B7.4 | Assemble/API reject `sport=cbb`                         | **PASS**                                           | Assemble returns **400** `Retired sport key` / `use: "ncaam"` via `isRetiredNcaamSportKey`. Prisma Sport comments no longer say `cbb`.                                        |
| B7.5 | Named **Schedule SoT** for future game_id joins         | **DATA GAP** (documented; does not block identity) | See below.                                                                                                                                                                    |

## Schedule SoT (B7.5) — cite / gap

**CFB (exists):** ESPN team-schedule SoT — `official_schedule.py` / packaged `cfb_official_schedule_2026.json` (game_id + names).

**NFL (exists):** Canonical schedule JSON + ops notes under `data/ops/nfl-canonical-schedule-*`.

**NCAAM (gap):** There is **no** named Schedule SoT with stable `game_id` for warehouse joins.

Closest today (not a Schedule SoT):

- Odds-derived schedule grain: `apps/web/src/build_schedule_from_odds.py` → `event_id` + `game_date` + `home_team_norm` / `away_team_norm`
- Methodology join key (date + normalized teams): `docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md`

**Do not invent** a schedule system in this identity PR. Future game_id joins need an explicit NCAAM Schedule SoT decision (ESPN / NCAA / SportsData / Odds event_id promotion) before publish-on-schedule.

## Hard rules locked in this slice

- Fail-closed: unknown or ambiguous alias → omit from publish join (no fuzzy auto-publish).
- No first-token / `odds_team_to_short` shortening on production publish paths.
- `ratings_norm_bridge` maps clean ids → inherited KenPom `normalize_team` bugs (`nc state` → `nc stateate`) so joins work **without** fair remat.

## Explicit non-goals (HOLD)

- Fair remat / KEI JSON refresh as progress
- Edge Board populate / KenPom-sharp board
- Props / PLAY / Conf%
- Wholesale CBB model engine
