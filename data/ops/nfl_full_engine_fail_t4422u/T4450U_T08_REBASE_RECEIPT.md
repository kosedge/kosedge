# t4450u — PR #637 rebase + T-08 receipt

**Draft. Do not merge. Do not deploy. NFL NO-GO. Coming Soon ON.**

Ryan t4450u (decision sha8 `20ea635f`) + IMV grade `a3799db3`.  
Predictive FAIL `f4c61237` **still stands**. `ed701ef3` is Mac-only non-claims bind; **this tip ≠ G-I certified**.

## SHAs

| Item | SHA |
|------|-----|
| Rebase base (`origin/deploy-vercel`) | `bfc89f57` |
| Previous #637 tip | `d8aec5dc` |
| Rebased FE-1/FE-2 commit (t4422u, no conflict) | `1af55efb` |
| T-08 CI wire (`pr-check.yml` Postgres step) | `23a26443` |
| This receipt commit / new tip | *(this commit)* |

Rebase was clean (1/1). FE-1/FE-2 files did not overlap #634–#636 site/Stat Drop work.

## T-08 (IMV exact path)

Local `postgres:16` with `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` = `migtest`.

```bash
cd services/model-service
MIG_TEST_DATABASE_URL=postgresql://migtest:migtest@localhost:5432/migtest \
  pytest -rs -v tests/test_nfl_week_cap_bind.py
```

**4 passed, 0 skipped.** Skip = FAIL for this task — not observed.

Proof lines (also `t08_postgres_4of0.txt`):

```
tests/test_nfl_week_cap_bind.py::test_week_cap_predicate_is_explicitly_cast PASSED
tests/test_nfl_week_cap_bind.py::test_prior_season_null_week_cap_sql_is_typed PASSED
tests/test_nfl_week_cap_bind.py::test_fail_closed_overlay_defaults_unchanged PASSED
tests/test_nfl_week_cap_bind.py::test_untyped_null_week_bind_raises_ambiguous_parameter PASSED
========================= 4 passed, 1 warning in 2.09s =========================
```

CI also runs this file in the existing PR Checks Postgres step (`MIG_TEST_DATABASE_URL` + `postgres:16` `migtest`). Other gates left in place.

## FE-1 / FE-2 still present

- **FE-1:** `test_simulator_baseline_unchanged_without_matchup_features` still pins `framework_version == "nfl-handicap-core-v3.1"`.
- **FE-2:** `test_week1_pack_aligned_indices_stay_dog_side_of_market` still imports `priors_from_matchup_pack` from `nfl_matchup_features` (not `src.tasks`).

## CI run ids (this push)

| Workflow | Event | Run id | Notes |
|----------|-------|--------|-------|
| PR Checks | `pull_request` | `40522077899` | in progress at receipt write |
| Production Gate | `pull_request` | `40522077630` | in progress at receipt write |
| PR Checks | `push` | `40522069591` | success (push no-op) |

## Remaining gaps (honest)

- Predictive FAIL `f4c61237` — pre-register only; **not CLEAR**
- Fair Lines PRODUCTION-CERT unbound / NO CLEAR
- `n=2998` still unlocated
- `ed701ef3` Mac-only; this tip is **not** G-I certified
- No Odds API, no seal, no Coming Soon OFF, no production deploy, no merge
