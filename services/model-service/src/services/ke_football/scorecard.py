"""Phase 1B component scorecard — PASS / PARTIAL / FAIL / DATA_INSUFFICIENT.

Decisions are football-measurement only. No ATS / ROI / close / CLV.
NO_ADJUSTMENT_WINNER is an acceptable bakeoff call.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


PHASE2_STOP = (
    "STOP before Team Strength / composite weights, scoring integration, "
    "matchup modeling, market comparison, public KE ratings, UI, boards, "
    "and named KE Disruption weighting."
)


def _num(row: Any, *path: str) -> Optional[float]:
    cur: Any = row
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    if cur is None:
        return None
    try:
        return float(cur)
    except (TypeError, ValueError):
        return None


def _curve_at(curve: List[Dict[str, Any]], n: int) -> Optional[float]:
    for row in curve or []:
        if int(row.get("n_prior_games") or 0) == n:
            return row.get("pearson")
    return None


def grade_component(row: Dict[str, Any], *, sport: str) -> Dict[str, Any]:
    cid = row.get("id")
    if row.get("status_hint") == "DATA_INSUFFICIENT":
        return {
            "id": cid,
            "grade": "DATA_INSUFFICIENT",
            "phase2_eligible": False,
            "evidence": [row.get("reason") or "insufficient inputs"],
            "recommendation": "Do not manufacture. Leave OMIT / DATA_INSUFFICIENT.",
        }

    dist = row.get("distribution") or {}
    miss = _num(row, "missingness", "season_missing_rate")
    n_teams = int(dist.get("n_teams") or 0)
    persist = _num(row, "early_late_persistence", "pearson")
    late_w2w = _num(row, "week_to_week", "late_mean_pearson")
    own = _num(row, "oos", "own_unit", "pearson")
    own_n = _num(row, "oos", "own_unit", "n")
    epa_key = "next_def_epa" if row.get("side") == "def" else "next_off_epa"
    epa_oos = _num(row, "oos", epa_key, "pearson")
    incr = _num(row, "incremental_on_epa", "partial_pearson")
    curve4 = _curve_at(row.get("sample_size_curve") or [], 4)
    curve8 = _curve_at(row.get("sample_size_curve") or [], 8)
    family = row.get("family")

    evidence: List[str] = []
    if n_teams:
        evidence.append(f"n_teams={n_teams} mean={dist.get('mean')} sd={dist.get('sd')}")
    if miss is not None:
        evidence.append(f"season_missing_rate={miss:.3f}")
    if persist is not None:
        evidence.append(f"early→late pearson={persist:.3f}")
    if late_w2w is not None:
        evidence.append(f"late week-to-week pearson={late_w2w:.3f}")
    if own is not None:
        evidence.append(f"OOS own-unit pearson={own:.3f} n={own_n}")
    if epa_oos is not None:
        evidence.append(f"OOS {epa_key} pearson={epa_oos:.3f}")
    if incr is not None:
        evidence.append(f"incremental-on-EPA partial r={incr:.3f} (report only)")
    if curve4 is not None:
        evidence.append(f"split-half n=4 pearson={curve4:.3f}")
    if curve8 is not None:
        evidence.append(f"split-half n=8 pearson={curve8:.3f}")

    # Hard DATA_INSUFFICIENT: almost no published values.
    if n_teams < 8 or (miss is not None and miss > 0.80):
        return {
            "id": cid,
            "grade": "DATA_INSUFFICIENT",
            "phase2_eligible": False,
            "evidence": evidence + ["too few published team values"],
            "recommendation": "Do not fill. Keep status DATA_INSUFFICIENT.",
        }

    # Finishing repaired range check (NFL). Phase 1 defect was PPO~2.1 / finish~0.41.
    if family == "finishing" and sport == "nfl" and cid in {"ke.ppo", "ke.finish"}:
        mean = dist.get("mean")
        if cid == "ke.ppo" and mean is not None and mean < 2.8:
            return {
                "id": cid,
                "grade": "FAIL",
                "phase2_eligible": False,
                "evidence": evidence + [f"PPO mean {mean:.2f} still in the kickoff-at-35 defect band (~2.1)"],
                "recommendation": "Do not calibrate around the bad measurement. Repair drive boundaries first.",
            }
        if cid == "ke.finish" and mean is not None and mean < 0.50:
            return {
                "id": cid,
                "grade": "FAIL",
                "phase2_eligible": False,
                "evidence": evidence + [f"finish mean {mean:.2f} still looks like the false-opportunity defect"],
                "recommendation": "Do not shrink toward 0.40. Re-check opportunity yardline exclusions.",
            }

    # Pace seconds: clock coverage is a known CFB hole.
    if cid == "ke.pace_seconds" and miss is not None and miss > 0.20:
        return {
            "id": cid,
            "grade": "DATA_INSUFFICIENT" if miss > 0.50 else "PARTIAL",
            "phase2_eligible": miss <= 0.50,
            "evidence": evidence,
            "recommendation": "Keep plays/game as the pace SoT. Do not impute clock pace.",
        }

    # ST: NFL published but unvalidated as a module; CFB already handled.
    if cid == "ke.st":
        if sport != "nfl":
            return {
                "id": cid,
                "grade": "DATA_INSUFFICIENT",
                "phase2_eligible": False,
                "evidence": evidence,
                "recommendation": "CFB ST stays OMIT.",
            }
        return {
            "id": cid,
            "grade": "PARTIAL",
            "phase2_eligible": True,
            "evidence": evidence + ["NFL ST EPA/play published; no 1.0 hook; module uncertified as a rating"],
            "recommendation": "Eligible as a DERIVED component only. Do not weight into Team Strength this phase.",
        }

    # rz_td is a sibling, not ke.finish.
    if cid == "ke.rz_td":
        return {
            "id": cid,
            "grade": "PARTIAL",
            "phase2_eligible": True,
            "evidence": evidence + ["play-level RZ TD rate; must not be named ke.finish"],
            "recommendation": "Keep as PARTIAL sibling. Do not substitute for drive finishing.",
        }

    # Core EPA / success / expl / finishing / pace decision.
    reliable = (persist is not None and persist >= 0.35) or (curve4 is not None and curve4 >= 0.35)
    oos_ok = (own is not None and own >= 0.20) or (epa_oos is not None and epa_oos >= 0.20)
    # Single-game week-to-week is noisy by construction (especially EPA).
    # Report it; do not veto PASS when split-half / early→late already hold.
    thin_oos = own is not None and own < 0.10 and (epa_oos is None or epa_oos < 0.10)

    if family == "pace":
        if reliable and oos_ok:
            grade = "PASS"
            rec = "Eligible for Phase 2 as a distinct pace component. Do not convert to points."
        else:
            grade = "PARTIAL"
            rec = "Publish plays/game. Competitive/clock variants stay labeled."
        return {
            "id": cid,
            "grade": grade,
            "phase2_eligible": True,
            "evidence": evidence,
            "recommendation": rec,
        }

    if reliable and oos_ok and n_teams >= (20 if sport == "nfl" else 40):
        grade = "PASS"
        rec = "Eligible to enter Phase 2 as an independent DERIVED component. No composite weight yet."
    elif thin_oos and not reliable:
        grade = "PARTIAL"
        rec = "Measurement publishes; predictive persistence is weak. Do not overweight in a later composite."
    else:
        grade = "PARTIAL"
        rec = "Eligible with caveats (sample / early-season / collinearity). Validate again before weighting."

    return {
        "id": cid,
        "grade": grade,
        "phase2_eligible": grade in {"PASS", "PARTIAL"},
        "evidence": evidence,
        "recommendation": rec,
    }


def grade_disruption(inventory: Dict[str, Any], *, sport: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = [
        {
            "id": "ke.havoc",
            "grade": "DATA_INSUFFICIENT",
            "phase2_eligible": False,
            "evidence": [
                "named ke.havoc requires certified TFL ∧ FF ∧ INT",
                f"named_havoc_allowed={inventory.get('named_havoc_allowed')}",
                "weights_assigned=false",
            ],
            "recommendation": "Keep OMIT. Do not invent KE Disruption weights.",
        }
    ]
    events = {e.get("event_id"): e for e in inventory.get("events") or [] if isinstance(e, dict)}
    sparse_cfb = {"interception", "fumble_forced", "tackle_for_loss", "pass_breakup"}
    for eid, spec in events.items():
        audit = spec.get("audit") or {}
        null_rate = audit.get("null_rate")
        present = audit.get("present")
        n_true = audit.get("n_true")
        if sport != "nfl" and eid in sparse_cfb:
            out.append(
                {
                    "id": f"ke.disruption_{eid}",
                    "grade": "DATA_INSUFFICIENT",
                    "phase2_eligible": False,
                    "evidence": [
                        f"present={present} null_rate={null_rate} n_true={n_true}",
                        "event-only / sparse flag — publishing 1.0 on non-null is forbidden",
                    ],
                    "recommendation": "Leave DATA_INSUFFICIENT. Do not substitute fake rates or a havoc bundle.",
                }
            )
            continue
        if not present:
            out.append(
                {
                    "id": f"ke.disruption_{eid}",
                    "grade": "DATA_INSUFFICIENT",
                    "phase2_eligible": False,
                    "evidence": [f"{eid} column absent"],
                    "recommendation": "Do not impute.",
                }
            )
            continue
        if null_rate is not None and float(null_rate) > 0.05:
            out.append(
                {
                    "id": f"ke.disruption_{eid}",
                    "grade": "DATA_INSUFFICIENT",
                    "phase2_eligible": False,
                    "evidence": [f"null_rate={null_rate} > 0.05"],
                    "recommendation": "Do not treat null as false.",
                }
            )
            continue
        out.append(
            {
                "id": f"ke.disruption_{eid}",
                "grade": "PARTIAL",
                "phase2_eligible": True,
                "evidence": [
                    f"present null_rate={null_rate} n_true={n_true}",
                    "inventory-ok, not official-charting certified",
                ],
                "recommendation": "Eligible as a per-event DERIVED rate only. Not named ke.havoc.",
            }
        )
    if sport == "nfl":
        out.append(
            {
                "id": "ke.disruption_proxy_nfl",
                "grade": "PARTIAL",
                "phase2_eligible": True,
                "evidence": ["sack ∨ INT ∨ qb_hit; must_not_be_named ke.havoc"],
                "recommendation": "Keep the proxy ID. Do not promote to named havoc.",
            }
        )
    return out


def grade_adjustment(bakeoff: Dict[str, Any]) -> Dict[str, Any]:
    winner = bakeoff.get("winner") or "NO_ADJUSTMENT_WINNER"
    unadj = ((bakeoff.get("candidates") or {}).get("unadjusted") or {}).get("confirmation") or {}
    loo = ((bakeoff.get("candidates") or {}).get("loo_sos") or {}).get("confirmation") or {}
    evidence = [
        f"winner={winner}",
        f"confirmation unadjusted off MAE={((unadj.get('offense') or {}).get('mae'))}",
        f"confirmation loo_sos off MAE={((loo.get('offense') or {}).get('mae'))}",
        "Phase 1 simple SOS failed to beat unadjusted — preserved",
        "No ATS / close / ROI used",
    ]
    if winner == "NO_ADJUSTMENT_WINNER":
        return {
            "id": "ke.opp_adj_epa",
            "grade": "PARTIAL",
            "phase2_eligible": False,
            "evidence": evidence,
            "recommendation": (
                "NO_ADJUSTMENT_WINNER. Do not promote an opponent adjustment "
                "because it is theoretically desirable. Phase 2 may keep the "
                "PIT SOS research cell as ADJUSTED-not-promoted."
            ),
            "winner": winner,
        }
    return {
        "id": "ke.opp_adj_epa",
        "grade": "PARTIAL",
        "phase2_eligible": True,
        "evidence": evidence,
        "recommendation": (
            f"{winner} beat unadjusted on both sides in the frozen confirmation "
            "window. Still ADJUSTED research — not a Team Strength weight."
        ),
        "winner": winner,
    }


def build_scorecard(
    *,
    sport: str,
    validation: Dict[str, Any],
    inventory: Dict[str, Any],
    bakeoff: Dict[str, Any],
    finishing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    grades = [grade_component(row, sport=sport) for row in validation.get("components") or []]
    grades.extend(grade_disruption(inventory, sport=sport))
    grades.append(grade_adjustment(bakeoff))
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "DATA_INSUFFICIENT": 0}
    eligible = []
    hold = []
    for g in grades:
        counts[g["grade"]] = counts.get(g["grade"], 0) + 1
        if g.get("phase2_eligible"):
            eligible.append(g["id"])
        else:
            hold.append(g["id"])
    return {
        "sport": sport,
        "production_promote": False,
        "forbidden_objectives": ["ats", "close", "roi", "kei", "clv", "market_residual"],
        "counts": counts,
        "grades": grades,
        "phase2_eligible_ids": eligible,
        "phase2_hold_ids": hold,
        "finishing_repair": finishing,
        "bakeoff_winner": bakeoff.get("winner"),
        "stop": PHASE2_STOP,
        "note": (
            "PASS/PARTIAL may enter Phase 2 as independent measurements. "
            "No composite / Team Strength / named havoc in this GO."
        ),
    }
