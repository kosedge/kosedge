# NFL Season Engine — Depth Chart Volatility & Committee Handling (v1.5)

**Date:** 2026-08-03  
**Branch:** `feat/nfl-season-engine-depth-volatility` → `deploy-vercel`  
**Engine version before:** `nfl-season-engine-v1.4.1-hardened`  
**Engine version after:** `nfl-season-engine-v1.5-depth-volatility`  
**Package:** `services/model-service/src/services/nfl_season_engine/`  
**Scope:** Layer-3 depth structure + committee splits + weekly role volatility. No UI. No new game-script logic. No survivor EV overhaul.

## Goal

Make role assignment and work distribution more realistic when:

- True feature back vs committee
- WR1/WR2/WR3 hierarchy clear vs murky
- Injuries or performance create mid-season role changes
- Multiple players share a position without a dominant starter

## What changed

### 1. Depth-chart structure (`depth_chart.py`)

Per-team classification:

| Axis | Values | Rule (inspectable) |
| --- | --- | --- |
| RB | `feature` / `committee` / `thin` | Committee when top-2 rush shares ≥ 0.26 and \|gap\| ≤ 0.14 |
| WR | `clear` / `murky` / `thin` | Murky when WR1−WR2 ≤ 0.05 or WR1−WR3 ≤ 0.10 |

Surfaced in `include_diagnostics` as `depth_structure` (+ `depth_structure_detail` on game-boxes).

### 2. Committee / feature base splits (documented tables)

**Committee rush (absolute team volume among named backs):**

| Backs | Label | Absolute shares |
| --- | --- | --- |
| 2 | 55/45 | 0.42 / 0.34 |
| 3 | 45/35/20 | 0.36 / 0.28 / 0.16 |

**Feature rush:**

| Backs | Label | Absolute shares |
| --- | --- | --- |
| 2 | 68/32 | 0.55 / 0.26 |
| 3 | 60/25/15 | 0.50 / 0.22 / 0.12 |

**WR targets:**

| Hierarchy | WR1 / WR2 / WR3 |
| --- | --- |
| Clear | 0.23 / 0.16 / 0.09 |
| Murky | 0.18 / 0.15 / 0.12 |

Committee / murky books get table splits applied at load time. Feature / clear books keep loaded priors (CMC, Barkley, AJ Brown, etc.) unless `force_table_splits=True`.

### 3. Volatility (deterministic given seed)

Per season-path week (teams that play that week):

1. Small Gaussian share drift (larger SD for committee / murky)
2. Rare adjacent role shuffle (`p=0.08`) among committee RBs or murky WRs
3. Injury of a starter → label promotion (`RB2`→temporary `RB1`; WR ladder compress; committee reorder)

Diagnostics: `role_transitions` / `role_transitions_sample`.

### 4. Injury interaction

- **Feature RB1 out:** RB2 inherits feature-like lion’s share (~68% of assignable rush) and is relabeled `RB1`
- **Committee member out:** remaining backs get uneven weights (58/42 or 45/35/20) — not equal splits
- Injured player rush/target shares still zero at availability 0; residual other bucket unchanged
- Thin charts (single RB) do not crash

## Before / after examples (demo universe)

### Feature vs committee (carry concentration)

| Team | Structure | Top-1 rush | Herfindahl (RB) | Notes |
| --- | --- | --- | --- | --- |
| PHI (Barkley/Shipley) | feature | ~0.58 | higher | Dominant RB1 |
| DET (Gibbs/Montgomery) | committee | ~0.42 after split | lower | Uneven 55/45-style book |

Synthetic force-table check: feature HHI > committee HHI; feature top-1 > committee top-1.

### WR hierarchy

| Team | Hierarchy | WR1−WR3 target gap |
| --- | --- | --- |
| PHI (Brown / Smith / Dotson) | clear | ~0.14 (table 0.23−0.09) |
| SF (Samuel / Aiyuk / Pearsall) | murky | ~0.06 (table 0.18−0.12) |

Murky compresses alpha without erasing WR1 > WR2 > WR3 rank.

### Volatility

Same seed → identical week-3 DET rush shares and transition log. Different seed or week → different drifted shares. Season-path seed stability preserved on mini schedule.

### Realism (BUF @ KC)

Cook rush yards mean still &lt; 95; Rice receptions mean still &lt; 8 (no return of 100-rush / 9-catch inflation).

## Diagnostics / API (additive)

| Surface | New fields |
| --- | --- |
| `game-boxes` + `include_diagnostics=true` | `depth_structure`, `depth_structure_detail`, `role_transitions` |
| `simulate` + diagnostics | `depth_structure`, `role_transitions_sample`, `path0_depth_structures_end` |
| `GET /nfl/season-engine/status` | `capabilities`: `depth_chart`, `role_volatility`; `depth_chart` docs block |

Stable player-row fields unchanged (`usage_role`, `personnel`, distributions).

## Files

| Path | Change |
| --- | --- |
| `…/depth_chart.py` | **New** — structure, splits, volatility, promotions |
| `…/usage_roles.py` | Committee injury note; depth docs in matrix dump |
| `…/injury_paths.py` | Feature/committee-aware realloc + promotions |
| `…/season_sim.py` | Weekly path volatility + diagnostics |
| `…/game_query.py` | Focus-team depth + volatility + diagnostics |
| `…/loaders.py` | Apply depth splits on demo/DB load |
| `…/calibration.py` | `ENGINE_VERSION = nfl-season-engine-v1.5-depth-volatility` |
| `…/routes/nfl.py` | Status capabilities / depth_chart block |
| `tests/test_nfl_season_engine_depth_volatility.py` | **New** |
| `data/ops/nfl-season-engine-api-contract-20260803.md` | Additive fields noted |
| `data/ops/nfl-full-model-foundation-report.md` | v1.5 note |

## Tests

```bash
cd services/model-service && python3 -m pytest tests/test_nfl_season_engine*.py -q
```

Coverage: feature vs committee concentration; murky vs clear WR gap; seed-stable volatility; committee/feature injury realloc; thin chart; Cook/Rice bounds; diagnostics presence.

## Remaining limitations

1. Structure inferred from prior shares / depth_order — not coaching staff intent or snap-chart NLP
2. Volatility is share drift + rare shuffle — not full mid-season “breakout” career arcs
3. No red-zone-specific committee rules; no coaching-tendency matrix
4. Slot role still depth-rank heuristic (4th WR → `WR_SLOT`)
5. Demo round-robin has every team every week (volatility runs league-wide each week)

## Railway

Deploy model-service `kosedge` after merge so live HTTP serves `v1.5-depth-volatility`. Smoke:

```bash
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/status" | jq '.engine_version, .capabilities, .depth_chart'
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/game-boxes?home_team=KC&away_team=BUF&week=1&demo=true&n_replicates=100&include_diagnostics=true" \
  | jq '{engine_version, depth_structure: .diagnostics.depth_structure, role_transitions: (.diagnostics.role_transitions|length)}'
```
