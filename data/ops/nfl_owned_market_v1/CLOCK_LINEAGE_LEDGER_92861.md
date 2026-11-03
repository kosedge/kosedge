# JSONL TRACE LEDGER — 92861 (t5335u)

CERT=0. Machine: `CLOCK_LINEAGE_LEDGER_92861.json`
sha256 `6879ed43cc9e4ad7bef0a124bc0514ea7d1adb9af1775101e0bbcd6aad6d5e75`.

Status **PARTIAL**. `owned_completion_claimed=false`.
freeze `#limitations` **not** marked verified. NTBB-K **not** implemented.
No historical ATS/ROI/forecast.

Parent IDENTITY 81759 (`ce188c64…`) preserved: **23/23** events · **44/44** CSV mappings.

## Reconcile (exact)

| equation | n | ids |
|---|---|---|
| selected quotes | 187 | freeze `#intersection.games[].quotes` |
| CSV envelope mapped | 44 | 81759 subset (game_id, book) |
| JSONL remaining | 143 | 187 − 44 · source=`the-odds-api-historical-enterprise` |
| **187 = 44 + 143** | true | mapped_not_in_quotes=0 |
| selected games | 96 | freeze `#intersection.game_ids` |
| missingness | 400 | freeze `#intersection.missing_game_ids` |
| **496 = 96 + 400** | true | selected ∩ missing = 0 |

## 143 source/value bind (already-owned selected only)

Sources: `7834cbc7:MARKET_ARM_FREEZE.json` sha `12a87529…` ·
`7834cbc7:ADMISSIBLE_QUOTES_B1.jsonl` sha `b4a3a4db…` (selected game_ids only; no new API / no broad scan) ·
staged `JSONL_SELECTED_143_SOURCE_VALUE_PROJECTION.json` sha `bf5fd92e…` **MATCH** (143/143 pairs+values; `clock_semantics_verified=false`).

| field | status | n |
|---|---|---|
| book / event / side=home / market=spread | BOUND | 143/143 |
| line (`spread_home`) unique freeze + ADMISSIBLE | BOUND_UNIQUE_FREEZE_AND_ADMISSIBLE | 143/143 |
| price_home / price_away unique ADMISSIBLE spread row | BOUND_UNIQUE_ADMISSIBLE_SPREAD_ROW | 143/143 |
| per-row freeze + ADMISSIBLE source hashes | present | 143/143 |
| snapshot_kind | `enterprise_snapshot` (not open/close) | 143/143 |
| seasons | 2020 / 2021 only | 72 / 71 |

Provenance file names (not a 2022/23 quote reopen): snapshots-2021=71 · snapshots-2020=40 · snapshots-2022=32 (those 32 are **2021** week 17–18 January kickoffs).

## Clocks (separated)

| column | status | present/scope | locator |
|---|---|---|---|
| claimed-capture (`captured_at`) | CLAIMED_FIELD_PRESENT_NOT_VERIFIED | 143/143 | freeze quote == unique ADMISSIBLE spread row; `#limitations` still unverified |
| request (`request_date`) | **NOT_EVALUABLE** | 0/143 | absent on JSONL freeze/ADMISSIBLE; CSV envelopes cover 44 only |
| provider (`payload/previous/next_timestamp`) | **NOT_EVALUABLE** | 0/143 | same |
| book-update (`last_update`) | **NOT_EVALUABLE** | 0/143 | same |
| download (`pulled_at`) | **NOT_EVALUABLE** | 0/143 | CSV download 2026-08-18 is not JSONL proof |
| availability (contemporaneous) | **NOT_EVALUABLE** | 0/143 | `observation_is_not_file_mtime=true` on 143/143 |
| raw snapshot JSONL `source_file_sha256` | **NOT_EVALUABLE** | 0/3 files | `clean/odds/nfl/snapshots-202{0,1,2}-20260806.jsonl` absent on this host and absent from 7834cbc7/HEAD |

## Holds remaining

- publication/observation timestamp status = **unverified** on freeze `#limitations`
- 143 envelope clocks stay NOT_EVALUABLE
- missingness 400 causes **not invented**
- no outcome join · no export of verified clocks · science EXEC HOLD
