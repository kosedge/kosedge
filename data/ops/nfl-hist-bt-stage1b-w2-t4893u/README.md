# Hist BT Stage-1b t4893u — 2017 REG W2 first (DRAFT)

OWNER CLEAR t4893u · sha8 `05ec1dde` · **reconstruct + verify only**.

Alex RO is separate (`PASS_RECON | CONDITIONAL_RECON | RETURN`). Eng self-label: `VERDICT_ENG.md`. This packet does **not** claim PASS.

## What this is

Per-field reconstruction of IF input contract **b41f4b43** for a frozen **2017 REG W2 eligible** sample (N=14) under as-of **cf514078**, using the owned nflverse PBP 2017 parquet pin **84eacd96**.

It is **not** a score, not a fit, not Stage-2, not E1, not CERT, not an Odds call.

## Packet

| File | Role |
|---|---|
| `SELECTION_HASH_SEAL.json` | Hash of sorted **eligible** game_ids, written **before** PBP open / matrix rebuild |
| `SAMPLE_MANIFEST.json` | Eligible games, kickoffs, cutoffs, pins, exclusions |
| `EXCLUSIONS.json` | Every dropped W2 game + fixed rule |
| `RECON_MATRIX.csv` | game × field × status × source × cutoff × lineage |
| `ASSUMPTIONS.md` | Every derivation rule |
| `COVERAGE.md` / `COVERAGE.json` | 27/27 complete vs partial; exclusions |
| `CALL_AUDIT.md` | Odds=0; sources touched |
| `CONTRACT_PINS.json` | b41f4b43 / 1a53bbd3 / cf514078 / 4fe1cdd7 / 84eacd96 / 52d9e909 |
| `T1T4_PLAIN_ENGLISH_DEFS.md` | Pre-eng attach (OWNER) |
| `T1_TRANSFORM.md` / `.json` | T1 SQL port + pressure/RZ match notes |
| `LEAKAGE_AUDIT.json` | Consumed W1 games; kickoff < target |
| `t1_team_week_2017_w1.csv` | Intermediate T1 (30 teams; TB/MIA absent) |
| `VERDICT_ENG.md` | Eng self-label only |
| `build_recon_t4893u.py` | Reproducible builder (no IF invoke) |
| `SHA256SUMS` | Packet digests |

## Frozen sample

- Source pin: `games.csv` **4fe1cdd7** (re-hashed MATCH)
- Source W2: 16 REG games
- Excluded (fixed rule, pre-declared): `2017_02_CHI_TB` (TB), `2017_02_MIA_LAC` (MIA) — Irma; left out of sample, no fills
- Eligible N = **14**
- `selection_hash` = `96a1317613d695fe027caf4a9230028480f64facfe460736702bd66328708640`
- Recipe: `sha256(utf-8 of sorted canonical game_id list joined by "\n" with trailing "\n")`

## Headline counts

| Status | Cells (eligible 14 × 27) |
|---|---|
| DERIVED_PREGAME | **378** |
| MISSING_RECORD | **0** |
| OUT_OF_CONTRACT | 0 |
| EXCLUDED cells | 0 |

Complete eligible games (27/27 DERIVED_PREGAME): **14 / 14**. Partial: **0**.

## Locks

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · Stage-2 NOT authorized · NFL NO-GO · CERT=0
