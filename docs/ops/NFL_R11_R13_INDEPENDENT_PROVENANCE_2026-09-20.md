# KosEdge NFL — independent R11 / R13 provenance packet (2026-09-20)

**Lane:** provenance / reproducibility only  
**Model behavior:** unchanged  
**Holdout execution:** not run  
**Deploy / merge / promotion:** not requested and not performed  
**Verdict:** **FAIL_CLOSED** — exact reproduction is **not** established

Machine twin: [`data/ops/nfl-r11-r13-independent-20260920/verdict.json`](../../data/ops/nfl-r11-r13-independent-20260920/verdict.json)  
Ops receipt: [`data/ops/nfl-r11-r13-independent-20260920.md`](../../data/ops/nfl-r11-r13-independent-20260920.md)  
Cert runner (prepare-only): [`scripts/nfl/prepare_r11_r14_cert.py`](../../scripts/nfl/prepare_r11_r14_cert.py)

This packet does **not** edit `nfl_simulator.py`, retune coefficients, rematerialize, bind Fair Lines, or treat any near-miss artifact as frozen R11 / prior R13 / candidate R14.

A concurrent draft search exists as PR 576 (`cursor/nfl-r11-r13-lineage-7c4b`). It is recorded as an independent FAIL_CLOSED search in the same window. It is **not** used as a lineage source.

---

## Verdict

| Slot                                               | Status                      | Bind allowed |
| -------------------------------------------------- | --------------------------- | ------------ |
| Frozen R11 source                                  | **UNBOUND**                 | no           |
| Prior R13 experiment                               | **UNBOUND**                 | no           |
| Candidate R14                                      | **UNBOUND**                 | no           |
| Frozen gate set (key-3 / key-7 / OT / MAE / total) | **UNBOUND_DIMENSIONS_ONLY** | no compare   |

**R11 / R13 / R14 are labels that do not exist in this repo.** They were not found as filenames, commits, tags, worktrees, Linear issues, Notion pages, Gmail threads (except the concurrent PR 576 notices), Google Drive titles, or X posts. Reconstructing a lineage from nearby NFL artifacts would require inventing a binding. The instruction is fail-closed, so this lane stops.

---

## Requested lineage fields

For each of R11 and R13, the following were required. All remain null / empty.

| Field                                    | R11                                                                      | R13       |
| ---------------------------------------- | ------------------------------------------------------------------------ | --------- |
| git commit                               | not found                                                                | not found |
| git branch                               | not found                                                                | not found |
| worktree                                 | not found                                                                | not found |
| simulator source files                   | not found                                                                | not found |
| experiment runner                        | not found                                                                | not found |
| config / parameter set                   | not found                                                                | not found |
| data inputs + hashes                     | not found                                                                | not found |
| random seed(s)                           | not found                                                                | not found |
| command used                             | not found                                                                | not found |
| generated calibration artifacts          | not found                                                                | not found |
| key-3 / key-7 / OT / MAE / total metrics | not found                                                                | not found |
| uncommitted or external dependency       | **likely** — label exists only outside this checkout if it exists at all | same      |

Checkout at search: `kosedge/kosedge` `deploy-vercel` `4aeab78f2011ac593c708f24acc01bf5117f9728`. Only worktree: `/workspace`. Self-hosted Cursor workers: none connected. `/Volumes/KosEdgeData` is not mounted. Google Calendar search returned an internal error (no events recovered). Slack search is not available in this tool set.

---

## Near misses — recorded, not aliased

These exist in-repo and must **not** be treated as R11 / R13 / R14:

1. **`pe_drive_poss_v1`** sha `b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b`  
   Fair Lines PRODUCTION-CERT war-room practice SHA. Status: **REJECTED_PRACTICE_SHA** / Alex NO CLEAR / “all five gates FAIL”.  
   Missing from that packet: git SHA of the simulator that produced it, runner path, config, data hashes, seeds, command, and the five numeric metrics. The phrase “five gates” is not mapped to key-3 / key-7 / OT / MAE / total in any filed artifact.

2. **`pe_drive_poss_v2`** — diagnostic STOP. Not frozen. Not R13. Not R14.

3. **Live packaged-EPA SHA `153b6a884a8e`** — historical OOS diagnostic (`MODEL_SIGNAL_WEAK`). July-31 multi-season freeze is already marked **UNREPRODUCIBLE** in that packet. Different experiment.

4. **Market-risk register R11** — `book_ledger` ≠ market ledger. Odds infra, not a sim round.

5. **Personnel `r11` / `r13` rates** — 11-personnel / 13-personnel grouping rates in `personnel_efficiency.py`. Unrelated.

6. **WR11 / WR13 / WR14** — fantasy rank notes from 2026-08-13. Unrelated.

7. **Current `nfl_simulator.py`** (`DEFAULT_NFL_MODEL_VERSION = nfl-v1.5-matchup-sim`) — checked-in simulator, not labeled R11/R13/R14. Binding it would invent a lineage.

8. **`docs/NFL_ENTERPRISE_GATES.md`** ATS / CLV / MAE floors — product betting gates, not an R11 frozen gate set.

---

## Certification runner (prepared, not executed on holdout)

`scripts/nfl/prepare_r11_r14_cert.py` is a **deterministic readiness checker**.

Default:

```bash
python3 scripts/nfl/prepare_r11_r14_cert.py
```

What it does:

- Loads the three lineage slots + requested gate-set dimensions
- Requires every lineage field to be present and `status=EXACT` before a compare is legal
- Prints **FAIL_CLOSED** while slots are UNBOUND
- Hard-refuses `--execute-holdout` (no held-out data path)

What it does **not** do:

- Import or call `nfl_simulator.py` or any scoring equation
- Invent thresholds for key-3 / key-7 / OT / MAE / total
- Bind Fair Lines / PLAY / Kelly
- Rematerialize or write production artifacts

A compare of frozen R11 vs candidate R14 becomes legal only after someone files complete EXACT lineage JSON (same schema) **and** a BOUND gate set with sourced thresholds. That filing is outside this lane.

---

## How to unstick (human / war-room, not this agent)

To flip R11 from UNBOUND to EXACT, drop a completed `r11.lineage.json` that names:

- commit + branch + worktree
- simulator files + runner + config
- input paths **and** hashes
- seeds + exact command
- calibration artifact paths
- the five metrics
- any external/uncommitted dependency, called out

Same for R13 and for an R14 candidate. Until then, certification stays fail-closed.
