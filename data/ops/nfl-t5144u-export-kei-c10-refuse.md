# t5144u addendum — Export KEI C10 refuse

Authority: OWNER CLEAR t5144u **ee9b5a2c** · COS_ORDER sha8 **4e924a47**
CERT=0 · DRAFT≠merge · no deploy · no EVAL · no G5 · no #6 PASS claim

Institutional memory: **no prior grades** (engineering fail-closed check; not a recurring desk product).

R3 STOP disposition **81b6c0fc** is context only — this DRAFT does **not** continue R3.

## Chosen check

| Field           | Value                                                                                         |
| --------------- | --------------------------------------------------------------------------------------------- |
| Check id        | `EXPORT-KEI-C10-REFUSE`                                                                       |
| Map             | NFL GREEN eight-target **#6** (fail closed on missing/invalid data) + #695 inventory pref. (2) |
| Classification  | **EXISTING BUT UNVERIFIED** → evidence added                                                  |
| Contract ref    | `apps/web/scripts/export_kei_lines_nfl.py` @ **f5e3bb58** (bytes unchanged this DRAFT)        |
| Policy reused   | `except (URLError, TimeoutError, JSONDecodeError): return 1` before `json.dump(OUT)`          |
| Rounding reused | `round(float(spread\|total), 2)` · export keys `sport`/`keiCode`/`games`/`projSpreadHome`     |

T6-API-C10-CONSUMER-REFUSE (#695 tip **bff7c734**, already PASS_RO) is **not** re-opened.

## STEP 0 inspect (no pre-existing coverage)

| Location | Result |
| -------- | ------ |
| #695 inventory (`data/ops/nfl-t5137u-t6-api-c10-consumer-refuse.md` L29) | `Export KEI C10 refuse` = **EXISTING BUT UNVERIFIED** — “Impl exists; no test. **Not picked** (preference 2).” |
| `rg export_kei_lines_nfl` / `*c10*` / `*export*kei*` tests | No refuse test file. Script + T6 addendum mention only. |
| `apps/web/scripts/export_kei_lines_nfl.py` sha256 vs f5e3bb58 | **identical** `85d1d243ddf64bffad975e07f87584a1cb99483cab9db724d2fbe9a22d60473f` |

Not already covered → this DRAFT adds tests. No production script edit.

## Evidence this DRAFT adds

- `apps/web/tests_pipeline/test_export_kei_lines_nfl_c10_refuse.py`
- `apps/web/tests_pipeline/fixtures/export_kei_c10/fair_lines_success.json`
- `apps/web/tests_pipeline/fixtures/export_kei_c10/malformed.json`
- `policies/web-python-allowlist.txt` — new test file only (boundary check)

Cases (mocked `urllib.request.urlopen` only; `OUT` → tmp; controlled env; no Odds/model HTTP, no DB, no credential env):

| Mode | Process exit | OUT absent | OUT preexisting |
| ---- | ------------ | ---------- | --------------- |
| HTTP 503 (`HTTPError`, URLError subclass) | **1** | no file created (parent dir not mkdir’d) | bytes identical |
| HTTP 504 | **1** | same | same |
| `URLError("connection refused")` | **1** | same | same |
| `TimeoutError("timed out")` | **1** | same | same |
| malformed JSON fixture | **1** | same | same |
| valid synthetic success control | **0** | writes existing schema + `round(..., 2)` | — |

Success control proves the real parser/export path runs (`sport=nfl`, `keiCode=KEINFL`, `projSpreadHome=-3.26` from `-3.264`, `projTotal=47.55` from `47.551`, `start_time` wins over `game_date`). Unconditional refuse cannot pass.

Source oracle: refuse `return 1` stays **inside** the transport/JSON `except`; `json.dump(OUT)` stays **after** that try.

## Tests run (offline, no Odds HTTP)

```
cd apps/web && python3 -m pytest tests_pipeline/test_export_kei_lines_nfl_c10_refuse.py -v
# 25 passed
```

## Addendum — payload/schema gaps (reported, not invented)

No new eligibility / refuse rules were added. Observed on the f5e3bb58 source and left as-is:

1. **Empty / missing `lines` is not a refuse.** After a 200 JSON body, `payload.get("lines") or []` writes `{"sport":"nfl","keiCode":"KEINFL","games":[]}` and returns **0**. Evidence: `export_kei_lines_nfl.py` L39–L68.
2. **Blank `home_team` / `away_team` is a skip, not a refuse.** Existing `if not home or not away: continue`. Success fixture includes one blank-home row; export still exits 0 with one game. Not an invented threshold.
3. **Non-numeric `spread_home` / `total_mean` after a successful JSON parse is uncaught `ValueError`** (`round(float(spread), 2)`). Not in the `except` tuple. Would abort before OUT write via traceback, not the documented `return 1` branch. Not closed here.
4. **Any `HTTPError` (not only 503/504)** is a `URLError` subclass, so it already hits the existing refuse branch. Tests exercise 503/504 as specified; no extra status policy minted.

## Holds

Do **not** relabel eight-target #6 PASS. Independent RO next. CERT=0.
T6 (#695) remains the page-data consumer check. R2-C/G5 retained. R3 not continued.
