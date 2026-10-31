# MANIFEST t4850u v2

- run_id `eval-w8-t4850u-v2-20261031T021529Z-232f5da7`
- agent `bc-09ab3a07-8e33-54d4-bfdf-e71c44d61c0c`
- label `DIAGNOSTIC / EVAL_ONLY`
- #667 DRAFT commit `6ca03716` (`6ca03716fe52930332d5ffba302c312a651980cc`) · parent v1 `426bd1d9` (`426bd1d9e7d3eed4e9bf1166caa2b558862e7551`) · lineage `b6d019b0`
- parent v1 tip `426bd1d9` (`426bd1d9e7d3eed4e9bf1166caa2b558862e7551`)
- lineage / diff base `b6d019b0` (`b6d019b051f13156354504097d1635b64ab7ceae`)
- cmd `PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py --write-packet`
- test 6.1 cmd `PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py --test-6-1-missing-field` (expect exit 2)
- test 6.3 cmd `PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py --test-6-3-pin-mismatch` (expect exit 3)
- public_delivery `False` · scoring_admissible_now false · e1_admissible false

## config

```json
{
  "as_of": "cf514078",
  "bye_rolling_as_of": {
    "BUF": 6,
    "JAX": 6,
    "LAC": 6,
    "WAS": 6
  },
  "c10": false,
  "hl": false,
  "if_blend": 0,
  "odds": false,
  "panel": "340a06dd81e25eece87a4d8475feca918e1ccb3c5d9663edfe5063a85ba3fa9e",
  "railway": false,
  "rating_week": 7,
  "schedule": "d88ae73440d3da87198ddb9d8986e0a19773cd3626215e495138907c44ff43fe",
  "season": 2026,
  "seed_base": 48500,
  "simulations": 4000,
  "source_pin": "52d9e909",
  "sportsbook": false,
  "target_week": 8,
  "through_w7": "c674da77",
  "tnf_excluded": "2026-W08-CAR@GB"
}
```

## diff vs b6d019b0

```
data/ops/nfl-offline-if-caller-t4838u/README.md    |   4 +
 .../eval_w8_t4850u/DIAGNOSTIC_PACKET.json          | 146 ++++
 .../eval_w8_t4850u/DIAGNOSTIC_PACKET.md            |  19 +
 .../eval_w8_t4850u/ELIGIBILITY.json                | 301 +++++++
 .../eval_w8_t4850u/FINDINGS.json                   |  28 +
 .../eval_w8_t4850u/FINDINGS.md                     |  18 +
 .../eval_w8_t4850u/PINS.json                       |  97 +++
 .../eval_w8_t4850u/PUBLICATION_CONTROLS.json       |  21 +
 .../eval_w8_t4850u/RESULTS.json                    | 262 ++++++
 .../eval_w8_t4850u/SHA256SUMS                      |  12 +
 .../eval_w8_t4850u/UNRESOLVED.json                 |   1 +
 .../eval_w8_t4850u/UNRESOLVED.md                   |  15 +
 .../eval_w8_t4850u/inputs/ACCEPT.json              |  35 +
 .../inputs/team_efficiency_current_through_w7.json | 905 +++++++++++++++++++++
 scripts/nfl/run_offline_if_eval_w8_t4850u.py       |  54 ++
 .../src/services/nfl_offline_if_eval_w8.py         | 834 +++++++++++++++++++
 .../tests/test_nfl_offline_if_eval_w8_t4850u.py    | 123 +++
 17 files changed, 2875 insertions(+)
```
