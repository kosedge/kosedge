# FREEZE_ADDENDUM — t5035u (Alex RETURN `404a4ab2`)

**RETRO_FIT / DEV_RESEARCH · CERT=0 · NFL NO-GO · DRAFT**

Cite t5035u · `404a4ab2` · `d47934ca`. Parent t5033u / PR #685 executed
head `672d7957`.

## M1

`PROTOCOL_FREEZE` omitted the scored `q2s` rows. `compare_appendix_o.py`
only tested `FREEZE.exists()` and never re-hashed.

## What this addendum does

- Binds emitted rows sha
  `0d6a5e144ef13c3ebe65d601404445909fb3f504ec3e9e34b101db643b8423ae`
  (prefix `0d6a5e14`).
- Does **not** rewrite original `PROTOCOL_FREEZE` or Appendix O result
  artifacts.
- Authorizes one post-look guard amend of `compare_appendix_o.py` so the
  compare caller re-hashes every freeze entry and this rows pin.
- No second look. No weight change. ΔMAE artifacts stay byte-identical.

Machine record: `artifacts/FREEZE_ADDENDUM.json`.
