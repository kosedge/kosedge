# CFB 2025 efficiency source-vintage repair

Verdict: **PASS on source-vintage / provenance. Do not merge #532.** Public CFB/Edge Board kill switch stays OFF.

The 11-team universe repair in #547 is left closed. This pass fixes blockers 1–3 from that report: the ESPN 87/136 parse, live-public ≠ #536, and the overwritten W0 canary.

## Authoritative 2025 efficiency source and vintage

| Field | Value |
| --- | --- |
| Source | ESPN story 46128861, Bill Connelly |
| Title | 2025 college football SP+ rankings for all 136 FBS teams |
| URL | https://www.espn.com/college-football/story/_/id/46128861/2025-college-football-sp+-rankings-all-136-fbs-teams |
| Published | 2026-01-20 (`DC.date.issued`) |
| Vintage | `espn_story_2025_final` |
| Legal at model as-of | 2026-08-31 (W0 close) |
| Committed table | `cfb_sp_plus_final_2025_espn_story.json` |
| Coverage | **136 / 136** official 2026 full-member FBS |
| Unresolved / missing | **none** among official 136 |
| Transitions excluded | NDSU, Sacramento State (no 2025 FBS SP+; snapshot-only; no −25 / no 50-fill) |
| Row-level provenance | **136 / 136** (`source_vintage`, `source_published`, `source_url`, `source_table_name`) |

What the 2026 preseason / W0 model **actually used** (commit `69b971154`, packaged 2026-08-05 as `final_2025_sp_plus_public_table` from cfbupdate): a 136-key stale-universe snapshot with 130 mapped SP+ rows, 6 `league_average_fill` (including M-OH), and the 11 official codes absent. That scrape is the same *family* as the ESPN final (median \|Δ SP+\| = 0.1) but is **not** bit-identical and is no longer recoverable from live cfbupdate.

The recoverable complete year-locked publication is the ESPN story. It was public on 2026-01-20, so it was legal at W0. This remint uses **only** that table. It does not splice, does not mix frozen cfbupdate norms with ESPN rows, and does not read live cfbupdate.

## Why the ESPN parser yielded 87/136

The HTML is complete. Two `<table>` blocks are present (final SP+ ratings; résumé SP+). The ratings table has 136 data rows, ranks 1–136, no missing ranks.

The packager dropped 49 rows because ESPN uses abbreviated display names that were not in `NAME_TO_CODE`:

`Ohio St.`, `Penn St.`, `Ga. Tech`, `N. Carolina`, `Miami-OH`, `Coastal Caro.`, `J'ville St.` was already mapped, but `Ohio St.` was not.

Those 49 names are now `ESPN_FINAL_2025_STORY_NAME_TO_CODE`. After the map: 86 `name_to_code` + 49 abbreviations + 1 Miami collision = **136**. Unmapped ESPN names now fail closed instead of disappearing.

This was a name-mapping bug, not a truncated story and not missing source data.

## Why live public 2025 SP+ ≠ the #536 ESPN-story splice

Live `cfbupdate.com/sp-ratings` is the **2026 in-season board**, not final-2025.

Evidence from this run:

- Records are 0–2 games (`Ohio State (1-0)`, `Miami (2-0)`). 138 rows match `[0-2]-[0-2]`.
- TCU 3.9 / UNC +5.8 / Indiana 24.1 rank 6.
- ESPN final-2025: TCU 8.3 / UNC −6.6 / Indiana 32.4 rank 1.
- Frozen W0 / #536: TCU 8.5 / UNC −6.8.

#532 already rejected a live cfbupdate rematerialize for this reason (TCU 8.5→3.9). #547 then accepted the same live board because it was the first candidate that mapped all 136 official codes after the ESPN parse returned 87. That was vintage substitution to obtain coverage.

| Pair | n overlap | n differ | mean \|Δ SP+\| | max |
| --- | ---: | ---: | ---: | --- |
| W0 frozen vs ESPN story | 125 | 88 | 0.30 | ORE 29.3 vs 25.9 (3.4) |
| #536 vs ESPN story | 136 | 88 | 0.30 | same ORE 3.4 |
| #536 vs W0 | 136 | 0 | 0 | P0 splice only |
| #547 live vs ESPN story | 136 | 135 | 5.99 | UNT −13.2 vs 13.8 (27.0) |

W0 / #536 / ESPN are one 2025-final family (median 0.1, a few revisions). #547 is a different season.

## What was rematerialized

One chain, no coefficient edits:

1. Priors — official 136, unchanged from the #547 universe repair.
2. Efficiency — committed ESPN 2025-final table, ESPN-only z-score norms (`μ_off=27.1581`, `μ_def=26.4596`).
3. Power SoT + projections — `--stamps week0-close` (`2026-08-31`, `cfb-power-sot-v0.15-week0-close-20260831`).
4. KEI-only — `CFB_CLOSE_AS_OF=2026-09-10` → `cfb-kei-v1.0-2026w2`.

Live public and `--splice-p0-only` now hard-fail. Futures left on the existing week0-close `as_of=2026-08-31` (not reminted).

## W0 canary preserved

`data/ops/cfb-w0-canary-20260831/` is the immutable reference. Working packs no longer *are* the canary; they must not overwrite it.

| File | From | Check |
| --- | --- | --- |
| `cfb_season_projections_2026.json` | #536 week0-close | USF E[wins] **8.382**, OSU 9.537, UTAH 9.634, USF std < OSU std |
| `cfb_power_sot_2026.json` | #536 `power_as_of=2026-08-31` | SHA locked in `MANIFEST.json` |
| `cfb_kei_w0_w1_2026.json` | `0a8032b1c` original W0 | `cfb-kei-v1.0-2026w0`, `as_of=2026-08-31` |
| `cfb_efficiency_snapshot_2025_carry_2026.json` | `69b971154` | the scrape W0 actually used |

Working remint USF E[wins] is **9.348**. That is expected: a new close-stamped remint from the ESPN table, not a reprint of the canary. Enterprise canary tests now read the canary directory.

## Power SoT / KEI comparison

Model-spread attribution (home-signed). KEI is nested; W0 canary rows often have no top-level `kei_spread_home`.

### NEW (ESPN year-lock) vs #536 (frozen + P0 splice)

Same 2025 family. 96/183 model lines moved. mean \|Δ\| = **0.18**, max = **1.26** (BC@CIN). One sign flip (UTSA@TXST +0.34 → −0.76). The 11 P0 power rows stay within ~0.002 of #536 except **M-OH** (−0.041): #536 still had `league_average_fill` / 50; ESPN has Miami-OH −3.4, rank 82.

Giant #547 moves were **not** the 11-team repair. They were 2026 in-season SP+.

### NEW vs #547 (live 2026 board)

96/183 moved. mean \|Δ\| = **4.78**, max = **16.42**, **16 sign flips**.

| Game | W0 | #536 | #547 live | NEW ESPN |
| --- | ---: | ---: | ---: | ---: |
| WKU @ NEV | +8.03 | +7.77 | **−3.13** | +7.85 |
| CMU @ UNM | −5.44 | −13.15 | **−21.41** | −13.12 |
| UNT @ IU | −31.92 | −13.67 | **−22.33** | −13.73 |
| WYO @ CSU | +2.04 | −0.13 | **−5.81** | −0.03 |
| UAB @ ILL | −24.41 | −21.99 | −20.81 | −22.11 |
| UNC @ TCU | −19.19 | −15.14 | **−5.57** | −14.93 |
| MIZZ @ KU | — | +1.10 | −2.19 | +1.24 |

NEW KEI on those games: WKU@NEV +8.85; CMU@UNM −14.32; UNT@IU −14.93; WYO@CSU −1.08; UNC@TCU −16.13.

### NEW vs W0 canary (97 common games)

49 moved, 3 sign flips, max **+18.19** (UNT@IU −31.92 → −13.73). That is the honest 11-team + M-OH effect plus the small ESPN-vs-frozen copy difference. UNT/TOL/UNM/ECU were null/1.0 or missing in W0.

P0 power (NEW): MIZZ 1.2342 SEC, UNT 1.3117 AAC, JVST 1.0563 CUSA, M-OH 1.0147 MAC. No Independent except ND/CONN. No 50-fills.

## NDSU / Sacramento State

Documented 2026 transitions. Absent from the ESPN 2025 136, absent from the efficiency snapshot, absent from priors. Roster snapshot only. No generic −25, no league-average efficiency.

## Gates

| Gate | Result |
| --- | --- |
| Authoritative source identified and committed | PASS |
| Coverage 136/136 official | PASS |
| Unresolved official teams | none |
| Row-level provenance 136/136 | PASS |
| 87/136 explained (abbreviations, not truncated HTML) | PASS |
| #536 vs live public explained (2025 final vs 2026 in-season) | PASS |
| Live public rejected as 2025 carry | PASS |
| No silent vintage mix / no splice remint | PASS |
| W0 canary preserved (USF 8.382) | PASS |
| Working remint week0-close stamps, not 2026-08-14 | PASS |
| No league-average fills | PASS |
| NDSU/SAC transition policy | PASS |
| No coefficient changes | PASS |
| Kill switch OFF | PASS |
| #532 unmerged | PASS |

## PASS/FAIL for #532

**FAIL — do not merge #532.** Source-vintage is now clean enough to *judge* the rematerialized numbers. It is not a public-reactivation pack.

Remaining blockers before any public CFB merge:

1. Market residual / totals identity still unvalidated on this vintage (do not haircut).
2. Working remint ≠ original W0 canary (documented; canary kept).
3. Public Edge Board kill switch stays OFF.
4. Do not merge #532.

Tests: `test_cfb_name_to_code_fail_closed.py` `test_cfb_priors_official_universe.py` `test_cfb_efficiency_source_vintage.py` `test_cfb_enterprise_gates.py` `test_cfb_real_roster.py` `test_cfb_power_sot.py` — 48 passed.
