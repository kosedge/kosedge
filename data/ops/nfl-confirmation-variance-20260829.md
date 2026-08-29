# Confirmation + variance (KEI last leg) — 2026-08-29

**After #304 (snap_share_prior).** This leg only.

## Contract

Every committed pack / situation event is stamped `confirmation`:

| Level | Triggers | Mean shock | Variance |
|-------|----------|------------|----------|
| **high** | IR / named_starter / official depth | full (×1.0) | none (×1.0) |
| **med** | default accepted SoT | half (×0.5) | modest (×1.15) |
| **low** | beat-only / questionable / sleeper-weak | small (×0.1) | widen (×1.35) |

- Open competition stays a **mixture** (no crown). Sleeper / notes cannot close ATL-style races.
- Official high confirmation **may** close open competition.
- KEI surfaces expose **mean + uncertainty** (never mean-only).
- No new desk accepts; no scanner / rest-weather / shock_table_v1 rewrites.

## Files

- `services/model-service/src/services/nfl_confirmation_variance.py`
- `nfl_daily_intel.py` — ALLOWED `confirmation`; stamp `situation_events`; block notes close
- `nfl_kei_week1_reprice.py` — scale factor means by confirmation; log `mean` + `uncertainty`
- `tests/test_nfl_confirmation_variance.py`

## Out of scope

Live accepts, scanner rewrite, rest/weather edits, shock_table_v1 edits.
