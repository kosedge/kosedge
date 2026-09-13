# CFB reconstructed-truth release report

**Date:** 2026-09-12  
**Branch / PR:** `cursor/cfb-priors-eleven-9dba` / #547  
**#532:** **FAIL / DO NOT MERGE**  
**Public CFB Edge Board kill switch:** **OFF** — do not turn on.

No coefficient changes. #536 is a comparison artifact, not a fit target.

## Verdict

| Gate | Result | Public-activation bar |
| --- | --- | --- |
| Source-vintage / provenance | **PASS** | met |
| Fail-closed live-2026 substitution | **PASS** | met |
| W0 missing/fill reconciliation | **PASS** (all explained) | met |
| Schedule → priors → efficiency → Power SoT → week0-close → KEI as-of | **PASS with hygiene note** | met |
| Totals identity (`kei_total ≡ model_total`) | **PASS** as honesty | **FAIL** as market calibration |
| Market residuals (W2 FBS–FBS vs 2026-09-11 DK snapshot) | **Measured; KEEP DARK** | **FAIL** |
| Recommend kill switch ON | **NO** | — |
| Merge #532 | **NO** | — |

**Release: PASS as a reconstructed research truth chain. FAIL for public board activation.**

The reconstructed chain is now auditable. It is not a public-reactivation pack. Spreads still disagree with the book at MAE ~6.8 with 10 favorite flips. Totals remain the documented Over-drunk identity (`kei_total := model_total`, mean residual ~+10). Those are model/product facts, not vintage bugs. Do not haircut them here.

## Frozen authoritative input

| Field | Value |
| --- | --- |
| Dataset | `cfb_sp_plus_final_2025_espn_story.json` |
| Identity | ESPN story 46128861, Bill Connelly, final-2025 SP+ for all 136 FBS |
| Published | 2026-01-20 |
| Legal at W0 as-of | 2026-08-31 |
| SHA-256 | `15dd1cf99a4a63c8821613ede8c2f8c1b9124d09676e08ed1079385e0cf6ebc4` |
| Coverage | 136/136 official 2026 full members |
| Provenance | 136/136 row-level vintage / published / URL / table name |
| Live substitution | rejected (`rejected_2026_inseason_cfbupdate`) |

Working efficiency reprints TCU **8.3** / UNC **−6.6** / UNT **13.8** / Indiana **32.4**. Live 2026 values (TCU 3.9 / UNC +5.8 / UNT −13.2) are not present.

## 1. Market residual / totals identity

Measure only. Same ESPN/DK scoreboard snapshot as the #536 audit (`data/ops/cfb-w2-espn-scoreboard-odds-20260911.json`, n=85). W2 FBS–FBS joined n=47/47. No Odds lake write. No PLAY unsat.

| Metric | #536 | NEW (ESPN year-lock) |
| --- | ---: | ---: |
| spread MAE | 6.857 | **6.755** |
| total MAE | 10.236 | **10.265** |
| median spread residual | +2.90 | +2.76 |
| median total residual | +9.14 | +9.25 |
| mean total residual | +9.942 | +9.976 |
| favorite flips vs market | 11 | **10** |
| \|gap\| ≥7 / 10 / 14 / 20 | 20 / 12 / 8 / 0 | 19 / 12 / 8 / **0** |
| null power | 0 | 0 |

Focus:

| Game | NEW model / KEI | #536 | Market (DK 2026-09-11) | Note |
| --- | ---: | ---: | ---: | --- |
| MIZZ@KU | +1.24 / +1.97 | +1.10 / +1.85 | KU +4.5 | data-bug gone; residual ~−2.5 |
| RUT@BC | +12.46 / +13.46 | +12.49 / +13.49 | BC −3 | **+16.46 unchanged** — genuine |

Flip dropped vs #536: **UTSA@TXST** (the one NEW-vs-#536 sign flip, from Texas State SP+ copy 0.7→2.3). Remaining flips include RUT@BC, UNLV@UNT, USF@ARMY, OSU@TEX — model-vs-market, not hydrate.

Totals identity on the NEW KEI pack: **0 mismatches** on ≥90 FBS games. `cfb_kei.py` still sets `kei_total = model_total`. That is the honest live path while the totals-guard flag is OFF. It is also why totals residuals stay ~+10 Over-drunk. **Do not treat identity-as-honesty as identity-as-calibrated.** Public activation requires a totals guard that has unused-year GREEN, which this pass did not (and must not) invent.

## 2. NEW vs #536 full board

n=96 common scored FBS lines. #536 is **not** the truth target. This distribution only shows the reconstruction sits in the 2025-final neighborhood rather than the 2026-in-season neighborhood.

| | NEW vs #536 | NEW vs #547 (live 2026) |
| --- | ---: | ---: |
| mean Δ | −0.02 | +1.05 |
| mean \|Δ\| | **0.179** | **4.783** |
| median \|Δ\| | 0.07 | 4.35 |
| P90 \|Δ\| | 0.58 | 9.34 |
| P95 \|Δ\| | 0.79 | 9.87 |
| P99 \|Δ\| | 1.23 | 16.05 |
| max \|Δ\| | **1.26** | **16.42** |
| sign flips | **1** | **16** |
| \|spread\| bucket crosses 1/3/7/10/14 | 3 / 2 / 0 / 2 / 0 | (not the comparison that matters) |

Largest NEW-vs-#536 (all attributed; none fitted):

| Game | #536 → NEW | Δ | Attribution |
| --- | ---: | ---: | --- |
| BC@CIN | −17.11 → −15.85 | +1.26 | CIN SP+ 6.7 → 4.5 (frozen-copy vs ESPN) |
| M-OH@PITT | −16.39 → −17.62 | −1.23 | M-OH was `league_average_fill` / 50; ESPN −3.4 rank 82 |
| BOISE@ORE | −20.76 → −19.58 | +1.18 | ORE SP+ 29.3 → 25.9 |
| UTSA@TXST | +0.34 → −0.76 | −1.10 | TXST SP+ 0.7 → 2.3; only sign flip |
| NAVY@FAU | −4.96 → −3.89 | +1.07 | NAVY SP+ 4.8 → 6.2 |

P0 power vs #536 stays within ~0.002 except M-OH (−0.041 fill resolved). No coefficient moved these lines.

## 3. NEW vs W0 missing/fill reconciliation

Every W0-common game involving a W0-missing official code or M-OH fill is listed. None unexplained.

| Game | W0 | NEW | Δ | Cause |
| --- | ---: | ---: | ---: | --- |
| UNT@IU | −31.92 | −13.73 | +18.19 | UNT missing → 1.0 hydrate; ESPN SP+ 13.8 |
| TOL@MSU | −15.16 | −5.56 | +9.60 | TOL missing |
| CMU@UNM | −5.44 | −13.12 | −7.68 | UNM missing |
| ECU@ALA | −25.02 | −18.18 | +6.84 | ECU missing |
| UAB@ILL | −24.41 | −22.11 | +2.30 | UAB missing |
| WYO@CSU | +2.04 | −0.03 | −2.07 | CSU missing |
| ARST@MEM | −10.84 | −12.13 | −1.29 | ARST missing |
| M-OH@PITT | −18.09 | −17.62 | +0.47 | M-OH 50-fill in W0; ESPN mapped |
| WKU@NEV | +8.03 | +7.85 | −0.18 | NEV missing; W0 hydrate happened to land near ESPN |

W2-only (not in the W0 97): MIZZ@KU is the #536 data-bug repair (null MIZZ → real SEC), not a leftover mystery. JVST/ODU have no W0 common FBS line in that 97.

Other \|Δ\|≥1 W0 games (CIN/ORE/MIA/TXST/MSST copy deltas, plus week-0 preview lines such as UNC@TCU −19.19→−14.93) are ESPN-vs-frozen-copy plus the #536 structural rematerialize. NEW vs #536 on UNC@TCU is −15.14→−14.93. Do not chase those toward #536.

## 4. Fail-closed vintage guardrail

Intentional live-2026 substitution:

```
python3 scripts/cfb/package_efficiency_2025_carry.py --allow-live-public
→ exit 1
ERROR: Live public SP+ records look like 2026 in-season (138 teams at 0–2 games).
       Not a final-2025 source.
```

```
python3 scripts/cfb/package_efficiency_2025_carry.py --splice-p0-only
→ exit 1
ERROR: mixes ESPN rows onto a frozen cfbupdate snapshot (the #536 vintage).
```

Synthetic 20+ `1-0` records raise `LivePublicIsNotFinal2025`. 11-2 final-shaped records do not. Tests in `test_cfb_espn_vintage_release_gates.py`.

## 5. As-of / provenance chain

| Layer | as_of / identity | Semantics |
| --- | --- | --- |
| Official schedule / slate | 2026-08-31 | week0-close official ESPN slate |
| Efficiency model as-of | 2026-08-31 | carry used at W0 |
| Efficiency source published | 2026-01-20 | ESPN final-2025 |
| Power SoT | 2026-08-31 / `cfb-power-sot-v0.15-week0-close-20260831` | close remint, not 20260814 research |
| Projections | 2026-08-31 / `…-week0-close-20260831` | same |
| Futures | 2026-08-31 | not reminted |
| KEI | 2026-09-10 / `cfb-kei-v1.0-2026w2` | documented later mint |
| Priors / roster snapshot | **2026-09-12** | 2026 identity overlay from the universe rematerialize — **not** live 2026 SP+ |

Compatible: week0-close research desk + later KEI mint + year-locked 2025 efficiency. Hygiene: priors/roster stamps drifted to 2026-09-12 when #547 rebuilt identity. That is roster identity, not an efficiency vintage leak. W0 canary hashes still match `data/ops/cfb-w0-canary-20260831/MANIFEST.json` (USF E[wins] 8.382).

NDSU / Sacramento State remain snapshot-only transitions. No 2025 FBS SP+, no −25, no 50-fill.

## 6. What we refused

- Fitting NEW to #536
- Live cfbupdate as a 2025 carry
- Splicing ESPN onto frozen norms
- Coefficient / `MATCHUP_RESPONSE` / totals-guard haircut
- Merging #532
- Turning the public board on

## Artifacts

- `data/ops/cfb-espn-vintage-residual-w2-20260912.json`
- `data/ops/cfb-espn-vintage-release-audit-20260912.json`
- `scripts/cfb/cfb_espn_vintage_release_audit.py`
- `services/model-service/tests/test_cfb_espn_vintage_release_gates.py`

Tests: `test_cfb_espn_vintage_release_gates.py` + vintage / enterprise / name-to-code / official-universe — **47 passed**.
