# MLB/NHL Market Contract v1 (draft)

**Status:** Research draft — not production UI wire-up  
**Schema version:** `mlb-nhl-market-contract-v1`  
**Base SHA:** `4bd0f87de71d23cca8d61c980530a0902b3e8b36`  
**Hard stops:** no threshold shopping; no PLAY/LEAN unlock; no production UI change in this run.

## Versioned `market_contract_id`

Pattern: `{sport}.{family}.{period}.{settlement}.v{n}`

| market_contract_id | Customer label | Settlement |
| --- | --- | --- |
| `mlb.ml.fg.incl_extra_innings.v1` | Game Moneyline (includes extras) | Full game incl. extras |
| `mlb.ml.f5.regulation_only.v1` | First Five Moneyline | First five only |
| `mlb.run_line.fg.incl_extra_innings.v1` | Run Line | Full game (desk/research) |
| `mlb.total.fg.incl_extra_innings.v1` | Game Total | Full game |
| `mlb.total.f5.regulation_only.v1` | First Five Total | First five only |
| `nhl.ml.fg.incl_ot_so.v1` | Game Moneyline — Includes OT/Shootout | Incl. OT/SO |
| `nhl.ml.regulation.three_way.v1` | Regulation Moneyline (3-way) | Regulation only |
| `nhl.puck_line.fg.incl_ot_so.v1` | Puck Line | Incl. OT/SO |
| `nhl.total.fg.incl_ot_so.v1` | Game Total | Incl. OT goals |

## Enums

- **selected side:** `home | away | over | under | draw`
- **home/away orientation:** `home_signed | away_signed | side_explicit | not_applicable`
- **market family:** `moneyline | run_line | puck_line | total`
- **period scope:** `full_game | first_five | regulation`
- **settlement scope:** `includes_extra_innings | first_five_innings_only | includes_overtime_shootout | regulation_only_three_way`
- **price format:** `american | decimal | implied_prob | fair_line_points`
- **push/void:** catalog `push_void`

## Canonical calculation contract (per market)

| Contract | Calc | Edge direction | Push/void |
| --- | --- | --- | --- |
| MLB Game ML | two-way no-vig American → P(home); `signed = model − market` | Home if signed ≥ 0 | void/cancel if game cancelled |
| MLB First Five ML | same helper, **separate id** | same | push if F5 tied |
| MLB Run Line | home-signed handicap; `signed = fair − market` | Home if signed < 0 | no push at ±1.5 |
| MLB Game Total | `signed = fair − market` | Over if signed > 0 | push on exact |
| MLB First Five Total | same helper, **separate id** | same | push on exact |
| NHL Game ML (OT/SO) | two-way no-vig | Home if signed ≥ 0 | void/cancel |
| NHL Regulation ML | **three-way** only; two-way helper DATA_GAP | draw is priced | no push on draw |
| NHL Puck Line | home-signed handicap | Home if signed < 0 | no push at ±1.5 |
| NHL Game Total | totals helper | Over if signed > 0 | push on exact |

Cross-contract mix (FG↔F5, Game ML↔Regulation) is DATA_GAP.

## Locked product decisions (honored)

### MLB

- Full-game ML includes extra innings per book settlement.
- First Five is a **separate** contract.
- Initial board: Moneyline + Total only.
- Run Line remains desk/research until board support exists.
- Replace overloaded `*Home` with explicit side/orientation + contract id.

### NHL

- Customer spread label = **Puck Line**.
- Full-game Puck Line and Total follow governed book settlement.
- **Game Moneyline** explicitly includes OT/SO.
- **Regulation Moneyline** is separate three-way; never silently treated as Game ML.
- No NHL ML LEAN/PLAY presentation until ML contract + validation complete.

## Code entrypoints (research-only)

- `apps/web/lib/market-contract/types.ts` — schema + catalog
- `apps/web/lib/market-contract/calc.ts` — canonical calc helpers
- Tests: `apps/web/__tests__/lib/market-contract/market-contract.test.ts`

## Non-goals this run

- No LEAN/PLAY threshold derivation
- No production Edge Board / Odds Compare UI edits
- No schema migration of live payloads
