# Reusable components — Q2 Phase B t5009u (DEV_RESEARCH)

**CERT=0 · not production · not a promote**

| Component | Path | Reuse |
|---|---|---|
| Season-firewall CSV loader | `research/q2_phase_b_t5009u/q2pb/data.py` | Stream-filter seasons so EVAL rows are not materialized in phase 1 |
| Score-only extract | `research/q2_phase_b_t5009u/extract_outcomes_score_only.py` | Six-column public finals; rejects trailing/EPA/2024–25 |
| As-of ridge Massey | `research/q2_phase_b_t5009u/q2pb/strength.py` | `margin = h + s_i − s_j`; kickoff < target; prior regressed to mean |
| Leakage assert | `assert_asof_leakage` | Same-kickoff and later games excluded |
| wl_diff as-of | `research/q2_phase_b_t5009u/q2pb/metrics.py` `asof_wl_diff` | Definition frozen; not raw-scored vs margin |
| DEV maps | `ols` / `logistic_mle` | WL_MARGIN, WL_WP, Q2 maps — DEV only |
| Team-season ICC | `icc_oneway` | Replaces design ICC ASSUMPTION 0.02–0.04 |
| Cluster bootstrap | `cluster_bootstrap` | B=10000 seed 4918; ΔMAE + Spearman CI |
| Freeze barrier | `research/q2_phase_b_t5009u/run_q2_phase_b.py` | Hash fit → timestamp → write 0444 **then** maybe EVAL |
| Unit guards | `research/q2_phase_b_t5009u/tests/test_q2pb_guards.py` | Leakage / wl_diff / phase1 firewall |

Not reused / killed: S1 EPA-trail, `trailing_*`, hist index as experiment frame, Stage C.
