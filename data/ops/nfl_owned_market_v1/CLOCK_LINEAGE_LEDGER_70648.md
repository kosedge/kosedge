# CLOCK / SOURCE-LINEAGE LEDGER — EVIDENCE 70648 (t5324u)

CERT=0. Machine copy: `CLOCK_LINEAGE_LEDGER_70648.json`
sha256 `157a91c2957ceeb02e733c08e638889abf5497738b7536680ce4df2cc38c63b4`.

`owned_completion_claimed=false`.
`freeze_limitations_marked_verified=false`.
Provider historical timestamp is **NOT** contemporaneous model availability.

## GATE0 / staged verify

| | |
|---|---|
| host | `cursor` · `bc-02a716be` |
| free | 245.325031 GiB on `/dev/vdc` · PASS |
| start_tip | `2497a156b888c41c4e1b552ac9af325991c7c7e0` |
| staged | `data/ops/nfl_owned_market_v1/codex_staged/CSV_CLOCK_METADATA.json` |
| content sha256 | `496be81d9f7a1050490796c8a4e2a4e898a8ae085b72a796a4101126cbcabff2` **MATCH** (19889 bytes) |
| original_metadata_sha256 | `1e5705f74b7e5a477f31660bf83ca84617827965f257802c51437f1037283ebc` |

## 44 CSV associations (event×book with spreads market_last_update)

| envelope `request_date` | path | selected_csv | events |
|---|---|---|---|
| 2020-12-27T18:00:00Z | `raw/odds/americanfootball_nfl/historical/2020/2020-12-27_odds_pre7d_2020-12-27T180000Z.json` | 10 | 5 |
| 2021-12-26T18:00:00Z | `raw/odds/americanfootball_nfl/historical/2021/2021-12-26_odds_pre7d_2021-12-26T180000Z.json` | 8 | 4 |
| 2022-01-08T21:30:00Z | `raw/odds/americanfootball_nfl/historical/2022/2022-01-08_odds_pre7d_2022-01-08T213000Z.json` | 26 | 14 |

10+8+26=44. Third envelope calendar date is 2021-season REG end (Jan 2022 metadata only — no quote lines/prices).

Two book rows on envelope 2 **excluded** from 44 (no `market_last_updates[spreads]`):
- `event_id=a84b431e86647a9698859ae4b1cb62f2` book=`fanduel`
- `event_id=04dbadcea53d7d51ef5ede96914a6890` book=`fanduel`

## Evidenced clock semantics (44 only)

| field | mapping | semantic |
|---|---|---|
| `request_date` | `sources[].request_date` | Odds API historical as-of **request** clock |
| `payload_timestamp` | `sources[].payload_timestamp` | provider historical **snapshot** stamp |
| `previous_timestamp` / `next_timestamp` | `sources[]` | provider snapshot **neighbors** |
| `book.last_update` | `books_metadata[].last_update` | provider **book-update** in snapshot |
| `market_last_updates[spreads].last_update` | spreads market last_update | provider **market-update** |
| `commence_time` | `matching_events_metadata[].commence_time` | provider event commence |
| `pulled_at` | `sources[].pulled_at` | **download** 2026-08-18 — not model availability |
| `path` | `sources[].path` | repo-style `raw/` locator |

## Unresolved (exact — not blanket unavailable)

| field | locator | reason |
|---|---|---|
| `publication_timestamp_status` | `7834cbc7:…/MARKET_ARM_FREEZE.json#limitations` | still **unverified**; this evidence does not close it |
| `observation_timestamp_status` | same `#limitations` | still **unverified** |
| event_id → selected-187 `game_id` | staged `id` vs freeze `quotes.game_id` | **overlap 0**; no identity join |
| JSONL `captured_at\|available_at\|observed_at` | ADMISSIBLE / freeze quotes | 44 envelope rows do not prove JSONL clocks |
| **143 JSONL unknown** | 187−44 | preserved unknown (metadata `evidence_limit`) |
| contemporaneous model availability | `pulled_at` vs request/payload | historical provider stamps ≠ live availability |
| full price/value/export lineage | staged file | metadata only; not promoted |
| all-187 clock coverage | 44/187 | not claimed |

## Preserved

187/400 · ADMISSIBLE@7834cbc7 · FREEZE 96/496 · risk1 `ca253545…` · prior HOLD honesty on freeze#limitations.
No `clock_provenance.json` invented.
