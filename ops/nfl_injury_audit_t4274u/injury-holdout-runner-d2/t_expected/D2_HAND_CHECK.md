# D-2 hand check (filed before the runner)

Ryan `t4335s14919` / `fabf8732`: CLEAR to **build the runner**, then IMV reviews,
then open once. This package is the runner. Opening is not permitted.

**F-NAIVE:** `date_modified=2022-09-11T16:00:00` (no Z, no offset) → STOP
`D-2 listings TZ: naive/zoneless`. Do not treat as ET.

**F-INC-TS / F-INC-DELTA / F-COMP-NULL:** incomplete-row rule from request v3.1
C-2, applied on the export before join.

**F-V2-*:** pin is on-disk `.sha256.v2`. Blob `.sha256` is not a pin.

**F-JOIN-FIRST:** `join_close_or_outcome` before `apply_incomplete_row_rule` → STOP.

**F-NAME:** `Path("listings_2024.csv")` is refused on the name. The file is not
created and not opened.

**F-HOLDOUT:** `--mode holdout` dies with `D-2 opening blocked` before any
listings or export path is resolved.

**F-OK:** one incomplete id `2022_2_CCC_DDD`; listings 1×Z + 1×offset; naive=0.

**le2023:** listings 2013–2023 only, 58653 rows all `Z`; export `a38a55bb`
yields the 11 C-5 ids. No 2024/25 file is in `seeded/listings-le2023/`.
