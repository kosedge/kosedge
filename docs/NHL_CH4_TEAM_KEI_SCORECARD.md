# NHL Chapter 4 — team KEI scorecard

**Stamp:** `nhl-kei-v0.1-ch4` · engine `nhl-season-engine-v0.1`  
**Mode:** `--kei-only` · 1344 RS games  
**Brief:** [`docs/NHL_CH4_TEAM_KEI_BRIEF.md`](./NHL_CH4_TEAM_KEI_BRIEF.md)  
**Shrink / Ch3:** `0.85` · home +0.10 / B2B −0.15 / travel −0.08 / alt ±0.12 · cap 0.35 **frozen**

---

## Opening night — FLA @ CAR (2026-09-29)

| Away @ Home | Date       | KEI puck (home) | KEI total |    WP |
| ----------- | ---------- | --------------: | --------: | ----: |
| FLA @ CAR   | 2026-09-29 |           −0.94 |      6.71 | 69.4% |

Inputs (goal units): CAR net/G ≈ +0.58 · FLA net/G ≈ −0.26 · situation_Δ = +0.10 (home).  
Not a copy of Best — pack has no book Best; tags stay **PASS** until trusted `icehockey_nhl` Best and \|edge\| ≥ 2.5.

---

## Formula

```text
kei_puck_home = -((net_h - net_a) + (sit_h - sit_a))
kei_total     = gf_h' + gf_a'
WP            = Φ(-puck / 1.85)
```

---

## Tags

| Tag  | Rule                                           |
| ---- | ---------------------------------------------- |
| LEAN | \|edge\| ≥ 2.5 vs trusted Best                 |
| PLAY | \|edge\| ≥ 4.0                                 |
| PASS | Best missing / untrusted / preseason (default) |

---

## Gates

| Gate                                       | Result   |
| ------------------------------------------ | -------- |
| `/edge-board/nhl` no longer markets-only   | **PASS** |
| FLA@CAR KEI filled · not a copy of Best    | **PASS** |
| PASS unless trusted Best & \|edge\| ≥ 2.5  | **PASS** |
| Ch3 coeffs / shrink / Ch2 / Ch5 untouched  | **PASS** |
| NBA / WNBA / CFB untouched                 | **PASS** |
| Props dark · starter-unknown goalie rows — | **PASS** |

**Stop.** Chapter 6 dark after screenshot. Not props.
