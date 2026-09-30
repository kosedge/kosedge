# MLB/NHL market contradiction / gap register (v1)

Severity: **S0** ship-blocker for claims · **S1** contract honesty · **S2** hygiene · **S3** backlog  
Owner: default **desk/model** unless noted. Builder findings ≠ independent approval.

| ID | Severity | Observation | Inference | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| C1 | S1 | Many fields named `*Home` / `fair_fg_home_ml` without `market_contract_id` | Overloaded Home semantics risk silent FG↔F5 mixups | model + web | OPEN |
| C2 | S1 | NHL internal market key remains `Spread` while customer label is Puck Line | Label honesty fixed (#504); schema still legacy | web | OPEN |
| C3 | S0 | NHL LEAN/PLAY cuts exist on puck-line path; Game ML LEAN/PLAY not contract-cleared | Must not present NHL ML LEAN/PLAY until ML contract validated | product | BLOCKED (policy) |
| C4 | S1 | MLB fair-lines UI exposes Run Line focus though lock says desk/research-only until board contract | Product surface ahead of contract | web | OPEN |
| C5 | S1 | Odds-API NHL spreads away-signed; KEI home-signed | Orientation conversion exists; must be stamped on contract calc | web | implemented but unverified end-to-end |
| C6 | S1 | Regulation ML vs Game ML not first-class in payloads | Silent substitution risk if h2h reused | model | OPEN |
| C7 | S2 | MLB edges desk applies numeric min edge filters | Not threshold research; still not contract-scoped | web | OPEN |
| C8 | S1 | Customer-truth uses capitalized `Home`/`Away` vs contract enum lowercase | Mapping layer required before paint migration | web | OPEN |
| C9 | S2 | First Five model markets present; board copy often omits settlement wording | Needs labels when exposed | model + web | OPEN |
| C10 | S0 | No authorized LEAN/PLAY threshold selection from this prep | Do not derive thresholds from results | Ryan | Ryan-only |

## Proposed implementation sequence (after independent validation)

1. Adopt `market_contract_id` on research calc paths only (this draft).
2. Stamp orientation + settlement on model-service MLB/NHL fair payloads (additive fields).
3. Migrate customer-truth to consume contract ids (no threshold changes).
4. Align MLB board chrome: hide or clearly mark Run Line as research until board contract ships.
5. Paint NHL Game ML only with OT/SO label after validation; keep Regulation ML separate.
6. Only then consider stake-tag policy (Ryan).

## Independent validation checklist (post–Grok reset)

1. Re-read locked MLB/NHL decisions before code.
2. Confirm catalog ids and enums match this draft hash.
3. Re-run `market-contract` vitest suite.
4. Spot-check surface matrix rows against live files on `deploy-vercel`.
5. Verify no production UI diff in this branch beyond research modules/docs/tests.
6. Verify no threshold constants changed (`NHL_LEAN_EDGE_PTS`, MLB desk mins untouched or documented).
7. Mark each contradiction OPEN/BLOCKED — no soft green.
8. Ryan-only: any PLAY/LEAN enablement or board promotion of Run Line / NHL ML.
