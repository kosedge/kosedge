# MLB/NHL market contradiction / gap register (v1)

Severity: **S0** ship-blocker for claims · **S1** contract honesty · **S2** hygiene · **S3** backlog  
Owner: default **desk/model** unless noted. Builder findings ≠ independent approval.

| ID | Severity | Observation | Inference | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| C1 | S1 | Many fields named `*Home` / `fair_fg_home_ml` without `market_contract_id` | Overloaded Home semantics risk silent FG↔F5 mixups | model + web | OPEN |
| C2 | S1 | NHL internal market key remains `Spread` while customer label is Puck Line | Label honesty fixed (#504); schema still legacy | web | OPEN |
| C3 | S0 | NHL LEAN/PLAY cuts exist on puck-line path; Game ML LEAN/PLAY not contract-cleared | Must not present NHL ML LEAN/PLAY until ML contract validated | product | BLOCKED (policy) |
| C4 | S1 | MLB fair-lines UI + nav expose Run Line though lock says desk/research-only until board contract | Product surface ahead of contract | web | OPEN |
| C5 | S1 | Odds-API NHL spreads away-signed; KEI home-signed | Orientation conversion exists; must be stamped on contract calc | web | implemented but unverified end-to-end |
| C6 | S1 | Regulation ML vs Game ML not first-class in payloads | Silent substitution risk if h2h reused | model | OPEN |
| C7 | S2 | MLB edges desk applies numeric min edge filters (0.02 / 0.5) | Not threshold research; still not contract-scoped | web | OPEN |
| C8 | S1 | Customer-truth uses capitalized `Home`/`Away` vs contract enum lowercase | Mapping layer required before paint migration | web | OPEN |
| C9 | S2 | First Five model markets present; board copy often omits settlement wording | Needs labels when exposed | model + web | OPEN |
| C10 | S0 | No authorized LEAN/PLAY threshold selection from this prep | Do not derive thresholds from results | Ryan | Ryan-only |
| C11 | S1 | NHL fair-lines shell copy still says “puck line staged next” while Edge Board already paints Puck Line | Customer-facing inconsistency | web | OPEN |
| C12 | S1 | NHL goalie desk mentions “ML / totals / puck line” without OT/SO qualifier on ML | Could be read as Regulation ML | web | OPEN |
| C13 | S2 | MLB simulator emits both `fair_fg_*` and `fair_f5_*` without contract id | Dual markets exist; mixing is a future fail-closed requirement | model | OPEN |
| C14 | S1 | Shared edge-board matchup helpers use “Spread” wording that NHL must not inherit as customer copy | Cross-sport helper leakage | web | OPEN |

## Proposed implementation sequence (after independent validation)

1. Adopt `market_contract_id` on research calc paths only (this draft).
2. Stamp orientation + settlement on model-service MLB/NHL fair payloads (additive fields).
3. Migrate customer-truth to consume contract ids (no threshold changes).
4. Align MLB board chrome: hide or clearly mark Run Line as research until board contract ships.
5. Align NHL copy: OT/SO on Game ML; keep Regulation ML separate; retire “staged next” if PL is painted.
6. Paint NHL Game ML only with OT/SO label after validation.
7. Only then consider stake-tag policy (Ryan).

Do **not** lock LEAN/PLAY thresholds from this sequence.
