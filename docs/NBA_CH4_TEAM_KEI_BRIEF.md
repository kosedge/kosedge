# NBA Chapter 4 — team KEI brief

**Phase:** Publish team lines. **Not** props.  
**Stamp frozen:** `v0.1` · shrink `0.85` · Ch2 grids · Ch5 scorer · Ch3 apply-on-read  
**Ch3 coeffs:** do **not** retune (`home +2.0 / B2B −1.5 / travel −0.5 / altitude ±1.0`)  
**Scorecard:** [`docs/NBA_CH4_TEAM_KEI_SCORECARD.md`](./NBA_CH4_TEAM_KEI_SCORECARD.md)

---

## Formula

```text
KEI_spread_home = −((net_h − net_a) · pace/100 + (sit_h − sit_a))
KEI_total       = ppg_h' + ppg_a'          # Ch3 implied_ppg
WP              = Φ(−spread / NBA_MARGIN_SD)   # SD = 12.0
```

`--kei-only`. Does not rematerialize Ch1/Ch2/Ch5 packs.

---

## Tags (vs trusted Best only)

| Tag  | Rule                                  |
| ---- | ------------------------------------- |
| LEAN | \|edge\| ≥ **2.5**                    |
| PLAY | \|edge\| ≥ **4.0**                    |
| PASS | Best missing, untrusted, or preseason |

`basketball_nba` trust gate. **Best cleared** when untrusted.

---

## Allowlist

- `nba_kei.py` + `nba_kei_lines_ch4.json` + builder
- `/nba/kei-lines` + fair-lines `source=season_engine|auto`
- `/edge-board/nba` + `nba-trusted-market.ts`
- docs + NBA-only CI

---

## Forbidden (honored)

New s · new grid · new player means · new situation coeffs · props/Ch6 · fantasy · team if · walking KEI to the book · futures · CFB/NFL

---

## Gates

- `/edge-board/nba` loads · KEI filled · not a copy of Best
- PASS unless trusted Best and \|edge\| ≥ 2.5
- Props stub unchanged · CFB BALL@OSU **−40.5**

---

## Done

Stop after this. **Ch6 is dark-only** (proj vs line, no PLAY) and only after Ch4 is on prod.
