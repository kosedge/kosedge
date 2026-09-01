# WNBA Chapter 4 — team KEI scorecard

**Stamp:** `wnba-season-engine-v0.1` · `kei_version=wnba-kei-v0.1-ch4` · `as_of=2026-09-01`  
**Frozen:** shrink `0.85` · grid `200` · Ch3 coeffs unchanged · Ch5 135 / Σ MIN=200 not rematerialized  
**Brief:** [`docs/WNBA_CH4_TEAM_KEI_BRIEF.md`](./WNBA_CH4_TEAM_KEI_BRIEF.md)

---

## Sample (live remainder + paper)

| Away @ Home | Date       | Slate          | KEI spread (home) | KEI total |    WP |
| ----------- | ---------- | -------------- | ----------------: | --------: | ----: |
| CON @ ATL   | 2026-09-17 | live_remainder |             −8.49 |    176.47 | 78.0% |

Full emitter: **287** games in `wnba_kei_lines_ch4.json` (286×2025 paper schedule + CON@ATL live seed).  
Leftover fair-line ids **`401857105` / `401857106` dropped** from the live KEI column.

Thresholds: **LEAN ≥ 2.5** · **PLAY ≥ 4.0** · PASS if Best missing / untrusted / already final.

CON@ATL KEI **≠** market copy of **+14.5**.

---

## Gates

| Gate                                       | Result   |
| ------------------------------------------ | -------- |
| KEI pack filled (287)                      | **PASS** |
| Leftovers dropped from live KEI            | **PASS** |
| CON@ATL KEI filled · not +14.5 copy        | **PASS** |
| Tag PASS without trusted Best / final      | **PASS** |
| Ch3 coeffs untouched (+1.5/−1.5/−0.5/+0.5) | **PASS** |
| WNBA_TEAM_CARRY_SHRINK = 0.85              | **PASS** |
| Ch5 135 / Σ MIN=200 untouched              | **PASS** |
| NBA HOU@OKC ≈ −4.16                        | **PASS** |
| CFB BALL@OSU −40.51                        | **PASS** |
| Props / Ch6 not in this PR                 | **PASS** |

Wire: `/wnba/fair-lines?source=season_engine` · `/wnba/kei-lines` · `/edge-board/wnba` + `basketball_wnba` trust gate.

---

## Stop

Ch4 publishes team lines only. **Ch6 stays dark** until after the Ch4 screenshot / prod confirm — **not this PR**.
