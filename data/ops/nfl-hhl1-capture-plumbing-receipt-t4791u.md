# RECEIPT t4791u — H-HL-1 CAPTURE PLUMBING ONLY

**DRAFT PR only. Not merged. Not deployed. Capture remains OFF.**

| | |
| --- | --- |
| Authority | DECISION **2806545b** · ORDER **e0159e65** · protocol **a9f1c28f** · PASS_PROTOCOL **d359ce54** · CoS ACCEPT **3d80968f** |
| Parent paper | **7b4d70ac UNTOUCHED** (not opened, not edited) |
| Base | `deploy-vercel` @ `1b39f4e9` |
| Branch | `cursor/t4791u-hhl1-capture-plumbing-2bde` |
| Implementation SHA | _filled at seal_ |
| Tip SHA | _filled at seal_ |
| Receipt file sha256 | _sidecar after seal_ |

Full authority digests (recomputed on the filed packets this turn — MATCH):

- DECISION `2806545b3ed1b643e4dfdc5e44aea10b50329ae32660d26ec85e36954339d2c8`
- ORDER `e0159e6516092e6a81742663c4703bb7b69d03603a7b8691ee3a03409c16681f`
- protocol `a9f1c28f1cbbc0f623603f78b340e09aeff6ecb54926a3fed34e1cf4ee2a242a`
- PASS_PROTOCOL `d359ce54ad8c59f005385a226c9a964e183e1e2d724b7244076db76fd14e87c9`
- CoS ACCEPT `3d80968f5f3f057c3b49f98df543d82fd94b634851f682fa610dd833a675b7eb`

## What shipped

Minimum prospective-capture **plumbing** so a later CLEAR can collect timestamped, provenance-complete L1 availability rows.

New isolated package (not wired to tasks, routes, nowcast, simulator, or CLEAR-A ledger):

`services/model-service/src/services/nfl_hhl1_capture/`

| File | sha256 |
| --- | --- |
| `__init__.py` | `7ecc3632f2c8b803ff03458b7849210184123f2c4a7459b26fbf709bc94aa6be` |
| `constants.py` | `2d0934a484b7ecb58ab06b817d4179cb2c590f5bfd64ff638ce21e33db192a57` |
| `gates.py` | `5c6d7b5d774510b4a9e2be9e19769221f88491b221cbf61880730e947bb233a7` |
| `identity.py` | `1de76ecf92a6edb81f0a9c98baa242d3fe4f702f7044b423a999eada7558720a` |
| `schema.py` | `2be29cbe7d270876feb5ddd49181804638d721878920d670c424c299487fe38b` |
| `validate.py` | `14f863991207c618b06e2e606874913b3bd18315ee4e4274466d72876276a7ac` |
| `tests/test_nfl_hhl1_capture_plumbing.py` | `27956bb0bea7c40c6f6867ef9de2f92bbad9c684576cfa2d985e42c7c5cb18fb` |

Scope delivered vs DECISION §AUTHORIZED 1–6:

1. Schema/interfaces — immutable event identity (`capture_id`), source provenance, capture_ts triple + kickoff cutoff, expected starter state, missingness enum, rejection reasons. Aligned to protocol §5 L1.
2. Deterministic validation — stale / late / as-of / cutoff-mismatch / ambiguous / duplicated / provenance-incomplete / identity-mismatch.
3. Fail-closed unavailable (`SOURCE_DOWN` / `NOT_PUBLISHED` → exclusion record, no imputed row) and nowcast OFF everywhere (env cannot lift).
4. Unit + negative-path tests; synthetic fixtures only (`00-SYNTH-*`, `example.test` URLs, week 99).
5. Local RO verify — package not imported by any live caller; acquire / fetch_nowcast / odds / score / publish / baseline-builder / historical-reconstruct all raise; AST import scan clean.
6. This sealed receipt.

Hard locks in code: `HHL1_*_AUTHORIZED = False` for live capture, external acquisition, nowcast, scoring, publication, historical reconstruction, model execution.

Admitted source id (not activated): `official_nfl_injury_report` only.

## Tests run

```
cd services/model-service
python3 -m pytest tests/test_nfl_hhl1_capture_plumbing.py -q
# 55 passed
```

No nowcast tests, no simulator tests, no holdout, no Odds, no live HTTP.

## Local RO verification

- `rg nfl_hhl1_capture src` outside the new package → **none**
- git diff vs `origin/deploy-vercel` does **not** touch `nfl_injury_nowcast.py`, `nfl_simulator.py`, `nfl_handicap_ledger/*`, `tasks.py`, routes, CLEAR-A, #662/#663, efficiency STANDBY
- worktree nowcast sha256 still `73cad579…`
- worktree simulator sha256 still `52d9e909…` (conflict with protocol pin `9b61c5c3` preserved, not selected)
- `verify_plumbing_inert()` → `inert=True`

## Binding residuals (not waived)

**R1 — simulator SHA conflict.** Protocol/merge pin `9b61c5c3` vs tip bytes `52d9e909`. Both recorded as `SIMULATOR_EXECUTABLE_IDENTITY = UNRESOLVED_CONFLICT_9b61c5c3_vs_52d9e909`. Plumbing does not import or execute `nfl_simulator.py`. Do **not** select either pin for scoring.

**R2 — calibration UNVERIFIED.** 2013–2025 team-week claim remains a code comment on `nfl_injury_nowcast.py` `73cad579` L283–290. Table sha is an opaque pin only. No rebuild. No protected-sample touch. No nowcast import.

**R3 — provisional protocol constants, not empirically validated.** `decision_ts = kickoff − 90m`; baseline snap threshold `≥ 0.50`; Questionable kept (weight not applied). **Rating-window definition = `UNRESOLVED`.** `build_baseline_personnel_ref()` raises; any invented window string on a row REJECTS.

**R4 — field names ≠ permission.** L1 uses `offense_multiplier` / `defense_multiplier`. Presence of `injury_nowcast_*` on a capture row, or any nowcast/postgres-injury source id, REJECTS while nowcast is OFF.

## Unresolved assumptions (explicit)

1. Exact simulator executable identity (R1) — future **scoring** CLEAR.
2. 2013–2025 calibration remains UNVERIFIED (R2) — do not convert the comment into a verified claim.
3. Rating-window length/definition vs G34 (R3) — future CLEAR must pin it; this plumbing will not invent it.
4. Official NFL injury report path is EXISTING BUT UNVERIFIED and **not activated**.
5. nflverse snap counts as baseline input are EXISTING BUT UNVERIFIED; builder not implemented.
6. Odds HOLD `70c56700` — no close/line_at_decision acquisition.
7. Parser does not exist; `parser_version` is pinned to `hhl1-capture-plumbing-v0-no-parser`.
8. Persistence (0444 batch + sidecar writer) is **not** implemented — identity index is in-memory per validation batch only.
9. Delta magnitudes on a valid synthetic row are caller-supplied numbers for schema completeness; this CLEAR does not compute, fit, or score them.
10. `PASS_PROTOCOL ≠ capture CLEAR ≠ scoring CLEAR`.

## Next authorization required

A **separate Ryan capture/execute CLEAR** is still required before any live capture. A **separate scoring CLEAR** is required before any model execution (and must name the exact simulator file sha). Odds HOLD `70c56700` must be lifted by Ryan before (a)/(b)/economic legs are computable.

This receipt does **not** authorize: live capture · external acquisition · paid API / Odds · historical reconstruction · scoring · model execution · parameter fitting · holdout access · merge · deploy · publication · E1 / W8 / #663 / E2 / C10 / CERT / F2 changes · H-QB revival.

## Review request (narrow)

Please review the **acquisition / provenance boundary** only:

- Can any path in this package acquire, nowcast, score, or publish?
- Do rejected sources (nowcast surface, Postgres injuries, news, market fields, `injury_nowcast_*` names) fail closed?
- Is `capture_id` / `source_snapshot_id` / as-of triple sufficient to make a later live row provenance-complete?

Not requested: formatting, naming nits, or expansion into fetch/parser/writer/eval.

Locks: NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · Odds HOLD 70c56700 · nowcast OFF
