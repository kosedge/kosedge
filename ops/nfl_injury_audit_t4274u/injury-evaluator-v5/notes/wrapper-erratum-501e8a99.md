# W-1 wrapper erratum (cited 501e8a99)

Filed before any v5 scorer run. Ruling cited `d18ebf22`; this erratum cited `501e8a99`.
Original erratum bytes were not on this box; the required disclosure is written here.

## Disclosure

The Path 1 wrapper `write_sealed_injury_export_ts_v1.py` does **not** call frozen `main()`.
It re-implements the frozen `main()` apply/export path:

- imports frozen `8d188da2` helpers and `8e2a15ac` / `ff8e6527` contract
- skips `_assert_run_invariants` (HEAD is not `8e2a15ac` on this branch)
- skips the 729-point Spec C grid search
- evaluates Spec A, Spec B (theta grid), and the frozen selected Spec C params
- reconstructs `fit_object` with the frozen `created_at` so the sealed sha is `6a5490db`
- writes a **new** export `sealed_injury_export_ts_v1.json`

## Float overwrite

The wrapper overwrote **320** floats to the frozen bit-pattern (IMV count).
Max abs diff **1.07e-14**.

Package observation on the Path 1 run:

- 318 `delta_margin` values in the export (max abs 1.0658141036401503e-14)
- 2 `fit_object` MAE floats after ULP canonicalize (`spec_C.f2_validate.mae_margin`, `spec_C.mean_inner_mae_margin` on the successful write; Spec A/B also ULP-matched in the prior pass)

318 + 2 = 320. Old fields are byte-identical to `d87e6129`. The new on-disk export pin is `a38a55bb`. Blob hash `46d2a565` is **not** a pin.

Frozen `sealed_injury_export.json` (`d87e6129`) was never edited.
