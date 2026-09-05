# B2-PACE-v1 Phase 2.5 — Holdout governance recommendation

## Locked interpretation (unchanged)

- B2-PACE-v1 fixes a confirmed dimensional defect.
- Train-A ΔMAE vs C0 = −0.449, 95% CI [−0.562, −0.336].
- Still trails B1: ΔMAE = +0.314, 95% CI [+0.232, +0.394].
- Calibration 0.703 → 1.013.
- Successful unit correction; **not** evidence B1 is beaten.
- Non-default research challenger only.

## Do not unseal merely because n may exceed 100

Before any unseal, require **all** of:

1. Complete PIT-valid input intersection (odds B1 open/close + PIT KenPom AdjEM+AdjT + Schedule SoT outcomes + B7 + venue_status).
2. Reliable venue handling **or** a pre-registered unknown-venue policy (fail-closed).
3. Frozen candidate code + content hashes (formula bytes + Train-A manifests).
4. Green canonical CI for the Lab Python surface (boundary + pipeline pytest). Ruff is **not** in declared deps — do not greenwash with an unpinned install; fix infra separately if Ruff is required.
5. Frozen primary + secondary endpoints.
6. Explicit acknowledgment that Test-A is exposed for both pace and open-shrink hypotheses.
7. One-shot evaluator that writes an immutable receipt.
8. Explicit Ryan authorization in a **separate** phase.

## Hierarchical preregistration (if both challengers share one holdout)

If both B2-PACE-v1 and a future B2-PACE-NEUTRAL-v1 will be scored on the same holdout, preregister **before** unseal:

1. Primary: B2-PACE-v1 vs B1 (paired ΔMAE).
2. Secondary (only if primary gate met, or as descriptive): B2-PACE-NEUTRAL-v1 vs B2-PACE-v1 and vs B1.
3. Multiplicity rule fixed in advance (e.g. hierarchical: NEUTRAL only interpreted if PACE clears primary; or simultaneous with Bonferroni on secondary).
4. Do **not** inspect holdout results and then add the neutral candidate.

## Current holdout verdict

**NO VALID UNTOUCHED OOS WINDOW CURRENTLY MATERIALIZABLE**

Pocket 2025 is **PARTIAL_COVERAGE** (odds tips 2025-11-03 → 2025-12-06 only; Dec 7–31 not covered; zero PIT KenPom; no schedule pack).

## Recommended next atomic phase

**Phase 2.6 — PIT data foundation (ingest design → controlled capture), not another challenger.**

1. Implement/schedule the KenPom + Schedule SoT + venue_status ingestion architecture (design already in `docs/lab/NCAAM_PIT_INGESTION_ARCHITECTURE_v1.md`) for the **upcoming** season — contemporaneous capture only.
2. Optional: Ryan-local inventory of offline odds/KenPom/schedule packs (USER_CONFIRMED_OWNED_OFFLINE; cloud agent does not access the drive).
3. Only after a PIT-valid sealed window exists: separate authorization phase for hierarchical prereg + one-shot unseal.

Do **not**: implement B2-PACE-NEUTRAL-v1 yet; score Test-A/pocket; merge/deploy/promote; change formula; wire as default.
