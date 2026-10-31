# nfl-lane-s-discrimination-t4915u

**DRAFT packet — Cursor eng.** Alex RO next. Do not merge. Do not interpret to OWNER from this folder.

| | |
|---|---|
| Ticket | OWNER t4915u ACCEPT Phase 1 Lane S ONLY |
| Label | DEV_RESEARCH / RETRO_FIT exploratory |
| CERT | 0 |
| NFL | NO-GO |
| Sample | sealed 70 (`SCORE_RESULTS` sha8 **2b9f302e**) |
| Control tip | **02197f58** (unchanged) |
| IF tip | **6ca03716** (read-only via SCORE_RESULTS) |
| Freeze | Amend-1 sha256 **29dc4005…e3ac53fc** |
| **VERDICT_ENG** | **FAILS_TO_SHOW** |

## What this is

One frozen EXEC of whether W-L and A1-labeled EPA/success inputs discriminate realized margins on the already-examined 70-game development sample. Signal definitions, orientation, comparisons, and MISSING rules were sealed before EXEC (`EXEC_FREEZE_t4915u_LANE_S_ANALYSIS_PLAN.md`).

## What this is not

Forecast regeneration, engine ablation, model math/feature/weight change, cutoff search, sample expansion, 2024–25 access, publish, betting, CERT, or Phase 2 Lane E implementation.

## Packet

| File | Role |
|---|---|
| `EXEC_FREEZE_t4915u_LANE_S_ANALYSIS_PLAN.md` | Sealed analysis plan (Amend-1) |
| `OWNER_ACCEPT_t4915u_PHASE1_LANE_S.md` | Phase 1 Lane S ACCEPT |
| `SIGNAL_TABLE.csv` / `.json` | 70 rows: outcomes + every frozen signal |
| `DISCRIMINATION_RESULTS.json` / `.md` | All `comparisons_frozen` |
| `WEEK_SUBSET_AUDIT.md` / `.json` | Week / LOO concentration |
| `ASSUMPTIONS.md` | Formulas, seeds, MISSING, labels |
| `CALL_AUDIT.md` | Hash gate + untouched list |
| `VERDICT_ENG.md` | FAILS_TO_SHOW + next experiment |
| `run_lane_s_exec.py` | One-run runner (numpy only) |
| `inputs/` | SCORE_RESULTS, manifest, both RECON matrices |
| `SHA256SUMS` | Packet hashes |

## Reproduce

```bash
python3 data/ops/nfl-lane-s-discrimination-t4915u/run_lane_s_exec.py
```

Stops if `SCORE_RESULTS` sha256 does not start with `2b9f302e`.
