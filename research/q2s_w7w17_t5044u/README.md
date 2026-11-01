# t5044u — 2017 REG W7–W17 Q2s inputs (Phase 1 only)

**RETRO_FIT / DEV_RESEARCH · A1 · CERT=0 · NFL NO-GO · DRAFT**

Cite **12763c08 · 189ed49d · 8be58684 · 51d02c20 · d7e0a6bc · 2db90f76 · 404a4ab2 · 4334b7a3**.

NEW bounded package. Does **not** amend [#685](https://github.com/kosedge/kosedge/pull/685) look/guard artifacts. No merge. No fetch/spend. No IF invoke. No `research.q2s` emit. No freeze-for-look. No comparison.

## Phase 1 status (this PR)

| Gate | Result |
|---|---|
| 1 Identity seal | **PASS** — 165/165 scheduled identities from games `4fe1cdd7`, sealed before PBP |
| 2 Reconstruct | **STOP** — PBP `84eacd96` **not on this VM** (no fetch). W7–W8 reused from owned Stage B #674 after hash match. W9–W17 not reconstructed. |

Stop for **Alex pre-IF**. Phases 3–6 are design-only in `later_phases/FREEZE_DESIGN.md`.

## Completeness (this run)

| Class | N | Reason |
|---:|---:|---|
| Identity sealed | 165 | all 4fe1cdd7 2017 REG W7–W17 |
| Complete 27/27 (recon available) | 22 | Stage B W7–W8 reuse |
| Partial T2 (recon available) | 6 | sealed bye-return; cells retained missing |
| Recon not attempted | 137 | W9–W17; PBP `84eacd96` absent |
| Outcome-excluded | 0 | forbidden |
| Unexpected missing | 0 | — |

Combined identity selection hash: `41f211b639f39f98f8630f6774181dc9faaaeac34c9d67f486d0a16bae1dad3c`.

W7 hash `6030f79c…` and W8 hash `3bf4a0dc…` match Stage B t4923u.

## Reproduce (Phase 1)

```bash
python3 research/q2s_w7w17_t5044u/gate1/seal_identities.py
python3 research/q2s_w7w17_t5044u/gate2/run_gate2.py
python3 research/q2s_w7w17_t5044u/tests/test_gate1_identity_seal.py -v
python3 research/q2s_w7w17_t5044u/tests/test_gate2_stop_and_reuse.py -v
```

Gate 1 aborts if PBP is already remounted. Gate 2 writes the PBP blocker and transfers W7–W8 only.

## Locks

≠IF @ 6ca03716 ≠Q2s emit ≠Appendix O ≠re-look 70 ≠reopen 03a4dd90 ≠1ee90fac score ≠merge ≠deploy ≠broad Stage C ≠fetch/spend
