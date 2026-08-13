# NFL Daily Intel OS — runbook

**As of:** 2026-08-13  
**SoT:** one pack — `services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json`  
**KEI:** Gate B read-time reprice (`nfl_kei_week1_reprice`) on `/nfl/fair-lines`  
**Never:** a second depth map · auto-100k · Twitter/X as the sole source

## Cadence

| When | Action |
|------|--------|
| Morning camp / beat sweep | Expert note → SoT candidate overrides (this file) |
| Tue–Wed injury reports | Update `injury_status` / `ol_roles` on the pack (`kei_only` or `sot`) |
| Thu–Fri final injury (4pm ET class) | SoT write + KEI refresh (fair-lines read picks it up). Optional: `scripts/nfl/injury_kei_reprice.py --window friday_final --dry-run` |
| Gameday inactives | Late KEI only; Model snapshot stays. `injury_kei_reprice.py --window gameday_inactives` |
| After depth / QB identity change | Flag **research republish recommended** — do not auto-100k |

## Sources (order)

1. Team site / official injury report  
2. Reputable beat (club beat, AP, NFL Network)  
3. RotoWire / similar desk wire  
4. VSiN-class market desk (for *price* context, not identity)  

Twitter/X may **corroborate** only. It is never the sole source on an override row.

## Override table format

JSON object:

```json
{
  "as_of": "2026-08-13",
  "approved_by": "desk",
  "overrides": [
    {
      "team": "WAS",
      "player_name": "Laremy Tunsil",
      "player_id": "WAS-LT-OUT",
      "position": "LT",
      "layer": "ol_roles",
      "field": "injury_status",
      "before": "out",
      "after": "out",
      "reason": "torn triceps — already SoT; example row",
      "as_of": "2026-08-13",
      "confidence": "high",
      "destination": "kei_only",
      "sources": ["https://…"]
    }
  ]
}
```

Required per row: `team`, `field`, `before` (or null if unset), `after`, `reason`, `as_of`, `confidence`, `destination`.

`layer`: `rows` (skill) or `ol_roles`.

## What goes where

| Destination | Write pack? | KEI moves? | 100k |
|-------------|-------------|------------|------|
| `kei_only` | Yes (injury / competition the frozen model missed) | Yes, next fair-lines read | No |
| `sot` | Yes (identity / depth / injury) | Yes if KEI reads that field | **Republish recommended** for QB/identity |
| `wait_republish` | No | No | Human republish first |

## CLI

```bash
# Dry-run (default): print applied/skipped + Week 1 KEI smoke for touched teams
python scripts/nfl/apply_daily_intel_overrides.py \
  --overrides data/ops/nfl-daily-intel/sample-override.example.json --dry-run

# Write the one pack (refuses fixture files unless --allow-fixture)
python scripts/nfl/apply_daily_intel_overrides.py \
  --overrides path/to/approved.json --write
```

Smoke prints who moved (game, Δspread, new KEI drivers). Model is not rewritten.

## After a QB identity change

1. Override with `destination: sot` (or `wait_republish` until you are sure).  
2. Script prints `RESEARCH REPUBLISH RECOMMENDED`.  
3. When 100k is green: `scripts/nfl/publish_launch_research_to_web.py` after ATL Tua / MIA Willis checksum.  
4. Do not quote season win totals for dual-map teams until that publish.
