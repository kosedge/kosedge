# Actual original source locators — DELTA 58426

CERT=0. Worker B on THIS Cursor host. Cos DISK-1 HELD. No Cos staging.
Invented destinations (`owned_2020_21_selected_187.json`, `missingness_400.json`,
`clock_provenance.json`) are **not** the source. This file names the originals.

History restore: `git show 7834cbc79226e44fa3bd625e1eb526e9a800a128:<path>`
(not on `main`, not on tip `9ce485e9`).

## Original locators (Cos-verified)

| id | original object | field | restore | sha256 |
|---|---|---|---|---|
| admissible_quotes_b1 | `7834cbc7:data/ops/nfl-t5119u-r2-owned-coverage/t5136u_B1/ADMISSIBLE_QUOTES_B1.jsonl` | jsonl rows | **RESTORED_FROM_HISTORY** | `b4a3a4dbb8c5404d095b8095ec4018b96ceae532a50600d6d7f29f9d8fe950e6` MATCH |
| market_arm_freeze | `7834cbc7:data/ops/nfl-t5155u-r5-phase1/MARKET_ARM_FREEZE.json` | `reg496.n=496` (`identity_sha256=6429f859…`) · `intersection.n=96` · `missing_n=400` · `games[].quotes` n=187 | **RESTORED_FROM_HISTORY** | `12a8752979149f2c533b389c6dc7803856a1632b965ad12210de409f56963c98` |

`b1_universe` on the freeze pins the same ADMISSIBLE path+sha256.

## Identity projection (before quote-value exposure)

| object | n | seasons | values copied |
|---|---|---|---|
| selected-187 | 187 (`82` / `105`) | 2020 / 2021 only | **none** (no line/price/spread/home_margin) |
| missingness-400 | 400 game_ids (`199` / `201`) | 2020 / 2021 | causes **not invented** |

Source of 187: `MARKET_ARM_FREEZE.json#intersection.games[].quotes` = `two_book_n=91` + `one_book_n=5`.
No 2022/23 values used. Raw ADMISSIBLE file was **not** copied onto this tip (avoids 2022/23 value exposure).

## Remaining blocker — clock

**Not invented.** Original freeze already states:

- locator: `7834cbc7:data/ops/nfl-t5155u-r5-phase1/MARKET_ARM_FREEZE.json#limitations`
- `publication_timestamp_status=unverified`
- `observation_timestamp_status=unverified`
- original quote objects also carry field names `captured_at`, `cutoff_utc`, `kickoff_utc` — **not** promoted to verified clock provenance

`owned_completion_claimed=false`. Codex 187-row metadata not requested (187 recovered from freeze after restore).

## CONTINUE 69537 (t5320u)

Clock/source-value lineage still **HOLD** on freeze `#limitations`. See `CLOCK_SOURCE_HOLD_CONTINUE69537.md`.

## EVIDENCE 70648 (t5324u)

Staged three-envelope metadata MATCH `496be81d…`. 44 CSV associations evidenced at request/snapshot/book-update/download fields only.
Does **not** close freeze `#limitations`. 143 JSONL unknowns preserved. See `CLOCK_LINEAGE_LEDGER_70648.md`.
