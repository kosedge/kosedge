# Self-review against recent IMV RETURNs

Defects that returned earlier opening packages, and this filing:

| prior defect | this filing |
| --- | --- |
| hardcoded baseline | no scorer, no baseline, no runner |
| lock written before pins | `holdout-once.lock` not written; pin files say false |
| season gate as a substitute for leakage control | year refuse is not the control; week/availability is |
| roster look-ahead / B-4b(n)-PIT | documented; spec forbids season snapshots as weekly |
| expected answers after runner sha | no runner |
| claimed PASS | both packages say they are not a PASS |
| carry a38a55bb as a target | listed as leakage-invalidated |
| "pre-kickoff only" without roster timestamps | named as a false claim; L-9 requires a real check |

Open items we are **not** claiming closed:

- IMV has not accepted this spec
- weekly source bytes are not deposited
- Phase 2 rebuild / refit has not started
- IMV ruling file `0feec57e` was not hashed in this checkout
