# NBA Chapter 6 — props dark brief

**Phase:** Desk on Ch5 `PlayerProjection`. **Dark only** — proj vs line, **zero PLAY**.  
**Depends on:** [#371](https://github.com/kosedge/kosedge/pull/371) on `deploy-vercel` (Ch4 screenshot gate)  
**Stamp frozen:** `nba-season-engine-v0.1` · shrink `0.85` · Ch2 grids · Ch5 scorer · Ch3 coeffs · Ch4 KEI  
**Scorecard:** [`docs/NBA_CH6_PROPS_DARK_SCORECARD.md`](./NBA_CH6_PROPS_DARK_SCORECARD.md)

---

## What this PR does

Wire `/nba/props/board` (default `source=season_engine`) to Ch5 means:

```text
mean  = PlayerProjection[PTS|REB|AST|3PM]
σ_game = game-grain formula (Ch5 pack σ is season-rate — too tight for O/U)
tag   = PASS always   # dark — register PROP_PLAY not emitted
```

Hard minutes gate: `MIN < 12` omitted. Cap / PLAY thresholds registered, not fired.

---

## Register (coded, dark-suppressed)

| Name                      | Value              |
| ------------------------- | ------------------ |
| `PROP_PLAY`               | `≥ 4.0` abs **and** `≥ 0.6σ` |
| `PROP_PLAY_CAP_PER_SLATE` | `8`                |
| `PROP_MINUTES_GATE`       | `12.0`             |

---

## Allowlist

- `nba_props.py` (dark desk) + exports
- `/nba/props/board` default → Ch6 dark; stub path still PASS-clamped
- `/pro/nba/props` copy + board client
- docs + NBA-only CI (`test_nba_props_ch6.py`)

---

## Forbidden (honored)

- PLAY / WATCH tags · stake-eligible props · second scorer / stub rates as SoT  
- Rematerialize Ch1/Ch2/Ch5 · retune Ch3 · walk means to the book  
- Fantasy · CFB/NFL · ungate team Edge PLAY on props

---

## Gates

- Board means == Ch5 PlayerProjection (pts/reb/ast/threes)
- `play_n == 0` even when abs edge would clear register
- Minutes gate holds · CFB BALL@OSU still **−40.5**
- Shrink `0.85` untouched

---

## Done

Stop after dark desk. **Do not** ungate PLAY until Chapter 9 grade harness + stake policy.
