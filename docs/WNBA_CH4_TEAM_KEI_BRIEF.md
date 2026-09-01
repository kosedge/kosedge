# WNBA Chapter 4 — team KEI brief

**Phase:** Publish team lines. Replace the Aug 1 leftover. **Not** props.  
**Stamp frozen:** `wnba-season-engine-v0.1` · shrink `0.85` · Ch2 grid `200` · Ch5 scorer · Ch3 `home +1.5 / B2B −1.5 / travel −0.5 / altitude +0.5` · cap `±3.0`  
**Scorecard:** [`docs/WNBA_CH4_TEAM_KEI_SCORECARD.md`](./WNBA_CH4_TEAM_KEI_SCORECARD.md)

---

## Formula

```text
KEI_spread_home = −((net_h − net_a) · pace/100 + (sit_h − sit_a))
KEI_total       = ppg_h' + ppg_a'          # Ch3 implied_ppg (situation inside)
WP              = Φ(−spread / WNBA_MARGIN_SD)   # SD = 11.0
```

`--kei-only`. Does **not** rematerialize Ch1/Ch2/Ch5.

---

## Tags (vs trusted Best only)

| Tag  | Rule                                      |
| ---- | ----------------------------------------- |
| LEAN | \|edge\| ≥ **2.5**                        |
| PLAY | \|edge\| ≥ **4.0**                        |
| PASS | Best missing, untrusted, or already final |

`basketball_wnba` trust gate. **Best cleared** when untrusted (tags only; display may keep Current).

---

## Allowlist

- `wnba_kei.py` + `wnba_kei_lines_ch4.json` + `scripts/wnba/build_kei_ch4.py`
- `/wnba/kei-lines` + fair-lines `source=season_engine|auto` (drops `401857105` / `401857106`)
- `/edge-board/wnba` + `wnba-trusted-market.ts`
- docs + sample scorecard including **CON@ATL**
- WNBA-only CI

---

## Forbidden (honored)

New s · new grid · new player means · new situation coeffs · props · blending leftover fair-lines into the new KEI · team if · walking KEI to the book · NBA/CFB/NFL packs

---

## Gates

- `/edge-board/wnba` loads · remaining RS KEI from Ch2+Ch3, not Aug 1 leftovers
- CON@ATL KEI filled and is **not** a copy of +14.5
- PASS unless trusted Best and \|edge\| ≥ 2.5
- NBA HOU@OKC ~−4.2 · CFB BALL@OSU **−40.5**

---

## Done

Stop after this. **Chapter 6 dark** (proj vs line, cap 4 PLAY registered only) is **not** this PR.
