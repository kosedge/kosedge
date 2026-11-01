# q2pb keep-symbol copy (t5033u)

Byte-identical copy of the #682 / #679 `q2pb` keep packet so this
Layer-2 adapter can reuse `asof_for_targets`, `asof_wl_diff`, and
`assert_asof_leakage` without merging those drafts and without
rewriting sealed writer `emit_q2_asof_sidecar.py`.

Do not treat this copy as a second writer. Coefficients stay sealed
(`a_q2` / `b_q2` on fit `70db070d`). No refit.
