# TRACE — CLEAR 92861 t5335u Worker B

CERT=0. Cos-host unused/quarantined. DRAFT #715 ≠ merge. NTBB-K not implemented.

| field | value |
|---|---|
| clear | 92861 |
| ticket | t5335u |
| worker | B · `bc-02a716be-429a-56c8-ab0f-5f262aa479df` |
| gate0 | PASS · `START_PREFLIGHT_CLEAR92861_B.md` sha256 `6b63dff95e35feb8c0378d968b3f9905bc6d2c1bdf9ace307b905b544bbd91e2` |
| start_tip | `7ea9729fb5d40a1805f07eb4f63e61363259bd1c` MATCH |
| phase1_status | **PARTIAL** (value bind 143; envelope clocks NOT_EVALUABLE) |
| owned_completion_claimed | **false** |
| freeze_limitations_verified | **false** |
| historical_economic_calculation | **false** |
| ntbb_k_implemented | **false** |

## Runtime vs source vs reported

| layer | what |
|---|---|
| **source** | `7834cbc7` freeze quotes n=187 sha `12a87529…`; ADMISSIBLE selected rows n=565 of 1667 sha `b4a3a4db…`; 81759 ledger sha `ce188c64…` (23/44); identities sha `f03041ad…`; staged 143 projection sha `bf5fd92e…` MATCH |
| **runtime** | unique bind market=spread + exact kickoff + exact `spread_home` → 143/143 ADMISSIBLE rows with `price_home`/`price_away`; staged projection 143/143 pair+value match; 0 unique captured_at-only row (3 markets share the stamp); no CSV envelope fields on JSONL; raw `clean/odds/nfl/snapshots-*.jsonl` absent (0/3) |
| **reported** | PARTIAL · 187=44+143 · 496=96+400 · line/price BOUND on 143 with source hashes · request/provider/book-update/download/availability **NOT_EVALUABLE** 0/143 · raw snapshot `source_file_sha256` **NOT_EVALUABLE** 0/3 · claimed `captured_at` not promoted to verified publication/observation |

## Commands (this host)

```
df -h / /agent/repos/kosedge
git rev-parse HEAD
sha256sum data/ops/nfl_owned_market_v1/codex_staged/CSV_PROVIDER_EVENT_IDENTITIES.json
sha256sum data/ops/nfl_owned_market_v1/CLOCK_LINEAGE_LEDGER_81759.json
cd services/model-service && PYTHONPATH=. python3 -m pytest tests/test_nfl_owned_market_v1.py -q --tb=short
```

Tests: **21 passed** (18 prior + 3 focused). Risk1 fixture unchanged `ca25354581ae94d87d7bc09aece6829711da6bbe8fd15414e6856e100d5f4b2e`.
