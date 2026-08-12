# NFL truth labels — no Week 18 / dual-season confusion

Date: 2026-08-12  
Branch: `feat/nfl-truth-labels-preseason`  
Doctrine: Every research surface states what reality it is showing. August must not read as “2026 Week 18 current.”

## Contract

Shared helper: `apps/web/lib/nfl-truth-label.ts`

| Field | Behavior |
|-------|----------|
| season | e.g. 2026 |
| week | real REG week, or **null** when the label is Preseason / finals |
| week_label | **Preseason**, `Week N`, or `{season} finals` — never a future completed week |
| ui_state | **LIVE** \| **MODEL** \| **PRESEASON** \| **ARCHIVE** |
| source_type | actual \| model \| preseason \| archive \| fallback |
| is_current | true only for in-season LIVE |
| run_id / model_version / generated_at | stamped when model numbers are shown (via `NflLineageBadge`) |

Calendar cutoff matches season-engine `PRESEASON_CUTOFF_BY_SEASON` (2026-09-07 inclusive). REG Week 1 2026 is Thursday 2026-09-10.

## Pages touched

| Surface | Change |
|---------|--------|
| Depth / Stats / Rosters / Injuries (`NflIntelTablePage`) | PRESEASON/ARCHIVE badge; period line; honesty note. No `2026 W18 (as-of)`. |
| Team directory `/pro/nfl/teams` | Period line + record column labeled as prior W–L when archive |
| Team hub `/pro/nfl/teams/[team]/[view]` | Same; filter week omitted when Preseason so the dropdown is not stuck on 18 |
| Standings | `2025 W–L` vs `2026 E[wins]` / `2026 Playoff %`; ARCHIVE+MODEL or PRESEASON+MODEL; sort by E[wins] before LIVE |
| Stats fallback (empty intel) | PRESEASON+MODEL + lineage; model column headers |
| Injuries copy | As-of honesty; no “Not current · W18” |
| Power ratings | PRESEASON+MODEL badges |
| Freshness banner | `S2026 Preseason` instead of `S2026 W18` |
| Team intel week filter | “Latest” → **Preseason** before REG Week 1 |
| Edge Board / weekly slate | Board week helper; no REG Week 18 title in August |
| Props header | Week label goes through the same helper (label only; no engine change) |

## Smoke (2026-08-12)

- Depth: Season 2026 · **Preseason** · PRESEASON — no Week 18
- Stats: intel table or MODEL fallback — no W18-as-current
- Team hub (e.g. LAR): Preseason period line; 2025 W–L labeled if archive
- Standings: 2025 W–L column beside 2026 E[wins] (MODEL) — not mixed as one current table

## Non-goals (unchanged)

New data feeds, fantasy ranking changes, props eligibility engine.
