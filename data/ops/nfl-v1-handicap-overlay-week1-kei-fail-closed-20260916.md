# NFL V1 handicap-overlay cert — Week 1 KEI publish fail-closed (2026-09-16)

**Ryan:** ACCEPT CONDITIONAL + AUTHORIZE REPAIR
**Status:** CONDITIONAL (does **not** auto-convert to CLEAR after this repair)
**PR target:** `deploy-vercel` (draft; do not merge from agent)
**Branch:** `cursor/nfl-week1-kei-fail-closed-169b`

## Product locks left untouched

- Fair Lines stay dark / Coming soon ON (`NFL_EDGE_BOARD_PUBLIC_ENABLED = false`)
- PLAY / Best Bet / Kelly remain suppressed
- N4+ V1.0 publication floor stands
- No B0 / YTD retune
- `run_injury_kei_window` stays dark / library-only (not wired)

Coming soon is **not** the repair. The mix path is hard fail-closed even if Coming soon is later flipped ON.

## Hypothesis (verified)

In `services/model-service/src/routes/nfl.py`, `apply_week1_kei_reprice` mixed Week 1 KEI into `handicap_markets` after `resolve_model_and_handicap`. Those columns then drove published fair/edge:

- `_nfl_fair_lines_impl` — `spread_home` / `total_mean` / win probs → `spread_edge` / `total_edge` / `ml_edge_prob` / publish tags / `handicap_*`
- `_load_kei_week_win_prob_lines` — survivor KEI overlay win% (`home_win_prob` / `handicap_home_win_prob`)

Coming soon gated customer HTML. The code path was live.

## Repair

| Surface | Change |
|---------|--------|
| Publish binder | `apply_week1_kei_reprice_for_published_fair` — identity only; never calls the live mixer |
| Lock | `WEEK1_KEI_PUBLISH_MUTATE_FAIR = False` (not env-gated) |
| Fair-lines | Uses the binder; Week 1 pack is not loaded on the publish path |
| Survivor KEI overlay | Same binder |
| Library | `apply_week1_kei_reprice` remains for unit/ops tables only |

## Mutate-fair V1.0 limitation

Injury / rest / weather **bake into B0 at remat**. Stamped `model_*` already carries overlay-class factors. Do **not** describe Week 1 KEI (or any overlay) as an independent layer on frozen fair.

V1 published fair/edge = stamped handicap from remat. Read-time Gate B mix is a dead path.

## Tests (unreachable proofs)

`services/model-service/tests/test_nfl_week1_kei_publish_fail_closed.py`

1. AST: `routes/nfl.py` must not call `apply_week1_kei_reprice`.
2. AST: the publish binder must not call the live mixer.
3. Lock is hard `False`; binder source has no `os.getenv` / Coming-soon unlock.
4. Library still moves NE@SEA (travel −1.0); binder returns identity.
5. Poison: live mixer raises if reached — fair-lines Week 1 + survivor overlay stay at stamped numbers.

Re-wiring the live mixer into publish columns fails these tests.

## Out of scope

- Injury KEI cadence wiring
- B0 / YTD retune
- Promoting CONDITIONAL to CLEAR
- Flipping Coming soon / PLAY chrome
