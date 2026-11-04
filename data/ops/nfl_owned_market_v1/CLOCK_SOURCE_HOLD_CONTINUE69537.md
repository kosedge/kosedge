# CLOCK / SOURCE-VALUE LINEAGE — HOLD (CONTINUE 69537)

CERT=0. t5320u under 86257 / 47318 / 58426. Cos-host PAUSED.
`owned_completion_claimed=false`. Freeze unverified timestamps **not** marked verified.

## GATE0

PASS · 245.325142 GiB free on `/dev/vdc` · host `cursor` · worker `bc-02a716be`.
Receipt: `START_PREFLIGHT_CONTINUE69537_B.md`
sha256 `d144749a13dc522d0987f2e1152e9468dd380216b0c40efa920d241ec3966bc1`.

## Source status: HOLD

No permitted clock/source-value lineage object is **EXISTING AND VERIFIED** on this Cursor host.

The Cos-checked originals remain:

| locator | Cos status | clock contract |
|---|---|---|
| `7834cbc7:data/ops/nfl-t5155u-r5-phase1/MARKET_ARM_FREEZE.json#limitations` | EXISTING AND VERIFIED as freeze (96/496/400) | `publication_timestamp_status=unverified` · `observation_timestamp_status=unverified` |
| `7834cbc7:data/ops/nfl-t5119u-r2-owned-coverage/t5136u_B1/ADMISSIBLE_QUOTES_B1.jsonl` | EXISTING AND VERIFIED sha256 `b4a3a4db…` as quote universe | clock **fields exist** (`captured_at`,`cutoff_utc`,`kickoff_utc`) — **not** a verified publication/observation contract; freeze forbids treating them as verified |

Not used (would be a **new** source, or same HOLD):

| object | why not a permitted verified clock source |
|---|---|
| `7834cbc7:data/ops/nfl-t5157u-r5-history-id/JOIN_PROVENANCE.json` | not in Cos EXISTING AND VERIFIED set for this market arm; also `publication_timestamp_status=unverified` / `observation_timestamp_status=unverified`; PBP/history-id join, not selected-187 clock |
| invented `clock_provenance.json` | forbidden |
| Cos host / DB / API / 2022–23 quote values | forbidden |

## Exact blocker (unchanged)

`7834cbc79226e44fa3bd625e1eb526e9a800a128:data/ops/nfl-t5155u-r5-phase1/MARKET_ARM_FREEZE.json#limitations`

- field `publication_timestamp_status` = `unverified`
- field `observation_timestamp_status` = `unverified`

No new sources. No invented fields. No Cos staging.

## Preserved

187 identities / 400 IDs · ADMISSIBLE@7834cbc7 · FREEZE 96/496 · synthetic risk1 · Cos 3b9549a5.
