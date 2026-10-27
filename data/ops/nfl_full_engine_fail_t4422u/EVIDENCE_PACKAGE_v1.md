# t4422u — Full-engine FAIL root-cause + independent repro

**Authority:** Ryan t4422u Oct 27 NFL hard-push (Engineering Lead / Cursor)  
**Base:** `deploy-vercel` `20d51f220ce772545161ae5ce4ed22041110a150`  
**Publication:** NFL NO-GO. Coming Soon ON. Draft PR only. Do not merge or deploy.  
**Holdout:** sealed. NR-1 injury archive not reopened. No protected-holdout access.

This package does **not** clear Full-engine FAIL (`f4c61237`). It identifies the exact
engineering FAILs that blocked an independent engine run, fixes those defects, and
records a reproducible command. Predictive / product cert status is unchanged.

---

## 1. Exact failing test IDs (current FAIL evidence)

### 1.1 Engineering unit FAILs on `20d51f22` (this VM, before the code change)

Transcript: `fail_baseline_sim.txt`  
sha256: see `SHA256SUMS`  
Command:

```bash
cd services/model-service
PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_simulator.py::test_simulator_baseline_unchanged_without_matchup_features \
  tests/test_nfl_simulator.py::test_week1_pack_aligned_indices_stay_dog_side_of_market \
  --tb=short
```

| ID | Result | Quoted FAIL |
|----|--------|-------------|
| `tests/test_nfl_simulator.py::test_simulator_baseline_unchanged_without_matchup_features` | **FAIL** | `AssertionError: assert 'nfl-handicap-core-v3.1' == 'nfl-handicap-core-v1'` (line 130) |
| `tests/test_nfl_simulator.py::test_week1_pack_aligned_indices_stay_dog_side_of_market` | **FAIL** | `from src.tasks import _priors_from_matchup_pack` → `ModuleNotFoundError: No module named 'requests'` (tasks.py:15). Prior cloud/PR 611 transcript also hit `sklearn` on the same import. |

Exit: **2 failed**. Log sha256 `42ff0172ab0c4285606bafe11afe0262addb65a5e031235fac797b3ec748a8a1`.

### 1.2 Fair product cert FAIL package (product-control, tests PASS as fail-closed)

Not a pytest red. The certified slot is **unbound** and the war-room practice SHA is **rejected**.

| ID / artifact | Status | Evidence |
|---------------|--------|----------|
| Fair Lines PRODUCTION-CERT Product harness | **NO CLEAR** | `docs/ops/NFL_FAIR_LINES_PRODUCTION_CERT_PRODUCT_2026-09-17.md` |
| Machine packet | `recommendation=NO_CLEAR` | `data/ops/nfl-fair-lines-production-cert-product-20260917/packet.json` |
| War-room `pe_drive_poss_v1` / `b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b` | **REJECTED_PRACTICE_SHA** — Alex **"all five gates FAIL"** | packet `alex_note`; per-gate IDs **not committed** |
| `pe_drive_poss_v2` | **DIAGNOSTIC_STOP** | same packet |
| Certified `run_id` + sha256 | **unbound** (`null`) | `cfb-edge-board-public.ts` |
| Smoke `scripts/nfl/nfl-fair-lines-production-cert-smoke.sh` | **43/43 PASS** (public stays dark) | `fair_lines_cert_smoke.txt` sha256 `15a3044c2a2dbe152d11a07b2eee6220e559a71d1664fe57b69d6486d375b633` |

Vitest file `apps/web/__tests__/lib/nfl-fair-lines-production-cert.test.ts` exists; this VM had no `apps/web` vitest binary (`ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL`). Mac/local: `pnpm exec vitest run __tests__/lib/nfl-fair-lines-production-cert.test.ts`.

### 1.3 Enterprise / full-engine predictive FAIL (stands)

| ID | Status | Evidence |
|----|--------|----------|
| `ats_vs_minus_110` | **RED** | hit_rate **0.495** n=1693 vs floor 0.5238 (`data/ops/nfl-enterprise-gates-latest.json`, generated 2026-07-28) |
| `clv_spread_sample` | **RED** | positive_rate **0.5092** n=601 vs floor 0.55 |
| `overall` | **RED** | `betting_product_ready: false` |
| Full-engine FAIL memo | **stands** until pre-registered rerun | sha8 `f4c61237` (full SHA **not in public repo**; cited on unmerged PR 610/631) |
| n=2998 game list | **unlocated / withdrawn** as cert evidence | PR 610 R-6 |

Regenerating `evaluate_enterprise_gates.py` on this VM only rewrote `generated_at` / example rows. **Reverted.** Committed artifact left at sha256 `9a78afdcd60f2fe32ad0ace016cf0556f500fb2ba95df3f15bc619cb4c8d3ef4`.

### 1.4 Skip that remains NOT EVIDENCED

| ID | Result | Why |
|----|--------|-----|
| `tests/test_nfl_week_cap_bind.py::test_untyped_null_week_bind_raises_ambiguous_parameter` | **SKIPPED** | `local Postgres not available` (line 109). T-08 / PR 631: skip is **NOT EVIDENCED**. Cloud VM has no local Postgres. Mac path: set `MIG_TEST_DATABASE_URL` / `DATABASE_URL` to `127.0.0.1` and re-run. |

---

## 2. Root-cause diagnosis

### FE-1 — stale framework identity pin

- **Files:** `tests/test_nfl_simulator.py:130` vs `src/services/nfl_handicapping_framework.py:12` (`NFL_HANDICAPPING_FRAMEWORK_VERSION = "nfl-handicap-core-v3.1"`) and `LOCKED_SCORING["framework_version"]` in `nfl_regression_diagnose.py:101-102`.
- **Mechanism:** the baseline test still demanded `nfl-handicap-core-v1`. Runtime has been v3.1 since the locked scoring identity. This is test/code drift, not a scoring change.
- **Not:** holdout retune, factor edit, or greenwashing by deleting the pin.

### FE-2 — week-1 pack guard coupled to the Celery/tasks import graph

- **Files:** `tests/test_nfl_simulator.py:387` imported `_priors_from_matchup_pack` from `src.tasks` (18k-line Celery module). `src/tasks.py:15` `import requests`; later `nfl_supervised_retrain` hard-imports `sklearn`.
- **Mechanism:** the helper is a pure EPA→index map. The test never needed requests / sklearn / Celery. Collection/import failed before the spread assertion ran.
- **After extract:** the same assertion (`spread > -1.5` and dog-side of market 2.6) **PASSES**. The week-1 pack math was not the FAIL; the import graph was.

### FE-3 — product cert / predictive RED (not fixed here)

- Product cert is fail-closed by design (`bindNflFairLinesCertifiedRun` → `unbound_certified_slot` / `rejected_practice_sha` / `diagnostic_stop`).
- Full-slate ATS/CLV RED is a 2026-07-28 committed gate result. Floors were not touched.

---

## 3. Fixes applied

1. **Identity pin** — `test_simulator_baseline_unchanged_without_matchup_features` now pins `nfl-handicap-core-v3.1` (LOCKED_SCORING). Comment records that this is not a scoring/holdout/factor change.
2. **Prior helper extract** — `priors_from_matchup_pack` lives on `src/services/nfl_matchup_features.py` and calls canonical `epa_to_strength_indices`. `tasks._priors_from_matchup_pack` is a re-export (no math change). Week-1 pack test imports the small module.
3. **Verified re-export** — `tests/test_nfl_tasks.py::test_priors_from_matchup_pack_aligns_base_strength_to_week_epa` **1 passed**.

**Not done (blocked, not invented):**
- No holdout rerun (`f4c61237` still required — see `PRE_REGISTER_FULL_ENGINE_RERUN_f4c61237.md`)
- No cert bind, no Coming Soon OFF, no PLAY ungate
- No local-Postgres T-08 proof
- No merge of #634–#636
- No NR-1 reopen
- Enterprise gates artifact not rewritten

---

## 4. Independently reproducible commands + results

Install declared deps (this VM used `scikit-learn==1.9.0`, `numpy==2.4.2`, `SQLAlchemy==2.0.32`, `pytest`, plus `requests`/`celery` only for suites that import `src.main` / `src.tasks`):

```bash
# A) Engineering FAILs that this PR addresses
cd services/model-service
PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_simulator.py \
  tests/test_nfl_regression_decompose.py \
  tests/test_nfl_564_remediation.py \
  tests/test_nfl_enterprise_gates.py \
  tests/test_nfl_efficiency_backbone.py \
  tests/test_nfl_week_cap_bind.py \
  --tb=line -rs
```

**This VM after fix:** **55 passed, 1 skipped** (Postgres T-08).  
Transcript `e2e_after.txt` sha256 `1cea21128893dc315a10d1de84902e069817bd8370f3496a00c902e21c17d322`.  
Exit 0.

```bash
# B) Fair product cert (fail-closed stays fail-closed)
bash scripts/nfl/nfl-fair-lines-production-cert-smoke.sh
```

**This VM:** **43/43 PASS**. Public still false.  
`fair_lines_cert_smoke.txt` sha256 `15a3044c2a2dbe152d11a07b2eee6220e559a71d1664fe57b69d6486d375b633`.

```bash
# C) Enterprise composite (committed artifact — do not treat regen as a new seal)
python3 -c "import json; p=json.load(open('data/ops/nfl-enterprise-gates-latest.json')); print(p['report']['overall'], p['report']['betting_product_ready'])"
# expected: RED False
```

Mac-only / private (not run here): IMV sealed runner `scripts/nfl/imv/nfl-imv-sealed-v2.4.sh` (PR **#609**, unmerged); memo body `f4c61237`; ADD141 Q9 7-name search; 2024–25 holdout.

---

## 5. What remains for IMV to grade

1. **Full-engine FAIL `f4c61237`** — still FAIL until the pre-register in `PRE_REGISTER_FULL_ENGINE_RERUN_f4c61237.md` is accepted and the unused rerun is executed by IMV (not this cloud VM).
2. **T-08** — `test_untyped_null_week_bind_raises_ambiguous_parameter` skip is still **NOT EVIDENCED**. Needs Mac/local Postgres.
3. **Five war-room gates** — still only the aggregate string; IMV should not invent IDs.
4. **n=2998** — still unlocated; do not re-earn from this PR.
5. **#634–#636** — CoS+IMV merge-readiness only; this PR does not touch them.
6. **Independent reproduction of this engineering path** — IMV should re-run §4 A+B on a second machine and match the pytest IDs (55 pass / 1 skip) and 43/43 smoke. Fingerprints of transcripts will differ by host; **test IDs and skip reason must match**.
7. **No certification PASS, no Coming Soon OFF, no deploy.**
