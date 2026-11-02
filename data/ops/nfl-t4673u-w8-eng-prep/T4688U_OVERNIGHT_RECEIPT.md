# t4688u OVERNIGHT P1 receipt — deepen DRAFT #653

**Authority:** DECISION_RYAN_t4688u_OVERNIGHT_W8_READINESS_SPRINT.md sha8 **9912d619**  
**Parent prep:** `W8_ENG_PREP_CONTRACTS_t4673u_v1.md` sha256 `127f4624…`  
**Parents:** Codex **88a08cae** · IMV RETURN **75141507**  
**Locks:** NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · B HOLD (do not merge / not production CLEAR)  
**Unrelated freeze:** #650 tip `9e851852` — not touched.

`no prior grades` in `data/knowledge/`.

---

## What landed on this draft tip (failing → passing)

| # | defect | land | tests |
|---|---|---|---|
| 1 | Injury-impact moves market / stdev at conf=0 | `nfl_handicapping_framework.py`: `error_regime` uses `gated_injury_impact = avg * injury_conf`; `injuries_depth.available` requires `injury_conf > 0` so coverage does not flip | `test_t_c1_stdev_*` |
| 2 | Fixtures bypass builders / pins | Draft builders `nfl_w8_forecast_builders_t4688u.py` + C3 sha refuse. **Not** wired into `#645` emit script (file absent on this tip) | `test_t_c1_pin_*` |
| 3 | No EPA week cutoff / silent 2025 prior | `build_current_strength` week≤7 exclude or refuse; empty / week.max<7 → `MissingCurrentStrength`; never opens 2025 pack | `test_t_epa_asof_*` |
| 4 | Fabricate W8 PRESENT / drop flags | `last_designated_week` (not max week); pack flag PRESENT only with official SoT pin; G3 flags always kept when pin absent | `test_t_g3_*` |
| 5 | Vacuous Odds test (`"False" in text`) | Import/call-form token lock + runtime `market_blend.*_applied is False` on C1 pair. No Odds HTTP. #650 untouched | `test_t_c7_*` |

C1 hashed fixtures (seed 4643 / 1200) reproduced Codex means-equal / spread-moved **before** the framework gate; after the gate, markets + `stdev_widen` match.

## Test list (16)

```
tests/test_nfl_w8_eng_prep_contracts_t4688u.py
  test_t_c1_stdev_1_injury_impact_does_not_move_markets
  test_t_c1_stdev_3_totals_overlay_stdev_stays_zero_at_conf_0
  test_t_c1_stdev_protection_removed_raw_impact_moves_helper
  test_t_c1_pin_1_builder_is_executed_not_grepped
  test_t_c1_pin_2_c3_sha_refuse
  test_t_c1_pin_3_week8_epa_does_not_enter_w1_w7
  test_t_epa_asof_2_grain_flag_set
  test_t_epa_asof_3_empty_refuses_and_does_not_open_2025_prior
  test_t_epa_asof_3b_week_max_below_7_refuses
  test_t_epa_asof_refuse_weeks_above_cap
  test_t_g3_1_empty_w8_stubs_do_not_become_week8
  test_t_g3_2_nflverse_w8_designations_do_not_mint_present
  test_t_g3_3_completeness_not_from_pack_week
  test_t_g3_4_one_fixture_writers_agree
  test_t_c7_odds_tokens_absent_from_builder_and_test
  test_t_c7_c1_sim_does_not_apply_market_blend
```

Local: `PYTHONPATH=. python3 -m pytest tests/test_nfl_w8_eng_prep_contracts_t4688u.py tests/test_nfl_handicapping_framework.py -q` → **21 passed**.

---

## Proposed diffs still under B HOLD

`scripts/nfl/run_w8_research_forecast_t4564u.py` lives on #645, **not** this tip. Do not copy the 1177-line emit onto this branch (slate / nflverse download). Wire after CLEAR:

```diff
# _build_current_strength (today: no week filter; only max<7 exit)
+    df = df[df["week"].astype(int) <= 7]
+    # or raise if any week>7 when refuse_weeks_above_cap

# _injury_impacts :325
-        latest_week[team] = max(designated_weeks) if designated_weeks else int(g["week"].max())
+        latest_week[team] = max(designated_weeks) if designated_weeks else None
+        # if None: skip overlay; still append G3 flags

# _simulate_one :465-468 — do not drop flags when as_of_week==8
+    missing.extend(["w8_official_injury_report", "injury_as_of_week8", "injury_as_of_week8_away"])
+    # always, while official-W8 SoT pin is absent

# _materialize_current_packs :691
-        "w8_official_report": "PRESENT" if latest_week >= WEEK else "MISSING",
+        "w8_official_report": "MISSING",  # PRESENT only if official_sot_pin

# C3 pin before _simulate_one / after _download
+    require_input_sha(parquet_sha, C3_PIN, label="epa")

# C7 test (4875faeb on #645)
-    assert "False" in text
+    # import-graph + market_blend.spread_applied is False (see t4688u tests)
```

Completeness auditor `audit_w8_input_completeness_t4605u.py:270-272` (`PRESENT if inj_week == week`) is the third writer — same HOLD.

---

## Residual Needs CLEAR (full B impl)

1. **Merge / production CLEAR** — this tip is DRAFT only. Framework change is shared-spine; do not ship without Ryan.
2. **Wire #645 emit** to these builders (script + completeness auditor).
3. **Official-W8 SoT** — still none. Do not invent rows.
4. **Landing (b)** DECLARED-UNCERTAINTY — not taken; landing (a) INVARIANT is what landed.
5. **Paid Odds / beat / worker** (WS-D) — out of scope; #650 `9e851852` frozen.
6. **Warehouse SELECT / A1 / CERT / Coming Soon / F2 / holdout** — locked.
7. **Deposit IMV RETURN 75141507** full text (still not in this checkout).
8. **C3 pin re-hash** on the emit tip before enforcing sha refuse against live parquets.

Signed: Cursor t4688u P1 · deepen #653 · CERT=0
END
