# Kos Edge — Model Validation Lab

**Intent:** Pre-register evaluation protocols **before** any result viewing.
Lab OS is **NFL-spread-first**. Evidence reports only — no live PLAY / LEAN /
PASS flips from Lab output (CoS → Ryan decides).

## Protocols

| Version | Doc                                                                              | Status      |
| ------- | -------------------------------------------------------------------------------- | ----------- |
| v1.0    | [`NFL_SPREAD_VALIDATION_PROTOCOL_v1.md`](./NFL_SPREAD_VALIDATION_PROTOCOL_v1.md) | `cos_signed` |

## Scorecards

| Version | Doc                                                                  | Machine JSON                                              |
| ------- | -------------------------------------------------------------------- | --------------------------------------------------------- |
| v1.0    | [`NFL_SPREAD_SCORECARD_v1.md`](./NFL_SPREAD_SCORECARD_v1.md)         | [`data/ops/lab/nfl-spread-scorecard-v1.json`](../../data/ops/lab/nfl-spread-scorecard-v1.json) |

## Machine twins

Schema + filled scorecards live under [`data/ops/lab/`](../../data/ops/lab/).

## Re-run

```bash
python3 scripts/lab/nfl_spread_validation_v1.py
```

Reads owned ops artifacts only (no Odds API scrapes). Missing series →
`N/A—DATA GAP`.

## Hard locks (summary)

- Protocol before results
- No inventing missing historical odds → `N/A—DATA GAP`
- No post-hoc bucket changes (version bump instead)
- No product tag flips from Lab
- RED can be a successful honest failure detection
