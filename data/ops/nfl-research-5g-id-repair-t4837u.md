# t4837u — research-only deterministic ID repair (DRAFT)

Authority: DECISION_RYAN_t4837u **e08cae8c** · Accept Alex **94ccd2b1** ·
ORDER attached · base tip **640c988d** · prior artifact **2454f094** ·
as-of CLOSED **cf514078**. Behind W8/E1; W8 STANDBY.

**Status:** DRAFT research rematerialize only. ≠admit ≠merge ≠acquisition
≠weights ≠scoring ≠E1 ≠bye contiguous `_5g` rewrite ≠commercial.
NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen.

## Seal (new)

| Item | Value |
|---|---|
| Artifact | `data/research/nfl/t4833u/snap_share_5g_exposure_ledger.parquet` |
| Prior sha256 | `2454f0948a649e02f4319a4ae07fa173327a7a895fae6d3be0b2397318001f88` |
| **New sha256** | `efb97fac3b5078699ca90714886a0cbb3c2819790e7f4733618271db0fc9a1d3` |
| Rows / cols / bytes | 3,356 / 57 / 266,137 |
| Schema | `research-snap-share-5g-exposure-ledger-v0-t4837u` |

Input pins unchanged (no additional acquisition): snap `81a1e6f5…` · players
`b6dd0c86…` · roster `7ba8d815…`.

## Unique IDs vs mirrored flags (do not conflate)

The 19 corrections are **19 player-game identities on 3 players**, not 38
players and not 38 windows. Each repaired snap identity had a roster
ACT-absent **mirror** (same person, pfr-null roster row). Clearing both
grains moves residual flags by −38.

| Player | PFR | Resolved GSIS | Snap IDs repaired | Mirror UNKNOWN cleared | Flag Δ |
|---|---|---|---|---|---|
| Alec Anderson BUF | AndeAl01 | `00-0037428` | 6 | 6 | −12 |
| Cody White LV | WhitCo05 | `00-0035891` | 7 | 7 | −14 |
| Peter Woods KC | WoodPe00 | roster `00-0041545` | 6 | 6 | −12 |
| **Unique identities** | **3 players** | | **19** | **19** | **−38** |

Woods: players-source `WOO547869` preserved on `player_gsis_id_players` for
audit. Repair provenance on repaired window rows (`id_repair_ticket=t4837u`,
`id_state_before_repair`, `id_gsis_resolved_from`).

**OkoyCJ00 / CJ Okoye stays unresolved (5 residual + 2 window rows).**
No Basil Okoye guess.

**~306 remaining ACT-absent UNKNOWN stay UNKNOWN.** Not converted to
verified_zero or measured.

## Residual before → after

| Residual | Before (2454f094) | After (efb97fac) |
|---|---|---|
| Total | **349** | **311** |
| unresolved_identity | 18 | **5** (OkoyCJ00 only) |
| conflict | 6 | **0** |
| unknown (ACT-absent) | 325 | **306** |

Windows: **52** unchanged (6 W−1-bye skips unchanged). As-of unchanged:
completed + `game_date <` target; `rating_week = target_week - 1`; target
excluded. `research_only=true` · `admitted=false`.

Window quality (Alex expected): measured 2624→2628; unresolved 5→2
(Okoye NYG W6/W7); conflict 2→0.

## Tests

```bash
cd services/model-service
PYTHONPATH=. python3 -m pytest -q \
  tests/test_nfl_research_5g_exposure.py \
  tests/test_nfl_if_pregame_asof.py \
  tests/test_nfl_snap_share_exposure_ledger.py
```

Allowlist is explicit (3 PFR ids). Not a general name matcher.
Production `nfl_snap_share_exposure_ledger` builder unchanged (still
fail-closed).
