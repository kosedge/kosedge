# t5070u — research.q2s.joint.handoff consumer (verification)

**CERT=0 · NFL NO-GO · DRAFT #686 — do not merge.**
OWNER AMEND+CLEAR under **d7e0a6bc** of scope **199140e2**.
Base head **ddb3fdfe**. Not a new joint experiment. Artifacts **5076421e** / **ce6b1244** untouched.

## Paths

| File | Role |
|---|---|
| `joint/consume.py` | read-only consumer |
| `joint/tests/test_consume.py` | focused tests |
| `joint/RECEIPT_t5070u_CONSUME.md` | this receipt |

## Tests

`python3 -m unittest research.q2s_w7w17_t5044u.joint.tests.test_consume -v` → **12/12 OK**.

| Case | Result |
|---|---|
| Real 141 round trip vs canonical pins | PASS |
| COND 34 + J14 NOT_EMITTED preserved | PASS |
| Missing / corrupt / alternate digest / forbidden basename | REFUSE |
| Wrong header / extra / missing / reorder / duplicate / shape / dtype / NaN / negative / row mismatch | REFUSE |
| Draw mutation isolation across handoffs | PASS |
| No 50bda875 / LOOK / freeze traversal; no simulator; no write | PASS |

## Capability (not full-closure)

`consume_q2s_joint(expected_json_sha256=…, expected_npz_sha256=…)` loads the pinned joint JSON+NPZ into an in-memory `research.q2s.joint.handoff` after caller hashes match the frozen canonical pins, header/identity/draw/catalog checks, and `derive_from_pairs` re-drive of WP/ML/spread/total/counts.

**Loaded ≠ all-gates-PASS ≠ calibrated probabilities ≠ book settlement ≠ operational acceptance.** Continuous scores; D=0 ties count away. Does **not** clear #682 broader held consumption or production #6/#8. No LOOK, retune, source edit, spend, merge, deploy, cert, or release.

## Holds

No artifact regen · no outcomes/LOOK/freeze-map reads · no `run_q2s_joint` / writer / simulator invoke · 34 COND + J14 NOT_EMITTED kept visible · CERT=0 · DRAFT.
