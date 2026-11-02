# CURSOR ADDENDUM t5157u — R5-HISTORY-ID (Worker A)

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO
Authority: OWNER CLEAR t5157u · R5-HISTORY-ID **e6cc6927** · Cos ORDER A **1e3c47b8**
HARD END 02:30 EST / 07:30Z.

Parent: PR **#701** tip **255adf7802830bc25814a739d62f65f095216203** · stamp **df074369**.
New isolated branch + **NEW DRAFT PR**. Does not rewrite #701 HOLD artifacts.

IF496 bytes **96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407**
unchanged — never regenerated. No Phase2 `--score`. No network / odds / paid.
No protected 2024–26 files. 2017 original Q2 eval **CLOSED**.

Preserve market∩96 **072e99e0** / **558fbfe5**. CERT=0 not EVAL / GREEN / #6.

**STOP for Cos/B.**

## 1) Identity projection ONLY

Read only `/Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01/play_by_play_2013.csv`
through `play_by_play_2019.csv`. Columns only: `game_id`, `old_game_id`, `season`,
`season_type`, `home_team`, `away_team`, `week`, `game_date`, `start_time`.

Each file sha256 matched existing `MANIFEST.md` in that archive directory.

| year | local sha256 | MANIFEST | n REG | n POST |
| ---: | --- | --- | ---: | ---: |
| 2013 | `33f96de7…9b22` | match | 256 | 11 |
| 2014 | `21250970…7ff8` | match | 256 | 11 |
| 2015 | `a6f608f4…6f00` | match | 256 | 11 |
| 2016 | `04884d03…80ca` | match | 256 | 11 |
| 2017 | `2f380b71…1b5a` | match | 256 | 11 |
| 2018 | `44ceb416…dabf` | match | 256 | 11 |
| 2019 | `1ae56cec…46e4` | match | 256 | 11 |

Dedup per game. Explicit `season_type` consistent (0 mixed / 0 invented).
REG membership frozen from `season_type=REG` — **not** week≤18.
Week≤18 would wrongly include **28** POST games (WC week 18). Example:
`2013_18_KC_IND`.

| Pin | sha256 |
| --- | --- |
| 2013–2019 REG identity | `9aad6f473fe6d32bf33466a47d80968dfdf8c8bd8ab8db0bca35e0972d1043a0` |
| 2013–2019 POST identity | `e43390f94e5b65204014ea588bbc9b6b4b880b6e28227a58e7cbc30ee765444f` |
| IDENTITY_FREEZE | `561ae3e1f0a0b99201f3b4a0a00d5da13e75ec7924ad9b6b67218c802aef8b3f` |
| IDENTITY_ROWS | `2a1dee956019e5a8e0a44f97a23dfe5d5580d69bd614918dc371f9bd8438720d` |
| PBP_FILE_SHA256 | `d97e3a993b2325c890ec3ceb22a922d8902634bb31038f3f69468bc5e35e31d4` |

Forbidden and not done: play values / EPA / stats / scores as features or
labels; invented `season_type`; raw-PBP feature reconstruction; opening
2020–26 PBP.

## 2) Bijective join

Approved kickoff = games.csv **4fe1cdd7**. Approved scores = outcomes
**50bda875**. 2020–21 REG membership remains schedule **08533423**
(`season_type=REG`).

Join via canonical `game_id` (1869 / 1869 for 2013–19; 528 / 528 for
2020–21 REG). Existing team map composed only
(`PBP_TO_CANON` / `GAMES_TO_CANON` / `PRIOR_ALIAS`) to prove
LA↔LAR↔STL, WAS↔WSH, LV↔OAK, SD↔LAC. No silent drop / default /
week≤18.

| Universe | REG | POST | unmatched | conflict |
| --- | ---: | ---: | ---: | ---: |
| PBP identity 2013–2019 | **1792** | **77** | **0** | **0** |
| Schedule REG 2020–21 | **528** | 0 | **0** | **0** |
| Q2 canon REG 2013–21 | **2320** | 77 (excluded) | **0** | **0** |

Unmatched examples: **none**. Kickoff from games.csv UTC Z — PBP
`start_time` is naive and was not used as kickoff.

JOIN_PROVENANCE sha
`fbe6331785e01622193f69a4ac9490702840066330afb962e0e87ffa6ffd3674`.

## 3) Original R5 Q2 rule — completed freeze

Rule unchanged and disclosed ≠ old kickoff-only as-of (`cf514078`):
earlier seasons + strictly earlier NFL weeks; kickoff < KO−60; no
same-week / own / later in state.

2013 `initial_prior=None` (zero-centered). Then 0.5 end-season carry
through complete canon REG. Choice + every history ID frozen **before**
forecasts.

| Fixed | Value |
| --- | --- |
| Q2 A / B | `2.5637441292077354` / `1.660624056183471` |
| ridge / prior | 20 / 0.5 |
| candidate | `0.5*IF+0.5*Q2` |
| R3 | w=0.75 **STOP** `81b6c0fc` |

Appended completed-candidate freeze **only** against unchanged IF496
bytes. old437 / new59 / full496 identities + RETRO_FIT kept
(SPLIT_SCAFFOLDING sha still `0b7a7d1e…` — same bytes as t5155u).

| Result | Value |
| --- | --- |
| n_forecasts | **496** |
| n_if_finite | **496** (copied, not regenerated) |
| n_q2_finite | **496** |
| n_q2_hold | **0** |
| n_candidate_finite | **496** |
| history n | 1808 (2020 W2) … 2304 (late 2021) |
| example `2020_02_CIN_CLE` | `m_if=0.07714026611934685` (exact pin) · `m_q2=2.945517401943153` · `m_c=1.51132883403125` · n_history=1808 |

| Pin | sha256 |
| --- | --- |
| history choice | `679d24283869ccf6b0a2b434efa200e92fd3e2c12a98c446da7d8f968da913b7` |
| HISTORY_IDS_FREEZE | `c97f8fbc72030e5a2f6ffb2d5b09d98ad7682ba7f6f8996c72737b6a6caae807` |
| Q2_COMPLETED_FREEZE | `eeb6fff73383289c1e69a1a1b30f6df5eed38c7201c58ca9de16feaa8f06cc04` |
| CANDIDATE_COMPLETED_FREEZE | `2f9a73e68d66878b984d5ae9e2e6fc01cfe16e45b0da4ad5389f90aabe9a87c7` |
| FORECASTS_DEV_R5_496_Q2_COMPLETED | `f4b970f0138a5e2c5f1496711220282650ce4d79f9ae62aeecc6473cae535171` |
| IF496 (untouched) | `96d3aa6f85e7896df2385df8d025ea0bd4d15d5e2a82edc3f5c9184cd35af407` |

t5155u HOLD dir not overwritten. `--score` / `--eval` / `--load-targets`
refuse with `outcome_loader_reads=0`.

## 4) Failure path (not taken)

HOLD with exact unmatched examples. No invented history. Not used —
join was bijective.

## Isolated package

`data/ops/nfl-t5157u-r5-history-id/`

FREEZE_MANIFEST sha
`6abba598d3c7dd8ed797cf26b308962b3e7b4d57524087c7356bd267b30c8bc0`.

Command:

```
PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_history_id_t5157u.py
PYTHONPATH=services/model-service python scripts/nfl/run_nfl_r5_history_id_t5157u.py --score
# → refused; outcome_loader_reads=0
```

## Tests

```
cd services/model-service && PYTHONPATH=. python -m pytest \
  tests/test_nfl_t5157u_r5_history_id.py tests/test_nfl_t5155u_r5_496_freeze.py -q
```

26 passed: identity fixture + invented-type refuse; bijective join +
unmatched examples; week≤18 refuse; existing team-map compose; R5
history filter; candidate 0.5/0.5 + R3 STOP; Phase2 score refuse;
IF/HOLD pins; committed freeze hashes; t5155u HOLD suite still green.

## Holds

R3 STOP `81b6c0fc`. R2-C / Stage C unchanged. No 2022–23 regen/scoring.
No 2024–26. No Q2/2017 reopen. No merge / deploy / secrets / paid pulls.
No Phase2 `--score`. CERT=0. Not EVAL / GREEN / #6.

**STOP for Cos/B.**
