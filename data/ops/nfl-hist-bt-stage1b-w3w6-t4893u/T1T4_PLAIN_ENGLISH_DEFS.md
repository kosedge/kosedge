# T1–T4 plain-English definitions + derivation (pre-eng attach)
Source: ALEX_T1T5_FIELD_MAP_SOURCE_PROPOSAL_t4890u_v1.md (paper sha8 3bdb29ba) · contract pin b41f4b43
OWNER t4893u: attach before execution; reconstruct b41f4b43 as written; substitute/contract change → escalate Ryan.

W2 defs file sha256 `019ee35b…` is the field-definition SoT. This copy adds only the W3–W6 coverage target. Field text is unchanged.

## As-of (cf514078)
Only games with kickoff_utc strictly < target kickoff. rating_week = target_week − 1. Week 1 has no same-season rating week (raises; no substitute). Pre-kickoff information only. No invented fills.

## Lineage
T1 = nfl_dp_team_situational_weekly (one row per team per played game, from PBP)
T2 = per-season rolling window ROWS BETWEEN 4 PRECEDING AND CURRENT ROW (≤5 games, same season only)
T3 = home/away side rollups
T4 = home-minus-away matchup diffs

## T1–T4 fields (16) — plain English
| key | plain English | units |
|---|---|---|
| home_off_epa_5g / away_off_epa_5g | team's average offensive EPA per play, last ≤5 games | EPA/play |
| home_def_epa_allowed_5g / away_def_epa_allowed_5g | EPA per play the defense allowed, last ≤5 | EPA/play |
| home_pass_rate_5g / away_pass_rate_5g | share of offensive plays that were passes (dropbacks) | fraction 0–1 |
| home_success_offense_5g / away_success_offense_5g | share of offensive plays with EPA>0 | fraction 0–1 |
| home_success_defense_allowed_5g / away_success_defense_allowed_5g | success rate allowed by defense | fraction 0–1 |
| matchup_diff_off_epa_5g | home off EPA − away off EPA | EPA/play |
| matchup_diff_def_epa_allowed_5g | home def EPA allowed − away def EPA allowed | EPA/play |
| matchup_diff_success_rate_5g | two-term mean of (off-success edge, def-success edge) | fraction diff |
| matchup_diff_pressure_generated_5g | home − away pass-rush pressure created | rate diff |
| matchup_diff_pressure_allowed_5g | home − away pressure allowed by offense | rate diff |
| matchup_diff_red_zone_td_rate_5g | home − away share of RZ trips (inside opp 20) ending in TD | rate diff |

SQL governs where this paraphrase disagrees (Alex W2 RO: contract/SQL signs; play-based RZ). Pressure = (sack OR qb_hit)/pass. RZ = yardline_100<=20 plays.

## Expected complete-game coverage (W3–W6)

- Declared sample: 2017 REG Weeks 3–6, excluding any game where either side has 0 completed same-season games as-of kickoff.
- Source N: 16+16+14+14 = 60. Eligible N target: **60** (Irma TB/MIA completed W2).
- Complete eligible game = all 27 required fields DERIVED_PREGAME with source sha + kickoff cutoff cited; zero defaults/fills.
- Pressure + RZ: match contract text b41f4b43 / T1 SQL. Do not substitute trips or qb_dropback denominator.
- W5-bye T2 exact-week miss: preserve as MISSING (no last-played fill).

## W2 lineage (accepted method)

W2 first: N=14/16, selection_hash `96a13176…`, 14/14 × 27/27, Alex PASS_RECON `91e2d7db` @ tip `440314e4`.

## Acceptance for W3–W6 eng (Alex RO next)

(a) selection_hash(es) sealed pre-build (per-week + combined)
(b) complete-game coverage reported (eligible games with 27/27 DERIVED vs partial)
(c) every cell cites source sha + cutoff; leakage test: no consumed play with kickoff ≥ target
(d) T1 transform reused from W2 or fail-closed MISSING
(e) pressure/RZ matched to contract OR left MISSING + escalate
(f) exclusions listed with fixed rule
(g) no 2023+/2024–25 rows; no scoring/fit/tune
(h) Alex RO before any extend beyond W6
(i) Credits 0 · ≠score ≠fit ≠tune ≠IF invoke ≠Odds ≠Stage-2 ≠admit ≠CERT
