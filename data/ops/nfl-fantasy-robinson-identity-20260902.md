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

## Fix (PR #411)

1. **Depth expand on collision** (`board-identity.ts`): when 2+ desk rows share initial+last+team+pos, replace labels with depth full names via `player_id` before ADP match + UI.
2. **Matcher harden** (`adp-match.ts`): refuse `short_name` when ADP `initial_last` for same team+pos is ambiguous; identical board labels only allow full/core/id keys; one ADP entry → one desk row.

## Follow-up (post-411 live — this PR)

Matcher refuse worked (no dual ADP 2) but **both** ADPs went to `—` and names stayed `B.Robinson`. Cause: Vercel NFT never shipped `services/model-service/.../nfl_depth_chart_2026_w1.json` for fantasy routes, so `loadNfl2026DepthRows()` returned `[]` and expand never ran.

**Finish expand in production:**

1. Package depth under `apps/web/lib/fantasy/data/nfl-depth-chart-2026-w1.json` (static import fallback).
2. NFT `outputFileTracingIncludes` for `/pro/nfl/fantasy/**`.
3. Board ambiguity gate uses **identical labels**, not mere initial+last — after expand, Bijan/Brian full names uniquely match ADP ~2 / ~142.

## Tests

- Two ATL `B.Robinson` cannot both receive ADP 2; after full-name expand, Bijan keeps ~2 and Brian keeps ~142.
- Lone abbreviated board cannot steal Bijan via Jr. short-name artifact.
- Depth expand only fires on collisions.
- Packaged depth loads ATL Robinsons and completes expand→ADP pipe.

## Out of scope

No Fantasy tile hide, no KEI mint, paywall off, no ATD/floor/Celery changes. Rematerialize not required — web-side identity at desk load.
