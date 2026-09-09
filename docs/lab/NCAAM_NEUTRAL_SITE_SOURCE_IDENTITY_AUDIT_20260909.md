# Neutral-site / HCA — source & identity audit (dimensional + PIT)

**Status:** research audit (Lane A)  
**Base SHA:** `4bd0f87de71d23cca8d61c980530a0902b3e8b36`  
**Does not unseal holdout. Does not score Test-A.**

## Authoritative venue / site source

| Layer | Source | Field | Role |
| --- | --- | --- | --- |
| Primary SoT for Lab joins | `services/model-service/.../ncaam_schedule/data/ncaam_official_schedule_{2022_23,2023_24}.json` | `neutral_site: bool` | Train-A / Test-A schedule packs |
| Upstream origin (documented) | ESPN public scoreboard | `neutralSite` / pack `neutral_site` | Inherited labeling |
| Holdout venue contract (foundation) | `ncaam_lab.holdout_2425.venue_contract` | `venue_status ∈ {confirmed_home, confirmed_neutral, unknown}` | Fail-closed normalization (hash-pinned; not mutated) |
| Lab fair engines (pre-NEUTRAL) | `fair_b2.py`, `fair_b2_pace_v1.py` | — | **Do not consume** `neutral_site` |

**Observed pack facts (Train-A-eligible packs only):**

| Pack | n_games | `neutral_site=true` | `neutral_site=false` | missing / non-bool | `as_of` | season_type |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| 2022-23 | 5699 | 762 | 4937 | 0 / 0 | `2026-09-04T17:28Z` | regular 5586 / postseason 113 |
| 2023-24 | 3438 | 397 | 3041 | 0 / 0 | `2026-09-04T17:29Z` | regular 3438 |

**Observed:** Pack `as_of` is a pack-build timestamp (retrospective), **not** a contemporaneous game-time PIT venue stamp. Source field is `espn_scoreboard_public`. `slate_complete=false` on both packs.

## Home / away orientation

| Rule | Contract |
| --- | --- |
| Join key | `(tip_date, home_team_id=pack.home, away_team_id=pack.away)` lowercased B7 slugs |
| Fair sign | `fair_spread_home` = predicted **home** margin (positive ⇒ home favored) |
| Designated home ≠ home court | Postseason venue token mismatch vs home id → `unknown` (fail closed) |
| Ambiguous duplicate keys | Dropped entirely (fail closed) |

## Tournament / multi-team events

| Behavior | Status |
| --- | --- |
| Auto-mark tournament as neutral | **Forbidden** |
| Rely on ESPN/pack `neutral_site` | **Current** |
| Semi-home / “true home” cups | Known limitation — may be mislabeled |

Top 2022-23 `neutral_site=true` venues (count): Barclays Center 26, Orleans Arena 24, Ocean Center 23, First Horizon Coliseum 20, T-Mobile Arena 18. These are typical multi-team / early-season events — **not** independently revalidated this lane.

## Ambiguous or missing site status

| Case | Treatment under NEUTRAL candidate |
| --- | --- |
| `neutral_site` missing / null join | `venue_status=unknown` → **no fair** |
| Non-boolean / string / int flag | `unknown` (`non_boolean_neutral_site`) — **no `bool()` coercion** |
| Conflicting duplicate SoT keys | dropped → unknown if no clean join |
| Postseason home-token mismatch | `unknown` + `conflict_reason` |

## Renamed venues / relocated games

| Topic | Finding |
| --- | --- |
| Venue rename | Pack snapshot only; no historical rename graph in Lab |
| Relocated game | Inherits pack row; no secondary relocation ledger |
| Implication | Identity audit treats pack row as SoT; conflicts → unknown |

## Inputs used by proposed NEUTRAL work (dimensional + PIT)

| Input | Grain | Unit | PIT rule | Fail-closed if |
| --- | --- | --- | --- | --- |
| KenPom AdjEM home/away | team-game | pts / 100 poss | `kenpom_as_of ≤ tip_date` | missing / post-tip / non-finite |
| KenPom AdjT home/away | team-game | poss / 40 min | same | missing / ≤0 / non-finite |
| HCA | scalar | game points | frozen 2.8696 or 0.0 | unknown venue |
| venue_status | game | enum | SoT pack join (retrospective pack) | unknown / ambiguous / non-bool |
| actual_margin (Train-A diagnostics only) | game | game points | final scores via `results_attach` | missing / ambiguous |
| B1 close consensus | game | home spread (negated to margin) | Lab frame close snapshot | non-finite (row dropped from scored set) |

**Forbidden inputs:** SETTLED / post-tip ratings; 2024–25 holdout features/labels; Test-A scoring; market-implied tempo; fitted β; national-average AdjT fallback; August 31 research ratings as Week 2 KEI.

## Gaps remaining OPEN

1. Independent secondary validation of ESPN neutral flags (not done this lane).
2. Contemporaneous PIT venue capture (pack as_of is retrospective).
3. Holdout venue_status distribution — **sealed; not inspected for performance**.
4. 2023-24 pack has no postseason rows in this snapshot — late-season / NCAA tournament coverage is incomplete in the Train-A-adjacent pack.
