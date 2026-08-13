# 2026 preseason model lock

**Date:** 2026-08-13  
**Pin:** `nfl-season-engine-2026-preseason-lock`  
**Web bundle:** `nfl-preseason-sim-2026-20260813T214500Z`  
**Research source:** `nfl-season-engine-launch-nfl-season-engine-v1.27-kicker-layer-Nteam100000-Nplayer1000-20260813T193726Z`  
**N:** team W/L **100,000** (6 workers, 2978.8s, Σ wins=271.9999) · player paths **1,000** (1664.9s)  
**Release gate:** **PASS** (`data/ops/nfl-preseason-release-gate-20260813.md`)

This is the **2026 preseason model**. Identity PRs #229 (Walker→KC) and #230 (pack vs FP `CLEAR_ERROR=0`) are on `deploy-vercel`. Feature volume, release gate, coherent resim, and pin are in this lock. **Stop model invention.** Next work is operate + the NFL automation queue.

## Frozen (do not invent new layers)

| Piece | Locked as |
|-------|-----------|
| Engine | `nfl-season-engine-v1.27-kicker-layer` (no new EPA / OL / doctrine) |
| Depth pack | Walker **KC** RB1 · Charbonnet **SEA** RB1 · Evans **SF** · Egbuka **TB** |
| Checksum QBs | Tua ATL / Willis MIA / Kyler MIN / ARI ≠ Kyler (Brissett) |
| Team W/L | 100k packaged wall-chart paths · Σ wins = 272 |
| Player board | 1k path-coherent sims + role-aware shape + Walker-class rush floors |
| Rush conservation | League rush **59,990.6** (engine pool; not a 64k CSV invent) |
| Pack vs market | `CLEAR_ERROR=0` |
| Weekly player props | **Gated** (`NFL_WEEKLY_PROPS_LIVE = false`) |
| Rank | Rank ≠ ADP. Points move only via volume/share |

## Still live (operate, not architecture)

| Piece | Status |
|-------|--------|
| KEI | Model frozen + Week 1 desk factors. Edge/Tag = KEI vs market only |
| Injuries / inactives | Current vs full-strength where already built; residual injury-API honesty is **not** board degradation |
| Rest / short week | Week 1 honestly **not applied** (no prior REG gap) |
| Weather | Indoor → not applied; outdoor uses real forecast; never climatology |
| Boards | `/edge-board/nfl`, fair-lines, power, fantasy, game-boxes, survivor show pin + N + date |
| REG Week 1 lines | When books post them. No preseason market theater |

## Before / after — Walker

| | Team | Rush | Rank | Half-PPR |
|--|------|------|------|----------|
| **Before** (T172000Z hotfix identity, thin KC pool) | KC | 904 | RB29 / ov98 | 169.6 |
| **After** (this lock) | KC | **1172** | **RB5 / ov22** | **234.0** |

KC team rush **1,361 → 1,850** from BUF/BAL surplus (donors stay ≥2,200). Not 1,800 invented Walker yards. Mahomes remains pass-heavy. Charbonnet stays SEA (no ghost Walker). Achane-class committee RB1s were **not** bulk-lifted.

## Gate table (2026-08-13)

All PASS: Walker KC · Charbonnet SEA · Evans SF · Egbuka TB · Walker feature volume 1172 · checksum QBs · QB pass shape 8/96 ≥4000 · top-5 RB spread 52.8 · Σ wins 272 · identity string · pack vs FP CLEAR_ERROR=0.

Pointer cannot flip on red: `publish_launch_research_to_web.py` writes the bundle, runs invariants + `preseason_release_gate.py`, **then** flips `data/ops/nfl-web-launch-bundle.json`. Finalize 100k defaults to `--skip-pointer`.

## Explicit non-goals (queued, not this lock)

- NFL automation cron
- Ungate weekly player props
- New EPA / OL premium / doctrine rewrite
- Rank = ADP
- CFB

## After merge

**Stop model invention. Operate.** Automation only after this lock is green.
