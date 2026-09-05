# Holdout feasibility matrix (Phase 2.5)

**Performance metrics computed: NO. Outcome values inspected: NO.**

## Verdict

**NO VALID UNTOUCHED OOS WINDOW CURRENTLY MATERIALIZABLE**

Although archive KenPom snapshots and odds exist for some post-Test-A calendar ranges, no window simultaneously has (1) PIT KenPom AdjEM+AdjT, (2) complete Schedule SoT outcome+venue+B7 packs, and (3) sealed/unscored status suitable for confirmation. Pocket 2025 lacks KenPom entirely and has only partial odds coverage through 2025-12-06. Remaining 2023-24 and full 2024-25 lack complete Schedule SoT packs in-repo.

## Pocket reclassification

- Configured label: 2025-11-01 → 2025-12-31
- Accurate class: **PARTIAL_COVERAGE**
- Odds tips observed: 2025-11-03 → 2025-12-06
- Dec 7–31: **NOT covered** by current odds lake

## Windows

### post_test_a_remaining_2023_24
- Bounds: ['2024-01-29', '2024-04-15']
- Odds events: 2288 (tips 2024-01-29→2024-04-09)
- B1 open/close: 2288/2288
- PIT KenPom snapshots in window: 9
- Schedule SoT outcomes: PARTIAL_PACK_TIP_MAX_2024-01-29
- Venue: PRESENT_IN_PACKS:['2023_24']
- B7: PRESENT_IN_PACKS:['2023_24']
- Expected eligible: NOT_MATERIALIZABLE
- Prior metrics on window: False
- Seal: UNSEALED_CANDIDATE_NOT_SCORED_BY_B2_PACE
- Blockers: SCHEDULE_SOT_INCOMPLETE_OR_ABSENT
- External drive: OPTIONAL_IF_CLOUD_ODDS_COMPLETE

### full_2024_25
- Bounds: ['2024-11-01', '2025-04-15']
- Odds events: 5758 (tips 2024-11-04→2025-04-08)
- B1 open/close: 5758/5758
- PIT KenPom snapshots in window: 21
- Schedule SoT outcomes: NO_SCHEDULE_PACK
- Venue: NO_SCHEDULE_PACK
- B7: NO_SCHEDULE_PACK
- Expected eligible: NOT_MATERIALIZABLE
- Prior metrics on window: False
- Seal: UNSEALED_CANDIDATE_NOT_SCORED_BY_B2_PACE
- Blockers: SCHEDULE_SOT_INCOMPLETE_OR_ABSENT
- External drive: OPTIONAL_IF_CLOUD_ODDS_COMPLETE

### pocket_2025_configured_label
- Bounds: ['2025-11-01', '2025-12-31']
- Odds events: 1287 (tips 2025-11-03→2025-12-06)
- B1 open/close: 1287/1287
- PIT KenPom snapshots in window: 0
- Schedule SoT outcomes: NO_SCHEDULE_PACK
- Venue: NO_SCHEDULE_PACK
- B7: NO_SCHEDULE_PACK
- Expected eligible: NOT_MATERIALIZABLE
- Prior metrics on window: False
- Seal: SEALED_PROTOCOL_EXCLUDED
- Blockers: MISSING_PIT_KENPOM_SNAPSHOTS, SCHEDULE_SOT_INCOMPLETE_OR_ABSENT
- External drive: MAY_HOLD_ADDITIONAL_ODDS_OR_SNAPSHOTS_UNVERIFIED

### pocket_2025_odds_observed_partial
- Bounds: ['2025-11-03', '2025-12-06']
- Odds events: 1287 (tips 2025-11-03→2025-12-06)
- B1 open/close: 1287/1287
- PIT KenPom snapshots in window: 0
- Schedule SoT outcomes: NO_SCHEDULE_PACK
- Venue: NO_SCHEDULE_PACK
- B7: NO_SCHEDULE_PACK
- Expected eligible: NOT_MATERIALIZABLE
- Prior metrics on window: False
- Seal: SEALED_PARTIAL_COVERAGE
- Blockers: MISSING_PIT_KENPOM_SNAPSHOTS, SCHEDULE_SOT_INCOMPLETE_OR_ABSENT
- External drive: MAY_HOLD_ADDITIONAL_ODDS_BEYOND_DEC6_UNVERIFIED

### post_pocket_2026_jan_mar
- Bounds: ['2026-01-01', '2026-03-31']
- Odds events: 0 (tips None→None)
- B1 open/close: 0/0
- PIT KenPom snapshots in window: 0
- Schedule SoT outcomes: NO_SCHEDULE_PACK
- Venue: NO_SCHEDULE_PACK
- B7: NO_SCHEDULE_PACK
- Expected eligible: NOT_MATERIALIZABLE
- Prior metrics on window: False
- Seal: NO_DATA
- Blockers: MISSING_PIT_KENPOM_SNAPSHOTS, SCHEDULE_SOT_INCOMPLETE_OR_ABSENT, NO_ODDS_EVENTS_IN_CLOUD_LAKE
- External drive: UNKNOWN

## Offline archive

- Odds: USER_CONFIRMED_OWNED_OFFLINE / cloud NOT_PRESENT / schema OFFLINE_UNVERIFIED
- KenPom PIT / Schedule SoT on offline drive: UNCONFIRMED_POSSIBLE
- No API credits requested; no external-drive access attempted.

