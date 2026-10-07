# Neutral-site / HCA — source & identity audit (dimensional + PIT)

**Status:** research audit (Lane A)  
**Base SHA:** `4bd0f87de71d23cca8d61c980530a0902b3e8b36`  
**Does not unseal holdout. Does not score Test-A.**

## Authoritative venue / site source

| Layer | Source | Field | Role |
| --- | --- | --- | --- |
| Primary SoT for Lab joins | `services/model-service/.../ncaam_schedule/data/ncaam_official_schedule_{2022_23,2023_24}.json` | `neutral_site: bool` | Train-A / Test-A schedule packs |
| Upstream origin (documented) | ESPN public scoreboard | `neutralSite` / pack `neutral_site` | Inherited labeling |
| Holdout venue contract (foundation) | `ncaam_lab.holdout_2425.venue_contract` | `venue_status ∈ {confirmed_home, confirmed_neutral, unknown}` | Fail-closed normalization |
| Lab fair engines (pre-NEUTRAL) | `fair_b2.py`, `fair_b2_pace_v1.py` | — | **Do not consume** `neutral_site` |

**Observed:** Pack `as_of` is a pack-build timestamp (retrospective), **not** a contemporaneous game-time PIT venue stamp.

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

## Ambiguous or missing site status

| Case | Treatment under NEUTRAL candidate |
| --- | --- |
| `neutral_site` missing / null join | `venue_status=unknown` → **no fair** |
| Conflicting duplicate SoT keys | dropped → unknown if no clean join |
| Postseason home-token mismatch | `unknown` + `conflict_reason` |
| Non-boolean / malformed | refused / unknown |

## Renamed venues / relocated games

| Topic | Finding |
| --- | --- |
| Venue rename | Pack snapshot only; no historical rename graph in Lab |
| Relocated game | Inherits pack row; no secondary relocation ledger |
| Implication | Identity audit treats pack row as SoT; conflicts → unknown |

## Inputs used by proposed NEUTRAL work (dimensional + PIT)

| Input | Grain | PIT rule | Fail-closed if |
| --- | --- | --- | --- |
| KenPom AdjEM home/away | team-game | `kenpom_as_of ≤ tip_date` | missing / post-tip / non-finite |
| KenPom AdjT home/away | team-game | same | missing / ≤0 / non-finite |
| HCA | scalar | frozen | N/A (pinned 2.8696 or 0) |
| venue_status | game | SoT pack join | unknown / ambiguous |
| actual_margin (Train-A diagnostics only) | game | final scores from SoT packs via `results_attach` | missing / ambiguous |
| B1 close consensus | game | Lab frame close snapshot | non-finite (row dropped from scored set) |

**Forbidden inputs:** SETTLED / post-tip ratings; 2024–25 holdout features/labels; Test-A scoring; market-implied tempo; fitted β; national-average AdjT fallback.

## Gaps remaining OPEN

1. Independent secondary validation of ESPN neutral flags (not done this lane).
2. Contemporaneous PIT venue capture (pack as_of is retrospective).
3. Holdout venue_status distribution — **sealed; not inspected for performance**.
