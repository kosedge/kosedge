# Editor Weekly Fact-Check — NFL previews & articles

**Owner:** Riley Nash (Editor)  
**Cadence:** Every Monday after Camp Desk / preview refresh, and after any market-moving desk publish.

## Command

```bash
python scripts/writers/preview-market-factcheck.py \
  --as-of YYYY-MM-DD \
  --write-ops
```

Optional: `--fix` applies market stamps only after human review of the printed mismatch table.

## SoT

| Layer | Source |
|-------|--------|
| Live market | DraftKings win totals (RotoWire / DK Network consensus) — **web scan required** |
| Model | `data/ops/nfl-web-launch-bundle.json` → `team_regular_season_outcomes.csv` `expected_wins` |
| Copy | `content/writers/season-previews-2026/*.md` |

## Pass rules (do not skip)

1. Print mismatch table (team · stated · live · Model E[wins] · Δ).
2. Send the table to the desk owner / user before silent bulk edits when Δ ≥ 1.0 win on the primary market.
3. Fix primary market in title, Market line, Handicapper’s Note, and lede asks.
4. Recalibrate lean: thin |fair − market| (~≤0.5) or material Model↔market conflict → **Pass**.
5. Write `data/ops/nfl-preview-factcheck-YYYYMMDD.md`.

## Integration

Writers ship copy. Editor closes the loop. See `riley-nash.md` and `.cursor/rules/ai-writer-team.mdc`.
