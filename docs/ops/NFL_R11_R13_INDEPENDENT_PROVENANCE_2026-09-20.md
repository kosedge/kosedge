# KosEdge NFL — independent R11 / R13 provenance packet (2026-09-20)

**Lane:** provenance / reproducibility only  
**Model behavior:** unchanged  
**Holdout execution:** not run  
**Deploy / merge / promotion:** not requested and not performed  
**Verdict:** **FAIL_CLOSED** — exact reproduction is **not** established

Machine twin: [`data/ops/nfl-r11-r13-independent-20260920/verdict.json`](../../data/ops/nfl-r11-r13-independent-20260920/verdict.json)  
Ops receipt: [`data/ops/nfl-r11-r13-independent-20260920.md`](../../data/ops/nfl-r11-r13-independent-20260920.md)  
Alex bind: [`data/ops/nfl-r11-r13-independent-20260920/alex_external_bind.json`](../../data/ops/nfl-r11-r13-independent-20260920/alex_external_bind.json)  
Cert runner (prepare-only): [`scripts/nfl/prepare_r11_r14_cert.py`](../../scripts/nfl/prepare_r11_r14_cert.py)

This packet does **not** edit `nfl_simulator.py`, retune coefficients, rematerialize, bind Fair Lines, or treat any near-miss artifact as frozen R11 / prior R13 / candidate R14.

A concurrent draft search exists as PR 576 (`cursor/nfl-r11-r13-lineage-7c4b`). It is recorded as an independent FAIL_CLOSED search in the same window. It is **not** used as a lineage source.

---

## Verdict

| Slot                                               | Status                           | Bind allowed |
| -------------------------------------------------- | -------------------------------- | ------------ |
| Frozen R11 source                                  | **PARTIAL_EXTERNAL**             | no           |
| Prior R13 experiment                               | **PARTIAL_EXTERNAL** (discarded) | no           |
| Candidate R14                                      | **UNBOUND**                      | no           |
| Frozen gate set (key-3 / key-7 / OT / MAE / total) | **UNBOUND_DIMENSIONS_ONLY**      | no compare   |

Alex filed an external provenance bind from the Academy / research store. Recoverable **labels and hash prefixes** are recorded below. Unrecovered fields stay null. Truncated hashes are **not** completed. The lane stays fail-closed until EXACT artifacts are checked in or attached.

---

## Alex external bind (documentation only)

Filed store paths (not in this git checkout):

| Store path                                                                     | sha256                 | Present here |
| ------------------------------------------------------------------------------ | ---------------------- | ------------ |
| `permanent-engine/docs/ops/NFL_R11_R13_INDEPENDENT_PROVENANCE_2026-09-20.md`   | prefix `bb6ebda9` only | **no**       |
| `permanent-engine/docs/ops/NFL_R11_R13_INDEPENDENT_PROVENANCE_2026-09-20.json` | prefix `d1dfc752` only | **no**       |

Searched: `/workspace/permanent-engine`, repo filenames, Google Drive titles, Gmail. Missing. Full sha256 was not invented.

### Recoverable labels (not EXACT)

| Slot | Artifact                         | Engine | Engine hash       | Runner hash       | Other                                                              |
| ---- | -------------------------------- | ------ | ----------------- | ----------------- | ------------------------------------------------------------------ |
| R11  | `pe_clock_play_v3.3`             | V33    | prefix `6f98bb19` | prefix `5abf5e69` | seed **20260917**; packets / pbp_clock / calib **named, unhashed** |
| R13  | `pe_clock_play_v3.5` (discarded) | V35    | prefix `4db68127` | prefix `35700d8b` | gate / STOP / KEY7 / ENDGAME packets **named, unhashed**           |

R13 KEY7 is a packet name, not a numeric key-7 threshold.

### Still UNRECOVERABLE (keep fail-closed)

- git SHAs for the R11 / R13 labels
- Mac / Drive absolute paths
- `freeze/CLOCK_PLAY_R11` and `CLOCK_PLAY_R13` directories
- original argv
- full sha256 (prefixes only)
- numeric key-3 / key-7 / OT / MAE / total metrics

`nfl_simulator.py` and personnel-r11 grouping rates remain **explicit non-aliases**.

---

## Requested lineage fields

| Field                                    | R11                                       | R13                                                |
| ---------------------------------------- | ----------------------------------------- | -------------------------------------------------- |
| git commit / branch / worktree           | **UNRECOVERABLE**                         | **UNRECOVERABLE**                                  |
| simulator source files                   | not in this checkout                      | not in this checkout                               |
| experiment runner                        | hash prefix `5abf5e69` only; path missing | hash prefix `35700d8b` only; path missing          |
| config / parameter set                   | not found                                 | not found                                          |
| data inputs + hashes                     | pbp_clock named; hashes missing           | not found                                          |
| random seed(s)                           | **20260917**                              | not found                                          |
| command used (original argv)             | **UNRECOVERABLE**                         | **UNRECOVERABLE**                                  |
| generated calibration artifacts          | named packets/calib; paths/hashes missing | named gate/STOP/KEY7/ENDGAME; paths/hashes missing |
| key-3 / key-7 / OT / MAE / total metrics | not found                                 | not found                                          |
| uncommitted or external dependency       | Academy store not attached                | same                                               |

---

## Near misses — recorded, not aliased

These exist in-repo and must **not** be treated as R11 / R13 / R14:

1. **`pe_drive_poss_v1`** sha `b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b` — rejected war-room practice SHA. Different artifact family from `pe_clock_play_v3.3`.
2. **`pe_drive_poss_v2`** — diagnostic STOP. Not R13/R14.
3. **Live packaged-EPA SHA `153b6a884a8e`** — historical OOS diagnostic (`MODEL_SIGNAL_WEAK`).
4. **Market-risk register R11** — odds infra, not a sim round.
5. **Personnel `r11` / `r13` rates** — 11-personnel / 13-personnel grouping rates in `personnel_efficiency.py`. **Explicit non-alias.**
6. **WR11 / WR13 / WR14** — fantasy rank notes.
7. **Current `nfl_simulator.py`** (`DEFAULT_NFL_MODEL_VERSION = nfl-v1.5-matchup-sim`) — **explicit non-alias.** Binding it would invent a lineage.
8. **`docs/NFL_ENTERPRISE_GATES.md`** — product ATS/CLV/MAE floors, not this gate set.

---

## Certification runner (prepared, not executed on holdout)

`scripts/nfl/prepare_r11_r14_cert.py` is a **deterministic readiness checker**.

Default:

```bash
python3 scripts/nfl/prepare_r11_r14_cert.py
```

What it does:

- Loads lineage slots + requested gate-set dimensions + `alex_external_bind.json`
- If Academy files appear under `permanent-engine/docs/ops/`, hashes them and checks the filed **prefixes** (does not invent full sha256)
- Requires every lineage field to be present, `status=EXACT`, and `bind_allowed=true` before a compare is legal
- Hash **prefixes** and PARTIAL_EXTERNAL slots do **not** satisfy EXACT
- Prints **FAIL_CLOSED** while slots are not EXACT
- Hard-refuses `--execute-holdout`

What it does **not** do:

- Import or call `nfl_simulator.py` or any scoring equation
- Invent thresholds or complete truncated hashes
- Bind Fair Lines / PLAY / Kelly
- Rematerialize or write production artifacts

A compare of frozen R11 vs candidate R14 becomes legal only after complete EXACT lineage JSON **and** a BOUND gate set with sourced thresholds are checked in or attached. That filing is outside this lane.

---

## How to unstick (human / war-room, not this agent)

Attach or check in the Academy files with **full** sha256, plus:

- git commit + branch + worktree for each label
- runner path (not prefix-only)
- input paths **and** full hashes
- original argv
- CLOCK_PLAY freeze dirs or a stated replacement
- the five numeric metrics and sourced gate thresholds

Until then, certification stays fail-closed.
