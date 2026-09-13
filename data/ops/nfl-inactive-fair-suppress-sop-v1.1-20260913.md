# NFL inactive remat-or-failclosed — display suppress (SOP v1.1)

**Ryan ACCEPT + CoS LOCK 2026-09-13.** Product owns suppress display only.
Remat itself is **Needs CoS CLEAR** / out of scope for this wiring.

## What customers see

When a **MAJOR** inactive is known and remat has not completed, Edge Board /
assemble must **not** paint stale house fair or edge for that game. Street
quotes (open / current / books / `linesAsOf`) may still refresh.

`qb_unresolved` + MAJOR known fails **fair + edge**, not PLAY-tier only.
`qb_unresolved` alone does **not** invent a board-wide suppress.

## Canonical `gameId`

**SoT join key:** NFL fair-lines / schedule `game_id`
(example: `2026-W01-ATL@PIT`). Stamped on assemble rows as `gameId`.
Odds event ids are **not** the join key (not consistently on Edge Board rows).

Product ops may also key the flag by `AWAY@HOME` (e.g. `ATL@PIT`); the
lookup aliases to the schedule id when present.

## Manual set path (interim — no SI wire)

1. Edit `data/ops/nfl-inactive-suppress.json`:

```json
{
  "games": {
    "2026-W01-ATL@PIT": {
      "markets": [],
      "reason": "major_inactive_pending_remat",
      "players": ["Example QB"],
      "classes": ["MAJOR"],
      "setBy": "product",
      "setAt": "2026-09-13T16:00:00Z",
      "ttlUntil": "2026-09-13T23:30:00Z",
      "rematRunId": null
    }
  }
}
```

Empty `markets` = all customer fair markets (Spread / Total / Moneyline).

2. Or env (Vercel / local), highest precedence first:

- `NFL_INACTIVE_SUPPRESS_JSON` — inline store JSON
- `NFL_INACTIVE_SUPPRESS` — comma-separated game ids / `AWAY@HOME`
- `NFL_INACTIVE_SUPPRESS_PATH` — alternate JSON file

## Revoke

- Remat success: set `rematRunId` to the remat receipt `run_id` (auto-revoke).
- CoS clear: `clearedBy: "cos"` (or remove the game key).
- While suppressed without remat, receipt `rematRunId` is `"none-suppressed"`.
- TTL: explicit `ttl` / `ttlUntil`, else kickoff + 3h buffer.

## `injury_clear` wire

Missing / unknown `injury_clear` is **false** (fail closed). No silent `True`.
TS `resolveInjuryClear` + Python `resolve_injury_clear` stay mirrored.
Does not rematerialize KEI.

## Out of scope

SI→builder auto-detect, remat scripts, CFB public board, #516 / Line Curve / DFS.
