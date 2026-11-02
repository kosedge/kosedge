# t5178u W-FIX-A — demonstrated scope (IMPLEMENTED, not VERIFIED/ACCEPTED)

- branch: `cursor/t5178u-wfix-a-fixture-assembly-c003`
- base: `deploy-vercel` @ `f5e3bb58ccbe5a8892fed2a01f347c2308394a2f`
- M0 tip (Cos ACCEPT): `d76c550d` / #707 · seal `4de08ebf`
- CERT=0 · DRAFT only · no merge/deploy
- IMPLEMENTED ≠ VERIFIED ≠ ACCEPTED

## What ran (actual)

```
cd services/model-service
PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_fixture_assembly_wfix_a.py \
  tests/test_nfl_hhl1_capture_plumbing.py -q
```

Result: **85 passed in 0.18s** (W-FIX-A + reused `#664` synthetic plumbing). No network, no DB, no jobs, no simulator.

## Positive path demonstrated

Envelope (POINT_MARGIN, fixture channel) → `reject_market_fields` + `validate_l1_candidate` → synthetic exact quote (`SYNTH-BOOK-T5178U` / event / HOME / `full_game` / line `-3.0` / price `-110` / time) → `ALLOW_FIXTURE`.

Pinned: `data/ops/t5178u-wfix-a/positive-input.json` + `positive-output.json`.

Synthetic raw/adjusted (`0.12` / `-0.08` / `0.97` / `1.03`) survive `#664` validation as **transport only** (`TRANSPORT_ONLY_NOT_INJURY_POLICY`).

`ALLOW_FIXTURE` payload: `fixture=true`, subscriber/betting/production consumable bits all false. `NFL_EDGE_BOARD_INTERNAL=1` + `NFL_FIXTURE_ALLOW_PRODUCTION=true` do **not** upgrade the result. `consume_eligibility(..., consumer=subscriber|betting|production|fair_lines_api|honesty_board|props_eligibility)` hard-refuses.

## Fault matrix demonstrated (typed hard refuse, no partial object)

identity · hash · version · game · period · line · sign · time · cutoff · capability · qualification · missing · stale · partial · cache · totals · moneyline · cover_prob · economic · production_mode · env_bypass · market_fields

Point-margin input → `REFUSE_TOTALS` / `REFUSE_MONEYLINE` / `REFUSE_COVER_PROBABILITY` / `REFUSE_ECONOMIC_ELIGIBILITY`. JOINT_SCORE bit declared only → `REFUSE_QUALIFICATION` (does not unlock totals).

## Not demonstrated / not claimed

Production mode · Odds/paid/live capture · Stage C · E1 · R5 reopen/scoring · scientific EXEC · all-eight PASS · merge/deploy · Worker B consumer projections.
