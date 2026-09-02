# NHL Chapter 4 — team KEI brief

**Phase:** First fill of the blank column. **Not** props.  
**Stamp frozen:** `v0.1` · shrink `0.85` · Ch2 TOI + tandem · Ch5 scorer · Ch3 home **+0.10** / B2B **−0.15** / travel **−0.08** / alt **±0.12** · cap **0.35**  
**Scorecard:** [`docs/NHL_CH4_TEAM_KEI_SCORECARD.md`](./NHL_CH4_TEAM_KEI_SCORECARD.md)

---

## Formula

```text
KEI_puck_home = −((net_h − net_a) + (sit_h − sit_a))
KEI_total     = gf_h' + gf_a'                 # Ch3 gf_pg'
WP            = Φ(−puck / NHL_MARGIN_SD)      # SD = 1.85
```

`--kei-only`. Does not rematerialize Ch1/Ch2/Ch5 or retune Ch3 coeffs.

---

## Tags (vs trusted Best only)

| Tag  | Rule                                  |
| ---- | ------------------------------------- |
| LEAN | \|edge\| ≥ **2.5**                    |
| PLAY | \|edge\| ≥ **4.0**                    |
| PASS | Best missing, untrusted, or preseason |

`icehockey_nhl` trust gate. **Best cleared** when untrusted.  
Starter-unknown goalie rows stay **—** (no goalie PLAY).

---

## Allowlist

- `nhl_kei.py` + `nhl_kei_lines_ch4.json` + builder
- `/nhl/kei-lines` + fair-lines `source=season_engine|auto`
- `/edge-board/nhl` + `nhl-trusted-market.ts`
- docs + NHL-only CI

---

## Forbidden

New s · new TOI · new means · new situation coeffs · props · walking KEI to the book · team if · NBA/WNBA/CFB/NFL

---

## Gates

- `/edge-board/nhl` banner no longer “KEI blank” for RS games
- FLA@CAR KEI filled and is **not** a copy of Best
- PASS unless trusted Best and \|edge\| ≥ 2.5
- NBA/WNBA/CFB untouched

---

## Done

Stop after this. **Chapter 6 dark** after that screenshot. Not props.
