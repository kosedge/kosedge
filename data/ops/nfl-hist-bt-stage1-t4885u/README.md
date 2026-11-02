# Hist BT Stage-1 t4885u — sample reconstruction (DRAFT)

OWNER CLEAR t4885u · card t4884u · **reconstruct + verify only**.

Alex RO is separate (`PASS_RECON | CONDITIONAL_RECON | RETURN`). Eng self-label: `VERDICT_ENG.md`.

## What this is

Per-field audit of IF input contract **b41f4b43** for a frozen **2017 REG W1–W2** sample (N=31) under as-of **cf514078**.

It is **not** a score, not a fit, not Stage-2, not E1, not CERT.

## Packet

| File | Role |
|---|---|
| `SELECTION_HASH_SEAL.json` | Hash of sorted game_ids, written **before** rebuild |
| `SAMPLE_MANIFEST.json` | Game ids, kickoffs, week, cutoffs, N, pins |
| `RECON_MATRIX.csv` | game × field × status × source × cutoff × lineage |
| `ASSUMPTIONS.md` | Every derivation rule |
| `COVERAGE.md` / `COVERAGE.json` | % present; full vs partial; Week-1 prior-season |
| `CALL_AUDIT.md` | Zero Odds/API; sources touched |
| `CONTRACT_PINS.json` | b41f4b43 / 1a53bbd3 / cf514078 / 4fe1cdd7 / 52d9e909 |
| `VERDICT_ENG.md` | Eng self-label only |
| `build_recon_t4885u.py` | Reproducible builder (no IF invoke) |
| `SHA256SUMS` | Packet digests |

## Frozen sample

- Source pin: `games.csv` **4fe1cdd7** (re-hashed MATCH)
- `selection_hash` = `b088b83286d46be53d05206ad2d2ccc19f460cb0eb77ed14050ab7285552df39`
- N = 31 (W1 15 + W2 16). MIA@TB not in pin; not added.

## Headline counts

| Status | Cells |
|---|---|
| DERIVED_PREGAME | 277 |
| MISSING_RECORD | 560 |
| OUT_OF_CONTRACT | 0 |
| EXCLUDED | 0 |

Fully reconstructable games: **0**. All 31 are partial (identity + rest; T5 on some W2 sides). T1–T4 5g fields are MISSING_RECORD everywhere.

## Locks

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · Stage-2 NOT authorized · NFL NO-GO · CERT=0
