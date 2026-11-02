# IMV local feature path v2.3 — ccecea74

v2.2 PASS WITH CONDITIONS. This addendum is plumbing only. Parent:
`nfl-imv-feature-path-v2.2.md`. **Do not run W7.** Mac runs allowed after
this code-check at grade **PLUMBING-ONLY**.

## Weekly averaging (reconciled)

**Code wins.** 5g and season-row rates are the **unweighted mean of weekly
rates** over the last N completed REG team-weeks. `off_plays` / `def_plays`
are summed and passed to the backbone as sample size, not as weights.
`WINDOW_5G_RULE` (last 5 played REG; bye/POST omitted) is unchanged.

## P-1 store path

Builder writes features into `--out/store`. The sealed runner resolves
`IMV_FEATURE_STORE/store` when `features.jsonl` is there. The expected sha
(`IMV_FEATURE_STORE_SHA`) is still supplied from **outside** and is the
digest of **store** (`FEATURE_STORE.sha256` copied out, never read back
from inside the store as a fallback).

## P-2 W8 window

Seal must **start** before `2026-10-29 20:15 ET` =
`2026-10-30T00:15:00Z`. Any game with `kickoff_utc <= capture_ts` is
excluded. A late start is `W8_SEAL_AFTER_DEADLINE` (no W8 snapshot).

## P-3 both helpers

`nfl_imv_v21.py` must hash to
`050271467cd38f5a174043c67f2df9622d7f0b8125f137b822f888846f4c561f`.
v22 is stamped beside it. Both land in the seal as `HELPER_V21.sha256`,
`HELPER_V22.sha256`, `HELPERS.json`.

## P-5 blocked paths

Missing / non-final nflverse scores → BLOCKED (no invented scores).
A BLOCKED feature `build-report.json` → `BLOCKED_BUILD_NO_SEALED_RUN`
(model is not called). Re-run is always a new timestamped directory.

## X-3 parity

See `nfl-imv-prod-export-spec-v2.3.md`. Until that export exists, parity
is `NOT_RUN_NO_PROD_EXPORT`.
