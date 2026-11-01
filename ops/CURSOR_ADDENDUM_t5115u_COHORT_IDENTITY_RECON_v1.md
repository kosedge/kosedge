# CURSOR ADDENDUM t5115u — EVAL cohort pin + 2020 identity recon

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER t5115u · CoS STOP-IF-UNCLAIMED · CLEAR 61906c87 G2
**t5114u EXEC STOPPED. No claim. No outcome join. No metrics. Not a scored look.**

## Gate

| Check                         | Result                                                                 |
| ----------------------------- | ---------------------------------------------------------------------- |
| #691 HEAD at stop             | `931a532c698b3034f840bf719ed5b90da325f6ad`                             |
| `ONE_RUN.json`                | **absent**                                                             |
| claim file                    | **absent**                                                             |
| result receipt                | **absent**                                                             |
| outcome join / MAE / bootstrap | **not run**                                                            |
| DEV pooled into EVAL metrics  | **no** (no metrics computed; runner now refuses that default)          |
| t5114u EXEC                   | **STOPPED_UNCLAIMED** — prior CoS bind remains on record; not consumed |

Ordinary failure ≠ another look. No second bind. No restart.

## A. Metric-specific EVAL cohort (explicit; never all 892)

Full freeze `FORECAST_FREEZE_t5112u.json` (`9e704b98…`) stays sealed: forecast `f326a39a…` / cohort `af129383…` / n=892. That file is **not** an EVAL accuracy cohort.

| Pin            | Split | Seasons    | n         | cohort_sha256                                                      |
| -------------- | ----- | ---------- | --------- | ------------------------------------------------------------------ |
| **EVAL metric** | EVAL  | 2022–23 REG | **449** (221+228) | `fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0` |
| **DEV retain** | DEV   | 2020–21     | **443** (216+227) | `f240fde23025d7584a5f8031ec1e0e74f902be1100ce1630aca4f2f20ed326b0` |

`run_eval_score` now refuses **before claim** if a mixed DEV+EVAL freeze is scored with no `eligible_cohorts`, or if the eligible set pools 2020–21 into 2022–23. Synthetic single-split tests unchanged.

File: `data/ops/nfl-forecast-builder-t5107u/METRIC_COHORTS_t5115u.json`

## B. Quote eligibility + G5 HOLD before metrics (bound, not executed)

Order required on any later authorized EXEC (Alex verify + CoS re-clear; same look, not a second look):

1. Use the **EVAL 449** pin as the metric universe (not 892).
2. Apply owned-quote eligibility from quote manifest `6a1c1b37…` (KO−60, ≤24h, DK/FD).
3. Re-apply existing **30% per-season HOLD** on the **declared PBP REG** universe.
4. Only then join outcomes / compute metrics.

Quote eligibility was **not** applied this turn (EXEC stopped). HOLD on recon exclusions vs declared REG:

| Season | Declared PBP REG | Recon excl+partial | Rate   | HOLD>30% |
| ------ | ---------------- | ------------------ | ------ | -------- |
| 2020   | **256**          | 16+30=46           | 17.97% | no       |
| 2021   | 272              | 16+29=45           | 16.54% | no       |
| 2022   | 271              | 18+32=50           | 18.45% | no       |
| 2023   | 272              | 16+28=44           | 16.18% | no       |

No criteria change. No subset waiver. HOLD denominator is PBP REG, not the week≤18 pin filter.

## C. 2020 identity: 262 vs 256

Exact rule used by `load_games_identity`: games.csv **4fe1cdd7** · season∈{2020–23} · **week 1–18** · require `kickoff_utc`. That filter is **not** the declared REG universe.

| Source                         | 2020 n | Notes                                      |
| ------------------------------ | ------ | ------------------------------------------ |
| PBP REG (`INPUT_BINDINGS`)     | **256** | publisher `a7700b51…`; extract `08533423…` |
| games.csv week 1–18            | **262** | no duplicate `game_id`; no duplicate (week,home,away) |
| PBP − pin                      | **0**   | every 2020 REG id is on the pin            |
| pin − PBP                      | **6**   | week 18 only                               |

The six extras are **2020-21 Wild Card** (9–11 Jan 2021), not extra REG games and not a universe rewrite:

| game_id           | home | away | kickoff_utc           | nflverse_gameday | class              |
| ----------------- | ---- | ---- | --------------------- | ---------------- | ------------------ |
| `2020_18_IND_BUF` | BUF  | IND  | 2021-01-09T18:05:00Z  | 2021-01-09       | NON_REG_WILDCARD   |
| `2020_18_LA_SEA`  | SEA  | LAR  | 2021-01-09T21:40:00Z  | 2021-01-09       | NON_REG_WILDCARD   |
| `2020_18_TB_WAS`  | WSH  | TB   | 2021-01-10T01:15:00Z  | 2021-01-09       | NON_REG_WILDCARD   |
| `2020_18_BAL_TEN` | TEN  | BAL  | 2021-01-10T18:05:00Z  | 2021-01-10       | NON_REG_WILDCARD   |
| `2020_18_CHI_NO`  | NO   | CHI  | 2021-01-10T21:40:00Z  | 2021-01-10       | NON_REG_WILDCARD   |
| `2020_18_CLE_PIT` | PIT  | CLE  | 2021-01-11T01:15:00Z  | 2021-01-10       | NON_REG_WILDCARD   |

2020 REG ended week 17 (16 games). `CLE@PIT` and `LAR@SEA` also exist as week-6 / week-16 **REG** rows — rematches, not duplicate schedule identities.

Preserved, not dropped:

- 16 W1 excluded (`W1_NO_PRIOR`) stay excluded.
- 30 2020 partials stay fail-closed.
- 6 Wild Card rows stay in the **DEV freeze** (216 = 210 REG complete + 6 WC) and are **outside** declared 256 and **outside** EVAL 449.

2021/22/23 pin week 1–18 **equals** PBP REG (272 / 271 / 272). 2022 declared 271 includes the cancelled W17 BUF–CIN absence.

File: `data/ops/nfl-forecast-builder-t5107u/IDENTITY_RESOLUTION_2020_t5115u.json`

## D. Hashes

| Artifact                    | sha256                                                             |
| --------------------------- | ------------------------------------------------------------------ |
| EVAL cohort (game_ids)      | `fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0` |
| DEV cohort (game_ids)       | `f240fde23025d7584a5f8031ec1e0e74f902be1100ce1630aca4f2f20ed326b0` |
| full freeze cohort (892)    | `af129383acdad81316897cea6a1d5b48ca51647b3fc51092b55b29ca284908bc` |
| forecast freeze file        | `9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732` |
| design seal                 | `e5bb682db1a6183b0c68e5ba1ad537c9096ca833b285190d6e3bdd9bf875addd` |
| games.csv                   | `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8` |
| quote manifest              | `6a1c1b378b91abd5e2ed185649536468192147057a2ea535a23e8ae5b14e6984` |
| METRIC_COHORTS file         | `4c35e7d006fd374a961e91dd946ddc94f6a2b4f5dccdc138c3192b11af9e7f41` |
| IDENTITY_RESOLUTION file    | `7adc43b0145ee73ec4cc361c27d5730b87bdc90dd1d8e1921c94e6e1e2af207d` |
| parent tip                  | `931a532c698b3034f840bf719ed5b90da325f6ad`                         |
| this implementation tip     | `39a25343943fec7b14aaacf020df0c313c6624f8`                         |

## E. EXEC

Do **not** re-enter EXEC until Alex independent verify of this tip **and** CoS re-clear. That is the same authorized look with fail-closed prerequisites repaired — not a second look.

CERT=0 · DRAFT≠merge · no merge/send.
