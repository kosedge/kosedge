# COS ORDER — t5129u BYTE REHASH RETURN-FIX

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · NO EVAL EXEC
Authority: Alex RETURN **f5788f7c** on tip `f4f6e311` / HEAD `2847ffc1`
OWNER CLEAR t5129u **31131644** · this ORDER **RETURN-FIX**
Stay on #693. Do not race/write R2-A coverage files.

## Gaps (fix ALL)

1. Bind R2 byte hashes (`bind_id` + freeze / manifest / extract hash sets) into **ONE_RUN**. `verify_one_run` before claim. Mutate + fresh side rebind must **REFUSE** (not ACCEPT with loader 1).
2. Tie freeze **file** bytes to `frozen.payload` — derive/verify from file bytes in-path. Unrelated file + rebind must refuse.
3. Enumerate admitted extracts from hashed **manifest contents**. Refuse if caller-supplied set ≠ manifest set.
4. Pre-claim market-completeness refuse when market incomplete for the eligible cohort (loader 0, no claim). IF-only must not claim then fail (look burn).
5. Keep addendum in repo path CoS can seal to `ops/`.

Preserve first-case / DEV437 / t5116u FAILED. G5 / KO−60 / ≤24h / DK-FD unchanged.

order_sha8: `2a099402`
