# q2pb keep-symbol copy (t5029u)

Byte-identical copy of the #682 / #679 `q2pb` keep packet **only** so
this adapter can reuse `assert_asof_leakage` (refuse-on-fail).

The Lane A adapter must **not** call `asof_for_targets` or rewrite
ratings. Do not treat this copy as a second writer.
