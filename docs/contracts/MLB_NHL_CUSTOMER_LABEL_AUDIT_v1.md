# MLB/NHL customer label audit (v1)

**Status:** research audit · no production UI edits this run  
**Base:** `4bd0f87d…`

## Honest naming — observed vs required

| Surface | Current customer string | Required contract label | Verdict |
| --- | --- | --- | --- |
| NHL Edge Board market | “Puck Line” (`nhlDisplayMarketLabel`) | Puck Line | **honest** |
| NHL Edge Board two-way ML helper | “Game Moneyline — Includes OT/Shootout” | Game ML incl. OT/SO | **honest** (helper exists; paint still gated) |
| NHL Edge Board footer | “LEAN (≥2.5) / PLAY (≥4.0)” | puck-line research tags only | **OPEN** — must not be read as Game ML tags (C3) |
| NHL fair-lines page shell | “moneylines and totals (puck line staged next)” | Puck Line already labeled on Edge Board | **contradiction** (C11) |
| NHL goalie desk | “ML / totals / puck line” | Game ML must say OT/SO | **OPEN** (C12) |
| NHL grade schema | `spread` | Puck Line | internal key; customer must not see “Spread” |
| MLB fair-lines | “Fair Lines” / “Run Line Board” | Game ML + Game Total initially; Run Line desk | **OPEN** — RL presented as board (C4) |
| MLB nav / IA | “Run Line” primary desk item | desk/research until board contract | **OPEN** (C4) |
| MLB edges tabs | `ml` / `total` / `run_line` | Game ML / Game Total / Run Line (desk) | labels OK; board posture not |
| MLB First Five | mostly absent from customer chrome | First Five Moneyline / First Five Total | **honest omission** on board; model still emits |
| Shared customer-truth | “Home” / “Away” | `home` / `away` enum | mapping required (C8) |

## Rules this audit does not change

- Do not retune `NHL_LEAN_EDGE_PTS` / `NHL_PLAY_EDGE_PTS`.
- Do not paint NHL Game ML LEAN/PLAY.
- Do not promote MLB Run Line to the initial public board in this run.
