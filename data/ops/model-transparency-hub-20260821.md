# Model Transparency Hub (2026-08-21)

One page owns model / KEI / surface explanation. Product boards stay clean.

## Why

Methodology copy was repeating on Edge Board, Overview, Survivor, Fantasy, KEI Lines, launch-notes, and Props. Users who wanted to use the tool were wading through governance. Users who wanted the contract had no single SoT besides the backtest-heavy old `/pro/model-transparency`.

## What shipped

| Surface | Change |
|---------|--------|
| `/pro/model-transparency` | Contract + what we show/don't + anchorable surface glossary. Held-out NFL check stays below (accurate, not a freshness clock). Public URL (200 without Pro wall). |
| More tools / overview footer | Label **Model Transparency** (was Model Health). Quiet text links on boards — no new banner essays. |
| Edge Board | One-line Model vs KEI honesty + hub link. Dropped “How to read the desk”. |
| Survivor / Game Boxes / Season Model | Short summaries. SportHubShell quiet hub link. Interactive vs research-lock notice: research ≥2k; interactive is labeled low-depth. |
| Fantasy | Keep Model rank ≠ pick order + ADP freshness. Hub link. Methods stay collapsed. |
| KEI Lines / Props / Camp / CFB overview | Essays stripped; one-line honesty + hub link. |
| `/pro/nfl/launch-notes` | Thin pointer to the hub (URL kept, still public). |

Glossary covers: Edge Board, KEI Lines, Weekly slate, Survivor, Fantasy, Game Boxes / Season Model, Power Ratings, Camp Desk / Injuries, Insights / Doctrine, Props (live).

## Non-goals (unchanged)

Engine / KEI math, new calibration claims, Disclaimer/Terms rewrite, Insights overhaul, loud header links on every page.

## Smoke

```bash
# Hub
curl -sI https://www.kosedge.com/pro/model-transparency | head -n 5
# expect 200; page has Core contract + #glossary + #edge-board … #props

# Boards no longer carry the removed essays
# /edge-board/nfl — no “How to read the desk”
# /pro/nfl/survivor — short planner summary, not SOS/path essay
# /pro/nfl/fantasy — Model rank one-liner only, not a methods wall
# /pro/nfl/overview — no dual launch-notes CTAs
```

Rollback: revert this PR. `/pro/nfl/launch-notes` still exists as a pointer.
