# NFL fantasy Robinson identity — one Bijan (2026-09-02)

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-fantasy-robinson-identity-5c85`

## Live bug

Fantasy Draft Desk / mock showed two Atlanta `B.Robinson` rows both wearing Bijan’s ADP (~2).

| Board row | player_id | Model rank | Rush yds | Wrong ADP | Correct |
|-----------|-----------|------------|----------|-----------|---------|
| B.Robinson ATL RB | `00-0038542` | ~3 | ~1552 | 2 | Bijan ADP ~2 |
| B.Robinson ATL RB | `00-0037746` | ~166 | ~506 | **2 (stolen)** | Brian ADP ~142 |

Treadwell-at-1.01 was **not** reproduced (CMC #1). Identity only.

## Root cause (confirmed)

1. Draft rankings keep nflverse abbreviated `player_name` (`B.Robinson`).
2. Depth pack already has full names + same GSIS ids (Bijan RB1 / Brian Jr. RB2).
3. FantasyPros ADP: Bijan short `B. Robinson`, Brian short `B. Robinson Jr.` — both ATL RB.
4. Matcher `initial_last` correctly refused (ADP bucket length 2).
5. **Hole:** `short_name` treated Bijan’s `B. Robinson` as unique vs Brian’s Jr. variant, so **both** board `B.Robinson` rows independently matched Bijan. Not a sportsdata_id collision (board `player_uid` ≠ FP `sportsdata_id`).

## Fix

1. **Depth expand on collision** (`board-identity.ts`): when 2+ desk rows share initial+last+team+pos, replace labels with depth full names via `player_id` before ADP match + UI.
2. **Matcher harden** (`adp-match.ts`): refuse `short_name` when ADP `initial_last` for same team+pos is ambiguous; board-side collisions only allow full/core/id keys; one ADP entry → one desk row.

## Tests

- Two ATL `B.Robinson` cannot both receive ADP 2; after full-name expand, Bijan keeps ~2 and Brian keeps ~142.
- Lone abbreviated board cannot steal Bijan via Jr. short-name artifact.
- Depth expand only fires on collisions.

## Out of scope

No Fantasy tile hide, no KEI mint, paywall off, no ATD/floor/Celery changes. Rematerialize not required — web-side identity at desk load.
