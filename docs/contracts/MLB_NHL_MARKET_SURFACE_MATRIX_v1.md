# MLB/NHL surface → market contract matrix (v1)

**Base:** `4bd0f87d…` · Research audit only · No production UI edits

| Surface | Sport | Current key / field | Mapped contract id | Orientation today | Honesty gap |
| --- | --- | --- | --- | --- | --- |
| Odds API MLB board (`odds-api.ts`) | MLB | `h2h`, `totals` | `mlb.ml.fg…`, `mlb.total.fg…` | side prices home/away | Run line not requested (OK for initial board) |
| MLB fair-lines API normalize | MLB | `fair_fg_home_ml`, `fair_f5_home_ml`, `fair_fg_total`, run-line cover | FG ML / F5 ML / FG total / run line | overloaded `*Home` | Needs explicit contract id + side |
| MLB fair-lines page | MLB | focus `run-line` | run line desk | home cover prob | Customer board shows RL despite “desk-only” lock — **gap** |
| MLB edges desk | MLB | `ml` / `total` / `run_line` | FG ML / FG total / RL | mixed | Threshold filters present; not contract-scoped |
| MLB Odds Compare | MLB | moneyline + totals books | FG ML / FG total | book home/away | No F5; no contract id |
| NHL fair-lines | NHL | `fair_home_ml`, `fair_spread_home`, `fair_total` | Game ML / Puck Line / Total | home-signed spread | ML settlement (OT/SO) not stamped on payload |
| NHL Edge Board display | NHL | internal `Spread` → label Puck Line | `nhl.puck_line…` | away book → home via `nhlAwayBookToHome` | Good label; no `market_contract_id` |
| NHL trusted market / tags | NHL | LEAN 2.5 / PLAY 4.0 | puck line tags | home-signed KEI | Thresholds exist; **do not retune**; ML tags not contract-cleared |
| NHL Edge Board ML chrome | NHL | helper label ready, not painted | `nhl.ml.fg…` | — | Correctly unpainted until contract validation |
| model-service MLB simulator | MLB | `fair_fg_*`, `fair_f5_*`, run line cover | all five MLB contracts | home-centric fields | Naming still `*Home` |
| model-service NHL KEI | NHL | `kei_puck_home`, totals | puck line + total | home-signed | Regulation ML absent |
| Customer-truth helpers | both | handicap/total/ML formulas | shared calc family | Home/Away strings | Align to enum `home`/`away` lowercase contract sides |
| Pro nav / desk copy | MLB | “Run Line” links | RL desk | — | Product copy implies board support |

## Board posture (locked)

| Sport | Initial customer board | Desk/research |
| --- | --- | --- |
| MLB | Game ML + Game Total | First Five *, Run Line |
| NHL | Puck Line + Game Total | Game ML (until validated), Regulation ML |

\* First Five may exist in model payloads; not initial public board.
