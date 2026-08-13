# NFL go-mode closeout — 2026-08-13

**PR:** `feat/nfl-gomode-closeout-daily-intel` → `deploy-vercel`  
**Depends on:** #220 SoT (merged), #221 Gate B KEI reprice (merged `a56106ca`)

## Posture

NFL is **go-mode**, not a soft launch:

- One SoT pack (named skill + `ol_roles`)
- KEI = model + Week 1 desk factors (Gate B)
- Edge / Tag = KEI vs market
- Daily intel → same pack → KEI, without a model rewrite

## Before / after copy

| Surface | Before | After |
|---------|--------|--------|
| Overview CTAs | Soft Launch Notes | How to read the desk |
| Overview header | Week 1 live; PRE off | `Week 1 REG live · PRE off board · KEI = model + desk factors` + guest path **Edge Board → Survivor → Fantasy → Season Model** |
| Edge Board subtitle | Soft Launch Notes | How to read the desk |
| Launch notes page | “NFL Desk — Soft Launch Notes” | “How to read the NFL desk” (URL `/pro/nfl/launch-notes` kept) |
| Guest hub walkthrough | Fantasy Mock → … Camp | Edge Board → Survivor → Fantasy → Season Model |
| Freshness banner | `injuries:stale` → “Data freshness degraded” | Residual honesty: no live injury API is **not** board degradation. Weather remains a KEI stub (`weather not applied`) |
| Survivor / model banner | (already SoT after #220) | Unchanged: packaged named SoT, not “synthetic roles until live feeds” |

Non-NFL props copy may still say “soft launch” (CFB/MLB) — out of scope.

## Daily Intel OS

- Runbook: `data/ops/nfl-daily-intel-runbook.md`
- CLI: `scripts/nfl/apply_daily_intel_overrides.py`
- Code: `nfl_daily_intel.py` — mutates the **one** pack
- Sample (fixture, `--write` refused): `data/ops/nfl-daily-intel/sample-override.example.json`

## Week 1 desk smoke

Automated (`tests/test_nfl_week1_desk_smoke.py`):

- 16 REG games; PRE not mixed
- Model present; KEI ≠ model count > 0
- ATL open_competition · MIA Willis named · MIN Kyler named · CLE open_competition

Human (not CI) — spot-check 4–6:

| Game | Look at |
|------|---------|
| WAS @ PHI | Tunsil + Allegretti; Bates TE3 not stacked |
| MIA @ LV | Willis named; 3-band travel |
| ATL @ PIT | Tua/Penix open_competition; no fake spread |
| NE @ SEA | Cross-country travel |
| CLE @ JAX | Watson/Sanders open_competition |
| GB @ MIN | Kyler named; indoor OK identity |

Record: model / KEI / market / factors.

## 100k handoff (does not block this PR)

| Item | Path / status |
|------|----------------|
| Progress pointer | `data/ops/nfl-100k-expert-sim-candidate-progress.json` |
| Log | `data/ops/nfl-100k-expert-sim-candidate-20260813T121719Z-run.log` |
| Out dir | `data/ops/nfl-season-engine-launch-nfl-season-engine-v1.27-kicker-layer-Nteam100000-Nplayer1000-20260813T121720Z/` |
| Team W/L 100k | **Complete** (log: 7/7 chunks, ~47 min) |
| Player 1000 | **Incomplete** — stalled ~200/1000; pid 21770 not running |
| Publish (when green) | `python scripts/nfl/publish_launch_research_to_web.py` after checksum **ATL = Tua / MIA = Willis** |
| Until then | Do not quote ATL/MIA season win totals (old research is dual-map world) |

Restart of player sims is a **separate** ops action, not this closeout.

## Tests

- `test_nfl_daily_intel.py` — sample override changes pack + WAS@PHI KEI drivers; wait_republish / QB republish flags
- `test_nfl_week1_desk_smoke.py` — Gate A/B smoke
- `nfl-data-freshness.test.ts` — injuries residual does not show degraded banner

## After this

1. Human + Grok: 4–6 game spot-check  
2. Finish/publish 100k when green  
3. Optional Gate B.1 weather/refs when a feed exists
