# MLB/NHL surface → market contract matrix (v1)

**Base:** `4bd0f87d…` · Research audit only · No production UI edits

| Surface | Sport | Current key / field | Mapped contract id | Orientation today | Honesty gap |
| --- | --- | --- | --- | --- | --- |
| Odds API MLB board | MLB | `h2h`, `totals` | `mlb.ml.fg…`, `mlb.total.fg…` | side prices home/away | Run line not requested (OK for initial board) |
| `apps/web/lib/mlb-fair-lines.ts` | MLB | `fair_fg_*`, `handicap_fair_fg_*`, `model_fair_fg_*`, `fg_home_cover_prob_run_line` | FG ML / FG total / run line | overloaded `*Home` | Needs explicit contract id + side; F5 fields not normalized |
| `apps/web/app/api/mlb/fair-lines/route.ts` | MLB | proxy of fair-lines | FG ML / FG total / RL | home-centric | No `market_contract_id` |
| `apps/web/app/(pro)/pro/mlb/fair-lines/page.tsx` | MLB | `focus=run-line` | run line desk | home cover | Customer board shows RL despite “desk-only” lock — **gap** |
| `apps/web/lib/mlb-edges.ts` + `mlb-desk-helpers.ts` | MLB | `ml` / `total` / `run_line`; `minProbEdge` 0.02 / `minLineEdge` 0.5 | FG ML / FG total / RL | mixed | Desk filters exist; **not** threshold research this run |
| `apps/web/app/(pro)/pro/mlb/edges/page.tsx` | MLB | market tabs include `run_line` | RL desk | mixed | Threshold UI present |
| `apps/web/lib/mlb-kei-from-fair-lines.ts` | MLB | KEI from fair payload | FG ML / total | home | Settlement not stamped |
| `apps/web/lib/sport-pro-nav.ts` / `pro-sport-ia.ts` / `pro-sport-desk.ts` / `sport-overview.ts` | MLB | “Run Line” nav | RL desk | — | Product copy implies board support |
| MLB Odds Compare (if present) | MLB | moneyline + totals books | FG ML / FG total | book home/away | No F5; no contract id |
| `services/model-service/.../mlb_pitch_simulator.py` | MLB | `fair_fg_*`, `fair_f5_*`, run-line cover | all five MLB contracts | home-centric | Naming still `*Home`; F5 and FG coexist without contract id |
| `services/model-service/src/tasks.py` MLB persist | MLB | handicap vs model `fair_fg_*` aliases | FG + F5 | home | Dual handicap/model columns |
| `services/model-service/.../mlb_board_health.py` | MLB | presence of FG spread/total | FG | — | No settlement stamp |
| `apps/web/lib/nhl-fair-lines.ts` | NHL | `fair_home_ml`, `fair_spread_home`, `fair_total` | Game ML / Puck Line / Total | home-signed spread | ML settlement (OT/SO) not stamped |
| `apps/web/app/api/nhl/fair-lines/route.ts` | NHL | proxy | Game ML / PL / Total | home | Honest empty when offseason |
| `apps/web/lib/nhl-edge-board-display.ts` | NHL | internal `Spread` → “Puck Line”; ML label ready | `nhl.puck_line…` / `nhl.ml.fg…` | away book → home via `nhlAwayBookToHome` | Good labels; no `market_contract_id` |
| `apps/web/lib/nhl-trusted-market.ts` | NHL | LEAN 2.5 / PLAY 4.0 (puck) | puck line tags | home-signed KEI | Thresholds exist; **do not retune**; ML tags not contract-cleared |
| `apps/web/lib/nhl-kei-from-fair-lines.ts` | NHL | KEI from fair | puck / total | home | Regulation ML absent |
| `apps/web/lib/edge-board-customer-truth.ts` | both | handicap/total/ML formulas; `Home`/`Away` | shared calc family | capitalized sides | Align to enum `home`/`away` before paint migration |
| `apps/web/lib/edge-board-matchup-*.ts` | NHL (shared) | `keiSpreadHome` / `marketSpreadHome` | puck line if NHL | home-signed | NFL-oriented helpers; NHL must not inherit spread wording |
| `apps/web/app/(pro)/pro/[sport]/fair-lines/page.tsx` | NHL | “puck line staged next” | PL | — | Copy still stages puck line while Edge Board already labels it |
| `apps/web/app/(pro)/pro/[sport]/goalies/page.tsx` | NHL | ML / totals / puck line framing | Game ML / Total / PL | — | ML mentioned without OT/SO qualifier |
| `services/model-service/.../nhl_kei.py` | NHL | `kei_puck_home`, totals; LEAN/PLAY twins | puck + total | home-signed | Regulation ML absent |
| `docs/NHL_GRADE_SCHEMA.md` | NHL | `spread` = puck line | PL | — | Internal key still `spread` |
| Customer-truth tests / NHL display tests | both | formula + label locks | shared | — | Good regression surface; no contract id |

## Board posture (locked)

| Sport | Initial customer board | Desk/research |
| --- | --- | --- |
| MLB | Game ML + Game Total | First Five *, Run Line |
| NHL | Puck Line + Game Total | Game ML (until validated), Regulation ML |

\* First Five may exist in model payloads; not initial public board.
