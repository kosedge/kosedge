# t5067u — Q1/J13 bitwise closure correction (covered verification)

**NOT a new experiment.** Covered check under dad9eb89 + a091ce1a.
**CERT=0 · NFL NO-GO · DRAFT #686 — do not merge.**

Adds research tests only. Does **not** regenerate `research.q2s.joint` 141 outputs.
Prior artifacts remain **5076421e** / **ce6b1244**. Prior receipts (including `RECEIPT_t5065u.md`) are not rewritten. No file named or hashed `ff921177` was present on this tree; nothing of that name was erased.

## Method (research-test only)

1. Call the **unmodified** pinned IF entrypoint `simulate_nfl_game_independent_fair` @ 6ca03716 / sim **52d9e909** / framework **a0051cc4**.
2. Trace `Random.gauss` on the already-imported stdlib module object used by that source (no production-source edits).
3. Floor the captured raw Gaussians in the **original H-then-A order**: `H0=max(0,g_even)`, `A0=max(0,g_odd)`.
4. Compare those float64 arrays to `simulate_q2s_joint(..., d=0)` for all 141.
5. Score **exact array equality** and **draw-array hash equality** separately from legacy summary (means ≤1e-12, rounded WP/ML, counts).

N=4000, `seed_for(game_id)`, no reseed, no high-N, no outcomes / 50bda875 / LOOK, J14 stays NOT EMITTED, 34 COND remain on the prior joint artifact.

## Results

| Check | PASS | FAIL | n |
|---|---|---|---|
| Exact array equality `H0/A0` vs d=0 replay | **141** | 0 | 141 |
| Draw-array hash equality | **141** | 0 | 141 |
| Legacy summary (means / WP / ML / counts) | **141** | 0 | 141 |

Tests: `python3 -m unittest research.q2s_w7w17_t5044u.joint.tests.test_q1_bitwise_d0 -v` → **4/4 OK**.

Joint outputs not regenerated:

| File | sha8 (unchanged) |
|---|---|
| `joint/artifacts/Q2S_JOINT_W7W17.json` | **5076421e** |
| `joint/artifacts/Q2S_JOINT_DRAWS_W7W17.npz` | **ce6b1244** |

Sampling COND on those artifacts is unchanged (J7a 17 · J8 3 · J9 8 · J11 6 = 34). J14 = 141 NOT EMITTED.

## Claim (this is what is now proven)

**For all 141 games, the d=0 `research.q2s.joint` H0/A0 float64 arrays are bitwise identical — exact `numpy.array_equal` and matching `paired_draw_hash` — to the floored H-then-A traces of the unmodified pinned IF generator (6ca03716 / 52d9e909 / a0051cc4). That bitwise identity is demonstrated separately from legacy summary agreement, which also PASSes on all 141 (means ≤1e-12, rounded WP/ML, win counts).**

t5065u’s earlier Q1 language that only compared summaries is **insufficient by itself** to prove bitwise identity; this addendum supplies the missing draw-array proof. No claim narrowing is required after the 141/141 exact-array result.

## Holds

No production-source edits · no seed/N change · no 50bda875 · no candidate regen · no reseed · no high-N chase · no new LOOK · J14 NOT EMITTED · 34 COND visible on prior artifacts · CERT=0 · DRAFT.
