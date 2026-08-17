# CFB independent KEI + futures — 2026-08-17 ship

Companions: `cfb-kei-rules-2026.md` · `cfb-season-rules-2026.md`

## Doctrine (locked)

- Model = research fair. Never gut-edited. `used_in_spread=false`.
- KEI = published line = model + versioned menu + measured bias guard. `used_in_spread=true`.
- Market = information only. Never auto-author of KEI.
- Edge / Tag = KEI vs best market only.
- Early weeks 0–2: PLAY 4.0 · LEAN 2.5 · PASS default.

## Success table (smoke on www after merge)

| # | Criterion | Local | www URL |
|---|-----------|-------|---------|
| 1 | W0 KEI lines live for FBS slate (6/6) | PASS | `/edge-board/cfb` |
| 2 | Model pure column + KEI published column | PASS | `/pro/cfb/project-game?home=TCU&away=UNC&week=0&neutral=1` |
| 3 | Edge tags vs market; early thresholds; PASS OK | PASS | `/edge-board/cfb` · `/edge-board/cfb?week=1` |
| 4 | Bias guard versioned; diagnostic vs raw model | PASS | `cfb-kei-rules-2026.md` |
| 5 | Proof logging CFB | PASS | proof_layer adapter (`kei_spread_home`) |
| 6 | Projections N desk-grade | PASS | `/pro/cfb/projections` (N=10,000) |
| 7 | Natty + CFP + conf title probs live | PASS | `/pro/cfb/futures` |
| 8 | Overview → tools coherent; no dead “no KEI” | PASS | `/pro/cfb/overview` |
| 9 | Season + KEI rules on prod path | PASS | `data/ops/cfb-kei-rules-2026.md` · `cfb-season-rules-2026.md` |
| 10 | Smoke table on www all PASS | after deploy | also `/pro/cfb/teams` · `/pro/cfb/slate` · `/pro/kei-lines/cfb` |

## Residual (honest)

- Packaged roster universe is 130/136. Futures cover those 130. 8 W1 FBS rows lack KEI until identity exists: UAB, TOL, ECU, UNT, CSU, ARST, UNM, NEV.
- No live injury API. Banner packaged as_of.
- Futures N=2,500 (win totals remain N=10,000). Preseason mass is wide.
- KEI/futures stamp live engine `cfb-season-engine-v0.9-inseason`; power/win-total packs stay `v0.15-power-sot`.
- Not a profitability claim.
