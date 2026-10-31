# Hist BT Stage-1b t4893u — 2017 REG W3–W6 (DRAFT)

OWNER CLEAR t4893u · CoS ORDER after Alex W2 PASS_RECON `91e2d7db` @ tip `440314e4`. **Reconstruct + verify only.**

Alex RO is separate (`PASS_RECON | CONDITIONAL_RECON | RETURN`). Eng self-label: `VERDICT_ENG.md`. This packet does **not** claim PASS.

## What this is

Per-field reconstruction of IF input contract **b41f4b43** for a frozen **2017 REG W3–W6 eligible** sample (N=60) under as-of **cf514078**, using the owned nflverse PBP 2017 parquet pin **84eacd96**.

Same T1–T4 method as `data/ops/nfl-hist-bt-stage1b-w2-t4893u/` (builder functions reused; no new transforms).

It is **not** a score, not a fit, not Stage-2, not E1, not CERT, not an Odds call.

## Packet

| File | Role |
|---|---|
| `SELECTION_HASH_SEAL.json` | Per-week + combined hashes of sorted **eligible** game_ids, written **before** PBP open / matrix rebuild (commit `32f9a3ec`) |
| `SEAL_ATTESTATION.md` | PBP-absent-at-seal proof |
| `seal_selection_t4893u.py` | Seal-only script (games.csv + OOS; no pandas / no parquet) |
| `SAMPLE_MANIFEST.json` | Eligible games, kickoffs, cutoffs, pins, T2 misses |
| `EXCLUSIONS.json` | Fixed rule; empty list (0 dropped) |
| `RECON_MATRIX.csv` | game × field × status × source × cutoff × lineage |
| `ASSUMPTIONS.md` | Every derivation rule |
| `COVERAGE.md` / `COVERAGE.json` | 27/27 complete vs partial; by week |
| `CALL_AUDIT.md` | Odds=0; sources touched |
| `CONTRACT_PINS.json` | b41f4b43 / 1a53bbd3 / cf514078 / 4fe1cdd7 / 84eacd96 / 52d9e909 |
| `T1T4_PLAIN_ENGLISH_DEFS.md` | Pre-eng attach (OWNER) + W3–W6 coverage target |
| `T1_TRANSFORM.md` / `.json` | T1 SQL port + pressure/RZ match notes |
| `LEAKAGE_AUDIT.json` | Consumed W1–W5 games; per-target kickoff < target |
| `t1_team_week_2017_w1w5.csv` | Intermediate T1 (154 team-weeks) |
| `W2_LINEAGE.md` | W2 tip / Alex hash / selection_hash |
| `VERDICT_ENG.md` | Eng self-label only |
| `build_recon_t4893u.py` | Reproducible builder (imports W2 T1–T4; no IF invoke) |
| `SHA256SUMS` | Packet digests |

## Frozen sample

- Source pin: `games.csv` **4fe1cdd7** (re-hashed MATCH)
- Source W3–W6: 16+16+14+14 = **60** REG games
- Excluded (fixed rule): **none**. Every side had ≥1 completed 2017 game as-of kickoff (Irma TB/MIA completed W2 before W3).
- Eligible N = **60**
- Combined `selection_hash` = `e03c962ee6a95ca62a25bf050e4775f44893c384c63a31baaead5f9c9f6c5ebf`
- Per-week hashes in `SELECTION_HASH_SEAL.json`
- Recipe: `sha256(utf-8 of sorted canonical game_id list joined by "\n" with trailing "\n")`

## Headline counts

| Status | Cells (eligible 60 × 27) |
|---|---|
| DERIVED_PREGAME | **1576** |
| MISSING_RECORD | **44** |
| OUT_OF_CONTRACT | 0 |
| EXCLUDED cells | 0 |

Complete eligible games (27/27 DERIVED_PREGAME): **56 / 60**. Partial: **4** (W6 homes that were on bye in W5; exact `rating_week=5` T2 miss; no last-played fill).

| Week | Source | Excl | Eligible | Complete 27/27 | Partial |
|---|---|---|---|---|---|
| 3 | 16 | 0 | 16 | 16 | 0 |
| 4 | 16 | 0 | 16 | 16 | 0 |
| 5 | 14 | 0 | 14 | 14 | 0 |
| 6 | 14 | 0 | 14 | 10 | 4 |
| Combined | 60 | 0 | 60 | 56 | 4 |

## W2 lineage

- Eng tip `440314e4` · PR #669 DRAFT · Alex PASS_RECON sha8 `91e2d7db`
- W2 selection_hash `96a1317613d695fe027caf4a9230028480f64facfe460736702bd66328708640` (N=14)
- W1 T1 rows in this packet match the W2 `t1_team_week_2017_w1.csv` (max abs diff 0)

## Locks

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · Stage-2 NOT authorized · NFL NO-GO · CERT=0
