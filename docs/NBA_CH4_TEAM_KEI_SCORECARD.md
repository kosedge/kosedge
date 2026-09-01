# NBA Chapter 4 — team KEI scorecard

**Stamp:** `nba-season-engine-v0.1` · `kei_version=nba-kei-v0.1-ch4` · `as_of=2026-09-01`  
**Frozen:** shrink `0.85` · Ch3 coeffs unchanged · Ch2/Ch5 packs not rematerialized  
**Brief:** [`docs/NBA_CH4_TEAM_KEI_BRIEF.md`](./NBA_CH4_TEAM_KEI_BRIEF.md)

---

## Sample (opening week 2025–26 pack)

| Away @ Home | Date       | KEI spread (home) | KEI total |    WP |
| ----------- | ---------- | ----------------: | --------: | ----: |
| HOU @ OKC   | 2025-10-21 |             −4.16 |     234.5 | 63.5% |
| GSW @ LAL   | 2025-10-21 |             −3.92 |     231.3 | 62.8% |
| CLE @ NYK   | 2025-10-22 |             −3.17 |     234.2 | 60.4% |
| SAS @ DAL   | 2025-10-22 |             +4.34 |     237.0 | 35.9% |
| BKN @ CHA   | 2025-10-22 |             −9.15 |     228.0 | 77.7% |
| MIA @ ORL   | 2025-10-22 |             −0.60 |     238.0 | 52.0% |
| TOR @ ATL   | 2025-10-22 |             −1.81 |     235.7 | 56.0% |
| PHI @ BOS   | 2025-10-22 |             −7.32 |     230.2 | 72.9% |

Full emitter: **1200** RS games in `nba_kei_lines_ch4.json`.

Thresholds: **LEAN ≥ 2.5** · **PLAY ≥ 4.0** · PASS if Best missing / untrusted / preseason.

---

## Gates

| Gate                                 | Result   |
| ------------------------------------ | -------- |
| KEI pack filled (1200)               | **PASS** |
| KEI ≠ trivial zero / not a Best copy | **PASS** |
| Tag PASS without trusted Best        | **PASS** |
| Ch3 coeffs untouched                 | **PASS** |
| TEAM_CARRY_SHRINK = 0.85             | **PASS** |
| CFB BALL@OSU −40.5                   | **PASS** |
| Props stub unchanged (research_only) | **PASS** |

Wire: `/nba/fair-lines?source=season_engine` · `/nba/kei-lines` · `/edge-board/nba` trust gate.

---

## Stop

Ch4 publishes team lines only. **Ch6 stays dark** until Ch4 is on prod.
