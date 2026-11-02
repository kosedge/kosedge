# CODEX_CHALLENGE_t4740u_HANDICAP_CLEAR_A_v1

**Verdict:** `CHALLENGE_FILED`  
**Not a grade:** this paper is **not** `PASS_CLEAR_A` and **not** `FAIL_CLEAR_A`. IMV grades after this challenge closes.  
**Role:** Codex — independent adversarial challenger. Paper only. No repairs. No product commits. No merge. No deploy. No capture. No self-grade.

| Field | Value |
|---|---|
| Authority | COS_ORDER_CODEX_t4740u · DECISION d744fa87 · PASS_PAPER a31035eb · paper 243a384e |
| Challenged tip | `c525210170fd09864b7232974b37dfc56f2ef4ab` |
| Implementation | `161df079c1c9ff8f752718c35933097e342fab0b` |
| Intermediate stamp (superseded) | `3e29a0a7da78d9f47be63ca7387eac6b3b8c30f9` |
| Base | `deploy-vercel` @ `209e90aa4a3f7edca15592af4cdd2f3c44f8b4c4` |
| DRAFT PR | https://github.com/kosedge/kosedge/pull/657 (`isDraft: true`, still draft at challenge) |
| Evidence sealed | CURSOR_EVIDENCE_t4740u_HANDICAP_CLEAR_A.md · RECEIPT tip c5252101 |
| Locks held in this challenge | NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF |

---

## 0. Method

Re-read tip diff vs `209e90aa` (9 files, +1053/−43). Read IF path, ledger package, D3 module, `pre_blend_model_markets_from_diagnostics`, live callers `tasks.py` / `routes/nfl.py`, and `infra/db` migrate discovery. Independently recomputed D3(ii) sha256 on a `209e90aa` worktree. Re-ran `tests/test_nfl_handicap_clear_a_d3.py` on the tip tree: **5 passed in 0.06s** (oracles still green; challenge is about what those greens fail to lock). Probed ledger rejects with crafted rows under `/tmp` only.

This paper does **not** change product behavior. Findings are for IMV / CoS.

---

## 1. Hunt results (CoS order items 1–7)

| # | Hunt | Result |
|---|---|---|
| 1 | Default/live path silent replacement | **NONE FOUND** for a live flip. See §3. |
| 2 | D3(i) vacuity | **FILED (weak oracle, not fully vacuous).** See F8. |
| 3 | D3(ii) truncated hash / bad pin | **NONE FOUND.** Pin independently matches `209e90aa`. See §4. |
| 4 | D3(iii) incomplete vs L1 / impute / TZ / overwrite | **FILED.** See F5, F6, F7. |
| 5 | Ledger not append-only in practice | **FILED.** See F1–F4, F10, F11, F13. |
| 6 | Overlay / MIF / HF bleed | **FILED (contract smear, overlays still OFF).** See F9. |
| 7 | Scope creep | **NONE FOUND** on tasks/routes/infra/db/web/F2/CERT/#655/capture/scoring/promotion. Residual: working JSONL store is more than DDL. See §6. |

---

## 2. Findings

### F1 — L0 `market_blend MUST = 0` accepts any value in `[0, 1)` (and `False`)

`validate_l0_row` does `blend_n = int(blend)` then requires `blend_n == 0` (`validate.py` ~102–107).

Measured on tip:

- `market_blend=0.3` → **ACCEPTED** (`int(0.3) == 0`)
- `market_blend=False` → **ACCEPTED** (`int(False) == 0`)

Blueprint L0: `market_blend MUST = 0`. A contaminated IF row with the live default weight **0.30** (or any float `< 1`) stores as Independent Fair. This is a fail-open hole in the delivered L0 contract, not a test skip.

### F2 — `store.append` + caller-chosen `prediction_id` bypasses validation and identity

`envelope_from_row` (`validate.py` ~150–158) uses `row["prediction_id"]` when present and **does not** re-derive or check it against `make_prediction_id`. `AppendOnlyHandicapLedger.append` (`store.py` ~58–78) only requires a non-empty id and that the id is new.

Measured: `store.append({"prediction_id": "hl_attacker_chosen", "layer": "L1", "forecast_label": "independent_fair", "payload": {"junk": True}})` → **ACCEPTED**. No L1 required fields, no as-of check, invented identity.

Claimed “immutable prediction identity” is only a duplicate-id guard on whatever string the caller supplies.

### F3 — JSONL reload is last-wins, not append-only

`store.py` ~38–47: on load, duplicate `prediction_id` lines overwrite `_ids[pid]` while both lines remain in `_rows`.

Measured: file with two `{"prediction_id":"same","n":1|2}` lines → `len(store)==2` and `get("same")["n"]==2`. Disk history can silently replace the indexed row. No delete API is required to get replace semantics.

### F4 — Business identity is not unique; Python store and DDL disagree

`make_prediction_id` hashes **payload** (`identity.py` ~20–42). Same `(layer, forecast_label, game_id, as_of_ts, capture_id, schema_version)` with a changed `delta` is a **new** id.

Measured: two `commit_l1_stage` writes of the same L1 keys, `delta` 0.0 then 1.5 → both accepted (`hl_fbb2ca47…`, `hl_e45c16bf…`), store length 2. That is a logical overwrite via append.

DDL unique index (`ddl_clear_a.sql` ~29–32) is on those identity columns **without** payload. If the SQL is ever applied, the same pair would **REJECT** in Postgres and **ACCEPT** in the Python store. The “never overwrite” test only re-appends the **exact same envelope** (same id). It does not lock business identity.

### F5 — D3(iii) timezone / naive trap (measured both directions)

`parse_ledger_ts` (`validate.py` ~40–41) assigns `timezone.utc` to naive datetimes.

Measured:

- `as_of_ts="2026-10-29T17:00:00"` (naive → 17:00 UTC) vs `decision_ts="2026-10-29T16:00:00-04:00"` (20:00 UTC) → **ACCEPTED**. If the naive stamp was America/New_York 17:00, it is **after** decision and should REJECT.
- `as_of_ts="2026-10-29T15:00:00-04:00"` (19:00 UTC) vs naive `decision_ts="2026-10-29T16:00:00"` → **REJECT** `as_of_ts > decision_ts`. A valid ET-ordered pair fails.

D3(iii) fixtures use `Z` on both sides only. Naive / mixed-offset paths are untested and not fail-closed.

### F6 — Impute / default paths the evidence says do not exist

Evidence: “no impute.” Measured imputes on the delivered contract:

| Path | Behavior |
|---|---|
| `envelope_from_row` `as_of_ts` | `_field_from(as_of_ts) or captured_at` — L4 as_of **imputed** from `captured_at` (measured) |
| `envelope_from_row` `baseline_ref` | falls back to `baseline_personnel_ref` (L0/L1 field smear) |
| `envelope_from_row` missing refs | `source_snapshot_id=""`, `registry_id=""` (measured on L0) |
| `schema_version` | defaults to `LEDGER_SCHEMA_VERSION` when omitted |
| `store.append` `created_at` | written as `_utc_now()` when missing |
| IF payload mus | `if_margin_mu if … is not None else 0.0` (invented 0) |
| DDL | `missing boolean DEFAULT false`, `payload jsonb DEFAULT '{}'` |

L1 validate does **not** impute the five D3 fields (those omitted rows reject). The hole is everything around that narrow gate.

### F7 — D3(iii) required-field list is narrower than blueprint L1

Blueprint L1: `{capture_id, factor, entry_point ∈ {…}, delta, uncertainty, source_snapshot_id, as_of_ts, registry_id, baseline_ref}`.

D3 sentence and `L1_REQUIRED_FIELDS` only: `capture_id, as_of_ts, baseline_ref, registry_id, source_snapshot_id`.

Measured: L1 row **without** `factor`, `entry_point`, `delta`, `uncertainty`, `missing` → `validate_l1_row` **ACCEPTED**. A blank delta can commit. `entry_point` is checked only if present.

This matches the D3 *sentence* and misses the L1 *contract*. Evidence “missing required L1 field” overclaims relative to 243a384e L1.

L0 required set also omits blueprint `off_eff_*`, `def_eff_*`, `pace_*`, `sigma` (and treats `market_blend` only via F1’s broken `int()`).

### F8 — D3(i) is a weak / partially circular oracle (not a free pass)

What the test actually does (`test_nfl_handicap_clear_a_d3.py` ~86–109):

1. Compare `independent_fair_mus(if_out)` (dedicated payload floats) to `pre_blend_model_markets_from_diagnostics(blended)`.
2. Repeat the helper on **`if_out` itself**.

The helper (`nfl_model_handicap.py` ~90–101) does **not** re-run the IF path. It reads `diagnostics.market_blend.pre_blend_*_mean` (already `round(..., 3)` in the simulator) and then `round(..., 2)`.

Measured on the sealed fixture (seed 47401, week 8, markets 3.5 / 43.5):

| Quantity | Value |
|---|---|
| IF payload `margin_mu` | 0.15714686663257818 |
| Helper (2 dp) | 0.16 |
| abs delta | 0.00285 ≤ 0.01 |
| IF `markets.spread_home` | −0.16 |
| Blended `markets.spread_home` | +0.94 |
| Blended post-blend margin mean | −0.94 |
| IF vs blended published spread | **1.10 pts** |

So D3(i) **would catch a full failed de-blend** of the payload field (gap ~1.10 ≫ 0.01). It is **not** vacuous for that failure.

It **is** weak / incomplete:

- **Float-round to pass:** the specified helper rounds to 2 decimals; tol 0.01 is larger than that rounding grain. The evidence table itself is 0.157 vs 0.16.
- **Wrong object:** D3(i) locks `independent_fair.margin_mu` / `total_mu`, which are copied from the IF-branch pre-mean **before** published `markets` are built (`nfl_simulator.py` ~615–620 vs ~690–710 vs ~851–858). A later bug that blended the draws but left those payload fields pre-blend would still pass. The test never asserts `if_out["markets"]` vs helper or vs blended markets.
- **Second assert is circular:** helper on IF diagnostics reads back `pre_blend_margin_mean=round(if_margin_mu, 3)` that the IF branch just wrote.
- **Week 8 only:** early-season disagreement boost (weeks 1–4) is not in the fixture.

### F9 — HF / MIF contract smear; L5 rule is comment-only

`test_if_hf_mif_coexist_without_overwrite` stores an **L1 delta** with `forecast_label=handicapped_fair`. Blueprint: L1 = `HandicapDelta[]`; HF is the L2/L3 forecast. Labeling deltas as HF teaches a later L5 to treat delta rows as fair lines.

`validate_l4_row` rejects labels `independent_fair` / `model_fair` but **accepts an empty label** (measured). MIF is not forced to `market_informed_fair`.

L5 “never reads MIF as fair” exists only as comments in `schema.py`. No decision surface is in this tip (overlays remain OFF — see §5). This is bleed in the **schema**, not a live overlay enable.

### F10 — DDL “append-only” is theater if anyone applies it

`ddl_clear_a.sql` ~34: `REVOKE UPDATE, DELETE … FROM PUBLIC`. Table owner (the role that `CREATE`s) retains UPDATE/DELETE. No trigger. `CREATE TABLE IF NOT EXISTS` plus `DEFAULT` imputes (F6). Comment says “Do not apply on any env” — that is process, not a technical lock.

Not in `infra/db`. Migrate discovery only accepts `NNN_name.sql` under `infra/db` (`db_migrations/discovery.py`). `ddl_clear_a.sql` would **not** auto-apply on Railway unless copied and numbered. Held as migrate risk; not held as an append-only guarantee.

### F11 — Missing L4 identity raises `ValueError`, not `HandicapLedgerReject`

Measured: L4 envelope without `capture_id` / `game_id` → `ValueError: all prediction_id components required`. Callers catching only `HandicapLedgerReject` can miss a fail-closed stage fail.

### F12 — Sealed evidence packet mis-identifies the challenged HEAD

On tip `c5252101`, `docs/ops/NFL_HANDICAP_CLEAR_A_EVIDENCE_t4740u.md` Identity table still says Tip SHA `3e29a0a7…` (previous stamp). `c5252101` only added the PR URL and moved the printed SHA one commit **behind** HEAD. CoS RECEIPT correctly names `c5252101`. The in-repo packet is not self-identifying at the sealed tip.

### F13 — `commit_l1_stage` is not atomic

All rows are validated, then appended one by one (`validate.py` ~187–201). If append #2 raises (duplicate id), append #1 is already on disk. D3(iii) uses single-row stages only.

---

## 3. Hunt 1 — silent default-path replacement (NONE FOUND)

Checked and held:

- `independent_fair: bool = False` is **KEYWORD_ONLY** (`simulate_nfl_game` signature after `*`).
- `NFL_INDEPENDENT_FAIR_PATH = False` is a constant. Simulator does **not** read an env kill-switch. Stray `NFL_INDEPENDENT_FAIR_PATH=1` does nothing (the constant is unused except in tests asserting it is False).
- Default return **omits** `forecast_label` / `independent_fair` keys (early `return result`).
- Live callers unchanged vs `209e90aa`: `tasks.py` ~4967 and `routes/nfl.py` ~4893 call `simulate_nfl_game(...)` without the flag.
- `git diff --stat 209e90aa..c5252101` on `tasks.py`, `routes/nfl.py`, `infra/db`, `apps/web` is empty.

Residual (not a current flip): any future `simulate_nfl_game(..., independent_fair=<truthy>)` or `**kwargs` that includes that key would take the IF branch. Not wired now.

---

## 4. Hunt 3 — D3(ii) pin / truncation (NONE FOUND)

Canonical sha256 on the **full** default-path dict, fixture as published:

`75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224`

Recomputed on a clean `209e90aa` worktree with the same inputs: **match**. Recomputed on tip default path and `independent_fair=False`: **match**. Keys on both trees: `decomposition, diagnostics, game_id, inputs, markets, model_version, simulation_count`. Hashing that subset equals the full hash because those are all keys — a **new** default-path key would change the digest. This is not a truncated-payload oracle.

`default=str` would hide a type-only change; no such type was added on the default path. Side effects (files/DB) are not in the hash; the simulator return is the D3(ii) object. Week 1–4 blend weights are not in this fixture (observation only; D3(ii) as written is fixed seed + fixed inputs).

---

## 5. Hard-stop checklist (this tip vs 209e90aa)

| Stop | Held? |
|---|---|
| data capture | **Held in production.** Schema + `/tmp` test JSONL only. Latent write class exists (F2/F3). No capture source named, no rows in prod stores. |
| vendor purchases | Held — not in diff |
| Handicap overlays ON any env | Held — no overlay flag/env flip; `routes/nfl.py` still stamps `overlays_off: True` (untouched) |
| predictive experiments / scoring / promotion | Held |
| merges / deployments | Held — #657 still `isDraft: true`, `baseRefOid=209e90aa` |
| API restore / C10 | Held — routes untouched |
| F2 / CERT / Coming Soon | Held — `apps/web` not in diff |
| S1/EPA · H-QB · Lane B · KEI mint · Railway #655 | Held — not in diff |
| `infra/db` migrate / Railway apply | Held — DDL not numbered under `infra/db` |

---

## 6. Scope (hunt 7)

**Touched (tip vs 209e90aa):**

- `services/model-service/src/services/nfl_simulator.py` (IF opt-in + default-path re-indent of existing blend)
- `services/model-service/src/services/nfl_handicap_ledger/*` (new)
- `services/model-service/tests/test_nfl_handicap_clear_a_d3.py` (new)
- `docs/ops/NFL_HANDICAP_CLEAR_A_EVIDENCE_t4740u.md` (new)

**Not touched:** `tasks.py`, `routes.py` / `routes/nfl.py`, `infra/db/*`, web/F2/CERT/Coming Soon, Railway #655, S1/EPA, H-QB, Lane B, KEI, overlays, capture.

Working JSONL/`AppendOnlyHandicapLedger` is more than “schema only.” Authorized CLEAR-A text allows ledger schema; the store is the implementation of that schema. Challenge does not treat the store’s existence as scope creep. Challenge **does** treat its bypasses (F2–F4) as contract defects.

---

## 7. What implementer evidence got right (so IMV does not re-open a clean item)

- Default blended path output is byte-identical to `209e90aa` on the pinned fixture (independently reproduced).
- IF path, when used, does not shift Monte Carlo draws; published IF vs blended spread differs by ~1.10 pts on the fixture.
- Production callers were not wired.
- D3 module exists, is fail-closed on the five listed L1 fields and on `as_of_ts > decision_ts` when both stamps are `Z`.
- Duplicate **exact** `prediction_id` rejects on the in-memory/JSONL `append` path.
- #657 remains draft. No merge, no deploy in this packet.

---

## 8. Close

**`CHALLENGE_FILED`.** Concrete defects are F1–F13. Clean hunts are silent live replacement, D3(ii) pin/truncation, and hard-stop / scope surfaces listed in §3–§6.

IMV validates next. Codex does not grade PASS/FAIL.

Paper only · no repairs · no merge · no deploy · no capture  
NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF
