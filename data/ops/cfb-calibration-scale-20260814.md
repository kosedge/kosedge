# CFB Calibration / Blowout-Scale Pass (research only)

**Date:** 2026-08-14  
**Branch:** `feat/cfb-p3b-calibration-scale` → `deploy-vercel` (stacked on #233–#236)  
**Engine:** `cfb-season-engine-v0.13-calibration-scale`  
**Calibration id:** `cfb-margin-scale-v0.13-20260814`  
**Doctrine:** Research fair only. `used_in_spread` stays **false**. No KEI. No lock. If ATS stays coin-flip, say so.

---

## A. Diagnose scale

### 2026 Week 0–2 FBS vs FBS (official slate, 96 games)

| | Before (v0.12) | After (v0.13) | Hist close 2022–25 W0–2 FBS–FBS |
| --- | ---: | ---: | ---: |
| n | 96 | 96 | 550 |
| mean \|spread\| | 13.30 | **10.50** | 12.07 |
| p50 | 12.0 | **10.2** | 8.5 |
| p90 | 25.6 | **19.6** | 28.5 |
| max | 38.3 | **24.5** | 50.0 |
| \|spread\| > 20 | 19.8% | **8.3%** | 20.2% |
| \|spread\| > 28 | 7.3% | **0.0%** | 10.5% |
| \|spread\| > 35 | 3.1% | **0.0%** | 5.6% |

Hist W0 is empty in the lake (those openers are tagged Week 1). Hist W1 p50 = 7.5; W2 p50 = 10.5. Markets **do** post −35 cupcakes (5.6% of W0–2 FBS–FBS). The 2026 problem was not “zero −28s exist in nature” — it was **ranking-prior theater**: OSU −38 / USC −29 from identity stack, mid-pack p50 12 vs hist 8.5.

Hist including FCS: mean 18.3, >28 = 27.5%. FCS stays labeled; we do not crush those gaps into fake 14-pt lines.

### Root cause

`MATCHUP_RESPONSE = 1.40` was raised in v0.8.1 because **historical reconstruction** (league-avg roster, no live identity) was *too cold* vs close. Live 2026 stacks ESPN roster + SP+ carry on top of that decompress. Linear `off/def` ratio^1.40 then invents −35–39 on G5 cupcakes.

Not HFA (baseline 1.7). Not Gaussian σ (left wide on purpose). Not missing stadium drama.

---

## B. Knobs (two, plus HFA placement)

```
matchup = home_exp − HFA − away_exp
scaled  = matchup * SCALE          # FBS–FBS 0.80; FCS 0.94
cal     = TAU * tanh(scaled / TAU) # TAU = 26
margin  = cal + HFA                # HFA added after compress
total   = unchanged pace path
```

| Knob | Value | Why |
| --- | ---: | --- |
| `MARGIN_FBS_SCALE` | **0.80** | Pull mid-pack p50 12 → ~10 toward hist 8.5 |
| `MARGIN_TANH_TAU` | **26** | Soft-cap OSU-class −39 → ~−24; no routine −35 |
| `MARGIN_FCS_SCALE` | **0.94** | FCS already labeled / wide-σ |
| `LEAGUE_REG_PLACEHOLDER` | **0.28** | Shrink O/D index 28% toward 1.0 when SP+ is `league_average_fill` (ARST/CSU/ECU/JVST/M-OH/MIZZ/NEV/ODU/TOL/UAB/UNM/UNT) |
| HFA | **after** tanh | Do not erase ~1.7 home points on blowouts |

Totals: team totals still sum to `fair_total`. Pace/efficiency total path **not touched**.

σ: open-QB still wider than incumbent vs incumbent. Early-season / Week 0 flag unchanged. Did **not** shrink σ to chase ATS.

---

## C. Walk-forward (hostile, strictly before kickoff)

Program-prior harness (`points = net_epa_adj × 28`, seasons `< Y`, no 2026 roster). **P2 stays base.** This pass does not retune that prior.

| Window | Before | After | Read |
| --- | ---: | ---: | --- |
| W0–1 ATS | 47.7% (n=415) | **47.7%** | flat |
| W0–1 MAE | 8.36 | **8.36** | flat |
| W0–1 median \|err\| | 6.53 | **6.53** | flat |
| W0–1 mean error | +4.13 | **+4.13** | still too *cold* vs close |
| Overall ATS / MAE | 50.3% / 7.48 | 50.3% / 7.48 | unchanged |

ATS CI W0–1 still 43.0–52.5%. Coin-flip. Compressing the **live 2026** identity path does not (and must not) fit 2026 roster into 2020–25.

**Blockers if you want ATS > 50%:** market blend (explicit non-goal this pass), more years of live identity, efficiency snapshot holes (12 teams league-avg fill), true lock closes vs early lake snaps. Do not “fix” ATS by shrinking σ.

---

## D. Week 0 / notable old vs new (N=400, research only)

| Matchup | Week | Old spread | New spread | Total | WP home |
| --- | ---: | ---: | ---: | ---: | ---: |
| UNC @ TCU (Dublin) | 0 | −17.2 | **−13.2** | 53.2 | 70% |
| SJSU @ USC | 0 | −29.4 | **−20.2** | 61.1 | 80% |
| NCSU @ UVA | 0 | −4.5 | −5.1 | 57.0 | 58% |
| HAW @ STAN | 0 | +8.7 | **+4.7** | 50.9 | 42% |
| NMSU @ FSU (open camp) | 0 | −13.3 | **−11.5** | 53.6 | 68% |
| MEM @ UNLV | 0 | −3.8 | −4.6 | 62.1 | 57% |
| BALL @ OSU | 1 | −41.0 | **−24.5** | 58.0 | — |
| UTEP @ OU | 1 | −32.4 | **−21.8** | 57.9 | — |
| MOST @ TAMU | 1 | −31.0 | **−21.4** | 63.4 | — |
| FRES @ USC | 1 | −28.6 | **−19.6** | 57.4 | — |

Power still favored. Not routine −35. Neutral Dublin compressed, not inverted. Open-QB FSU still a favorite with a wide band.

`used_in_spread=false` on every row.

---

## E. P4 research win totals

**Not yet.**

Scale is less theater (OSU-class −41 → −24.5; no W0–2 \|spread\| > 28). That is necessary, not sufficient. W0–1 is still 47.7% ATS. Season-sim evolution / win σ were not the thing we graded. Twelve teams still have league-average SP+ fill. CFP/natty stay stub.

Look at compressed project-game numbers as research. Do not plan a desk around season win totals.

---

## Safety

- Status 200: `calibration_id`, `calibration_as_of=2026-08-14`, version v0.13
- Densified seed still not official
- No Edge KEI
- No CFP/natty product numbers
