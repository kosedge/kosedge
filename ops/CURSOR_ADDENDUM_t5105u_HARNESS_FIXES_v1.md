# CURSOR ADDENDUM t5105u — harness / reader in-scope fixes v1

Date: 2026-11-01 · CERT=0 · DRAFT≠merge · in-scope fix chain  
Authority: OWNER t5105u B-amended · CoS order tip `ec7e0a36` · under CLEAR `4f3b9666` / `02ca8367`

Place a copy at `/workspace/ops/nfl_enterprise_green_t4359u/CURSOR_ADDENDUM_t5105u_HARNESS_FIXES_v1.md`.

## Preserve

Prior ACCEPT history stands. This addendum is a new tip only.

| Pin | Value |
| --- | --- |
| CoS ACCEPT | `7f9f7918` |
| CoS ACCEPT prior | `e549d23f` |
| Alex PASS_RO | `db8d27a2` / `43c04127` |
| CLEAR | `4f3b9666` / `02ca8367` |
| Prior #689 draft head | `f6b5b4c3ec4021fc64d86a36c863b483246be78b` |
| Prior #690 draft head | `45c6ee6efe0f1597ca29b6794e21640c209ec5c9` |

PRs remain DRAFT. Synthetic-only still. No real-outcome look. No de-vig "complete market benchmark" claim. No merge / deploy / paid Odds.

## What changed

### 1) Comparable-line probability (#690 harness)

`_lines_compatible` still allows a point-line difference when both numeric lines exist. Probability comparison is a separate bind:

- Emit `p_delta` only when forecast probability is bound to the actual quoted line/side.
- Bind if `probability_line` / `probability_side` (or `p_line` / `p_side`) match the quote, **or** the forecast prediction line equals the quoted line/side.
- Otherwise keep the comparison row (line_delta OK) and set `p_delta=None`, `p_compare=unbound_probability_line`.

Codex counterexample, using exact harness path:

- forecast spread −3.5 / `p_home_cover=0.58`
- quote spread −7.5 / price −110
- implied = 110/210 ≈ 0.5238095238095238
- **must not** emit `p_delta≈0.056190476190476124`
- does emit `line_delta=4.0` and `p_compare=unbound_probability_line`

Example fixture output was regenerated: KC spread −9.0 vs −9.5 and total 53.5 vs 54.5 now refuse `p_delta`; moneyline remains bound.

### 2) Timezone-free timestamps (#689 reader, merged into #690)

`normalize_quote_timestamp` / cutoff-join reader path no longer assign UTC to naive values.

- Qualified: explicit `Z` / offset, or tz-aware datetime.
- Or an explicit `source_timezone` contract (function argument, or `source_timezone` on the quote/game row). `UTC` is a named contract, not a default.
- Unqualified `'2020-09-10T16:00:00'` returns `None` and the join excludes the row as `unresolvable_timestamp`.
- Invalid zone names refuse (fail closed).

### 3) CI vs local (inventory only — not an all-checks-pass claim)

Focused local tests are not GitHub Actions. Failed check **names** on the prior draft heads:

**#689** run `41323879596` (head `f6b5b4c3`):

- Failed check: `PR Quality Checks` (workflow `PR Checks`)
- Failed step: `Check formatting` (`pnpm format:check` / `prettier --check .`)
- Prettier files: `data/ops/nfl-odds-reader-2020-2023-inventory.json`, `data/ops/nfl-odds-reader-2020-2023-inventory.md`, `ops/t5098u-1100-est-checkpoint.md`
- Skipped after format fail: `Run linter`, `Run type check`, `Run tests`
- Passed (not the focused pytest): `Vercel Preview Comments`, `Vercel – kosedge`, `Vercel – kosedge-vercel-push`, `inspiring-curiosity - kosedge`

**#690** run `41325417413` (head `45c6ee6e`):

- Failed check: `PR Quality Checks` (workflow `PR Checks`)
- Failed step: `Check formatting` (`pnpm format:check` / `prettier --check .`)
- Same three Prettier files as #689
- Same skipped steps: `Run linter`, `Run type check`, `Run tests`
- Passed (not the focused pytest): `Vercel Preview Comments`, `Vercel – kosedge`, `Vercel – kosedge-vercel-push`, `inspiring-curiosity - kosedge`

Prettier CI was **not** fixed in this chain. Do not treat focused local passes as all-checks-pass.

## New commit tips (code fixes; addendum commit is additional)

| PR | Branch | Code-fix commit |
| --- | --- | --- |
| #689 | `cursor/nfl-odds-reader-cutoff-join-17f0` | `26aad919876074504bfeda0e2200d9f50416c539` |
| #690 | `cursor/nfl-odds-comparison-harness-t5100u-f42c` | `ce51244aa5e24bf9a22bfc63bc5a01f44cfe2540` |

#690 also contains merge `d8298845e` (Package A timezone fix into the harness draft).

## Test counts

Prior focused local passes (reported on the previous draft heads; keep separate from CI):

- Reader: **12/12**
- Combined reader+harness: **22/22** (12 reader + 10 harness)

After this chain (local, `python3.11 -m pytest`):

```
cd services/model-service && PYTHONPATH=. python3.11 -m pytest \
  tests/test_nfl_odds_reader.py tests/test_nfl_odds_comparison_harness.py -q
..........................  26 passed
```

- Reader: **14/14** (prior 12 + naive-refuse + explicit `source_timezone` contract)
- Harness: **12/12** (prior 10 + Codex counterexample + bound-line positive path)
- Combined: **26/26**

## Out of scope (not done)

Real-outcome look · silent IF drop · weight retune · merge/deploy · paid Odds · claiming de-vig complete market benchmark · new planning · prettier/all-checks-pass waiver.

STOP · CERT=0 · DRAFT only
