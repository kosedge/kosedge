# t4555u / t4559u — T-08 Postgres evidence

**Draft. Do not merge. Do not deploy. NFL NO-GO. Coming Soon ON.**

Stacked on #637 tip `b752c038`. Does **not** touch W8 capture tip `385767a2` / PR #641.
Does **not** call Odds API. Predictive FAIL `f4c61237` still stands.

## Slate vs T-08 (t4559u)

T-08 is **not** the blocker for a W8 full-slate run today.

| Fact | Evidence |
|------|----------|
| Typed `week_cap` CAST + Integer bind | already on `origin/deploy-vercel` `tasks.py` (`_week_cap_nullable_predicate`) |
| T-08 | pytest proof that untyped `NULL` bind raises `AmbiguousParameter` and the typed predicate does not |
| Slate runner | `run_nfl_market_simulations` on Railway / local remat — uses the already-shipped CAST |
| Dedicated slate agent | `t4559u W8 full-slate engine run` (`bc-e1ed23ad`) — parallel, not waiting on this PR |

**STATUS: slate is NOT blocked by T-08.** This PR is evidence + fail-closed missing-input only.

## T-08 on this VM

Local `postgresql-16` cluster (no Docker). `policy-rc.d` blocks `service` start; `pg_ctlcluster 16 main start` works.

```bash
sudo pg_ctlcluster 16 main start
# role/db migtest / migtest / migtest on 127.0.0.1:5432
cd services/model-service
MIG_TEST_DATABASE_URL=postgresql://migtest:migtest@127.0.0.1:5432/migtest \
  PYTHONPATH=. python3 -m pytest -rs -v tests/test_nfl_week_cap_bind.py
```

**This VM:** **7 passed, 0 skipped** (4 T-08 bind + 3 missing-input). Transcript `t4555u_t08_postgres.txt`.

```
tests/test_nfl_week_cap_bind.py::test_week_cap_predicate_is_explicitly_cast PASSED
tests/test_nfl_week_cap_bind.py::test_prior_season_null_week_cap_sql_is_typed PASSED
tests/test_nfl_week_cap_bind.py::test_fail_closed_overlay_defaults_unchanged PASSED
tests/test_nfl_week_cap_bind.py::test_untyped_null_week_bind_raises_ambiguous_parameter PASSED
tests/test_nfl_week_cap_bind.py::test_full_engine_input_status_ok_when_both_sides_have_epa PASSED
tests/test_nfl_week_cap_bind.py::test_full_engine_input_status_context_fallback_not_missing PASSED
tests/test_nfl_week_cap_bind.py::test_full_engine_input_status_explicit_missing PASSED
```

Skip is **FAIL** unless `T08_ALLOW_SKIP=1`. Failure text is `T-08 BLOCKED_WITH_REPRO` with exact DSN, exception, and infra ask (postgres:16 / migtest — same as `pr-check.yml` services.postgres).

**T-08 status: EVIDENCED** (local 7/0 + prior CI 4/0 on `40522077899`).

## Missing-input (adjacent remat)

`_full_engine_input_status` after packaged / true-PR / matchup-pack fallback:

- both sides have EPA indices → keep `prior_source`
- no EPA, but all four context indices present → cold-start fallback (unchanged)
- else → **`MISSING`**, skip the game, do not invent 1.0/1.0

Return payload adds `games_missing_inputs` + `missing_inputs[]`. No scoring / holdout / cert change.

## Non-claims

- Not a certification PASS
- Not a holdout result
- Coming Soon stays ON
- No merge, no deploy, no Odds, no #641 edit
