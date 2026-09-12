# CFB 11-team priors repair — W2 vs frozen W0

Verdict: **PASS with remaining blockers.** Do not merge #532.

## Root cause

**Universe construction** (primary). `cfb_fbs_team_priors_2026.json` was keyed off a stale 136-code set plus FCS/alias extras (`ACU`, `CHAT`, `FAU2`, `OLE`, …), not `cfb_fbs_universe_2026.json`. Missouri (`MIZZ`, SEC) was omitted while Missouri State (`MOST`, CUSA) stayed. Alias/code mapping (Missouri vs Missouri State; ESPN abbr ≠ engine code) was a contributing historical cause. Source SP+ rows were never missing.

Jacksonville State (`JVST`): official lock is `fbs_full` / CUSA (FBS since 2023). Not a 2026 transition. Transitioning 2026 programs are NDSU and Sacramento State — roster snapshot only, no generic −25, no league-average efficiency.

## Rebuild

1. Priors package: official 136 full members, extras pruned, NDSU/SAC snapshot-only.
2. `package_efficiency_2025_carry.py`: official lock, fail-closed on unmapped official FBS. ESPN story HTML parses 87 rows (skipped). Complete public 2025 final table maps all 136.
3. `package_power_sot_and_projections.py`: research-desk remint (`POWER_AS_OF=2026-08-14`).
4. KEI-only with `CFB_CLOSE_AS_OF=2026-09-10` → `cfb-kei-v1.0-2026w2`.

No `MATCHUP_RESPONSE` / `LEAGUE_TEAM_PPG` / other coefficient edits. No 50-fills. No header-only stamp change.

## Gates

| Gate | Result |
| --- | --- |
| All 11 have mapped SP+ rows | PASS |
| All official FBS have finite offense/power | PASS |
| 2026 conferences (MIZZ SEC, CSU Pac-12, JVST CUSA, …) | PASS |
| Independents only ND + CONN | PASS |
| No league-average fills (incl. M-OH) | PASS |
| No header-only W2 timestamp repair | PASS |
| No model coefficient changes | PASS |
| #532 not merged | PASS |

## What changed because of the repaired population

Frozen W0 (`0a8032b1c`): `as_of=2026-08-31`, `cfb-kei-v1.0-2026w0`, 97 games.

New W2: `as_of=2026-09-10`, `cfb-kei-v1.0-2026w2`, 183 games (86 added Week-2 / remaining Week-1 rows). All 97 W0 games retained.

FBS-vs-FBS games among the 11 that exist in both packs (8) all moved. Largest W0→W2 model-spread moves on those games:

| Game | W0 model / KEI | New model / KEI |
| --- | --- | --- |
| WKU @ NEV | +8.03 / +9.03 | −3.13 / −3.81 |
| CMU @ UNM | −5.44 / −5.84 | −21.41 / −22.61 |
| UNT @ IU | −31.92 / −33.12 | −22.33 / −23.53 |
| WYO @ CSU | +2.04 / +2.68 | −5.81 / −6.17 |
| UAB @ ILL | −24.41 / −25.61 | −20.81 / −22.01 |

Power SoT vs the pre-repair #536 pack (the 11 were already spliced there):

| Team | Δ offense | Δ power | Note |
| --- | --- | --- | --- |
| UNT | −0.306 | −0.217 | live public SP+ vs ESPN-story splice |
| ODU | −0.145 | −0.090 | |
| ECU | −0.138 | −0.118 | |
| NEV | +0.125 | +0.065 | |
| M-OH | −0.121 | −0.078 | **was `league_average_fill` / 50** |
| TOL | −0.099 | −0.117 | |
| UNM | +0.053 | +0.043 | |
| CSU | +0.043 | +0.065 | |
| UAB | −0.037 | −0.006 | |
| ARST | −0.026 | −0.039 | |
| MIZZ | +0.022 | −0.012 | distinct from MOST |
| JVST | −0.016 | −0.004 | real SP+ rank 91, not a 50-fill |

A complete official-universe rebuild also retunes league z-scores (147-code snapshot with extras → 136 official). Every FBS-vs-FBS KEI line vs #536 moved; max |Δ KEI spread| = 17.88. That is not isolated to the 11.

## Remaining blockers

1. ESPN final-2025 story HTML is incomplete (87/136). Packager skips it rather than shipping a partial table.
2. Live public 2025 final SP+ ≠ the #536 ESPN-story splice. The 11 now have honest mapped rows; vintage is the complete public table.
3. Power SoT remint used research `2026-08-14` stamps and replaced the week0-close (`2026-08-31`) canary artifact id. Not a W2 header hack — call out before treating this remint as the close pack.
4. NDSU / Sacramento State have no 2025 FBS SP+. Documented transition; snapshot only.
5. Public Edge Board kill switch stays off.
6. Do not merge #532.
