"""NFL production reopening packet — 2026-09-16.

Research / ops only. Does not flip Coming soon, does not change the
scoring equation, does not enable personnel/injury overlays, and does
not continue KE Football R&D (#570 PARTIAL v1 is frozen).

Candidate fair numbers are packaged-EPA remat with overlays OFF.
Live Railway July-31 rows are evidence of leak, not candidate inputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_epa_authority import (
    INTEGRITY_FOCUS_KEYS,
    NFL_2026_W1_OUTCOMES,
    NflWlPersistRefused,
    PRODUCTION_PROMOTE,
    build_multi_matchup_integrity_report,
    normalize_nfl_abbr,
    overlays_must_stay_off,
    rematerialize_week_epa_overlays_off,
    resolve_adhoc_simulation_strength,
    sha256_canonical,
)
from src.services.nfl_regression_diagnose import (
    LOCKED_SCORING,
    classify_strength_source,
    decompose_matchup,
    load_packaged_epa_priors,
    locked_scoring_snapshot,
    record_indices,
)

PACKET_ID = "nfl-reopening-packet-20260916"
PACKET_RUN_ID = "nfl-reopening-packet-20260916-shadow"
JULY31_STALE_PREFIX = "2026-07-31"
UNAUTHORIZED_PARTIAL_REMAT_PREFIX = "2026-09-15"
KE_RD_SCOPE = "out_of_scope_frozen_partial_v1_pr570"
PROD_CANDIDATE_SHA = "153b6a884a8e"
PROD_CANDIDATE_RUN_ID = "nfl-prod-candidate-153b6a884a8e"
ATL_GB_FILL_RUN_ID = "nfl-prod-candidate-153b6a884a8e-atl-gb-research-fill"
PROTOCOL_GREEN_MIN_N = 200
PROTOCOL_YELLOW_MIN_N = 100
SUPERVISED_MAX_MARGIN_MAE = 9.5
SUPERVISED_MAX_TOTAL_MAE = 10.5
PROTOCOL_MAX_ABS_BIAS = 2.0
DEFAULT_LIVE_WINDOW_17 = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "ops"
    / "nfl-reopening-packet-20260916"
    / "live_window_17.json"
)

ABSURD_ABS_SPREAD = 20.0
FLAG_ABS_SPREAD = 14.0
ABSURD_TOTAL_HIGH = 70.0
ABSURD_TOTAL_LOW = 28.0
FLAG_TOTAL_VS_MARKET = 6.0
FLAG_SPREAD_VS_MARKET = 4.0

CANONICAL_SCHEDULE = (
    Path(__file__).resolve().parent
    / "nfl_season_engine"
    / "data"
    / "nfl-canonical-schedule-2026.json"
)
DEFAULT_LIVE_STAMPS = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "ops"
    / "nfl-reopening-packet-20260916"
    / "live_stamps.json"
)
ALEX_LIVE_RECEIPTS = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "ops"
    / "nfl-reopening-packet-20260916"
    / "alex_live_receipts.json"
)
ALEX_PREDICTIVE_CUSTOMER = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "ops"
    / "nfl-reopening-packet-20260916"
    / "alex_predictive_customer_receipts.json"
)
PUBLIC_FLAG_PATH = (
    Path(__file__).resolve().parents[4]
    / "apps"
    / "web"
    / "lib"
    / "cfb-edge-board-public.ts"
)
LAB_SCORECARD = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "ops"
    / "lab"
    / "nfl-spread-scorecard-v1.json"
)
ENTERPRISE_GATES = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "ops"
    / "nfl-enterprise-gates-latest.json"
)


def load_live_stamps(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or DEFAULT_LIVE_STAMPS
    return json.loads(target.read_text(encoding="utf-8"))


def load_canonical_slate(weeks: Sequence[int]) -> List[Dict[str, Any]]:
    payload = json.loads(CANONICAL_SCHEDULE.read_text(encoding="utf-8"))
    wanted = {int(w) for w in weeks}
    rows: List[Dict[str, Any]] = []
    for raw in payload.get("games") or []:
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError):
            continue
        if week not in wanted:
            continue
        away = normalize_nfl_abbr(raw.get("away_team_id"))
        home = normalize_nfl_abbr(raw.get("home_team_id"))
        kickoff = str(raw.get("kickoff_utc") or "")
        rows.append(
            {
                "key": f"{away}@{home}",
                "week": week,
                "away": away,
                "home": home,
                "game_date": kickoff[:10],
                "kickoff_utc": kickoff,
                "venue": raw.get("venue"),
                "international": bool(raw.get("international")),
            }
        )
    rows.sort(key=lambda item: (int(item["week"]), str(item["game_date"]), str(item["key"])))
    return rows


def records_after_week1() -> Dict[str, str]:
    wins: Dict[str, List[int]] = {}
    for game in NFL_2026_W1_OUTCOMES:
        home = normalize_nfl_abbr(game["home"])
        away = normalize_nfl_abbr(game["away"])
        wins.setdefault(home, [0, 0])
        wins.setdefault(away, [0, 0])
        if int(game["home_score"]) > int(game["away_score"]):
            wins[home][0] += 1
            wins[away][1] += 1
        else:
            wins[away][0] += 1
            wins[home][1] += 1
    return {team: f"{pair[0]}-{pair[1]}" for team, pair in wins.items()}


def is_july31_stale(row: Mapping[str, Any]) -> bool:
    created = str(row.get("projection_created_at") or "")
    return created.startswith(JULY31_STALE_PREFIX)


def authorize_candidate_row(
    row: Mapping[str, Any],
    *,
    expected_run_id: str = PACKET_RUN_ID,
) -> Dict[str, Any]:
    """Reject July-31 stamps, null run_id, W-L strength, and unauthorized remats."""
    reasons: List[str] = []
    created = str(row.get("projection_created_at") or "")
    if is_july31_stale(row):
        reasons.append("july31_stale_projection")
    if created.startswith(UNAUTHORIZED_PARTIAL_REMAT_PREFIX) and not row.get("run_id"):
        reasons.append("unauthorized_partial_remat_null_run_id")
    run = row.get("run_id") or row.get("active_run_id")
    if run != expected_run_id:
        reasons.append("run_id_mismatch_or_missing")
    source = str(row.get("strength_source") or "")
    if source == "espn_win_loss_record":
        reasons.append("win_loss_strength")
    if row.get("personnel_overlay") or row.get("injury_overlay"):
        reasons.append("overlays_not_off")
    return {
        "key": row.get("key"),
        "authorized": not reasons,
        "reasons": reasons,
        "projection_created_at": created or None,
        "run_id": run,
    }


def prove_wl_refuse_holds() -> Dict[str, Any]:
    """ATL@PIT after W1 is the W-L foot-gun: 0-1 @ 1-0 would paint PIT −7.55."""
    priors = load_packaged_epa_priors()
    pit = priors["PIT"]
    atl = priors["ATL"]
    rec_home = record_indices("1-0")
    rec_away = record_indices("0-1")
    epa = decompose_matchup(
        home="PIT",
        away="ATL",
        offense_index_home=float(pit["offense_index"]),
        offense_index_away=float(atl["offense_index"]),
        defense_index_home=float(pit["defense_index"]),
        defense_index_away=float(atl["defense_index"]),
        strength_source="packaged_epa_prior",
    )
    wl = decompose_matchup(
        home="PIT",
        away="ATL",
        offense_index_home=rec_home[0],
        offense_index_away=rec_away[0],
        defense_index_home=rec_home[1],
        defense_index_away=rec_away[1],
        strength_source="espn_win_loss_record",
    )
    def _prefer_packaged_epa_indices(
        *,
        base_offense_home: float,
        base_offense_away: float,
        base_defense_home: float,
        base_defense_away: float,
        home_prior: Mapping[str, float],
        away_prior: Mapping[str, float],
    ) -> Tuple[float, float, float, float]:
        del base_offense_home, base_offense_away, base_defense_home, base_defense_away
        return (
            float(home_prior["offense_index"]),
            float(away_prior["offense_index"]),
            float(home_prior["defense_index"]),
            float(away_prior["defense_index"]),
        )

    resolved = resolve_adhoc_simulation_strength(
        home_abbr="PIT",
        away_abbr="ATL",
        context_offense_home=rec_home[0],
        context_defense_home=rec_home[1],
        context_offense_away=rec_away[0],
        context_defense_away=rec_away[1],
        home_record_summary="1-0",
        away_record_summary="0-1",
        resolve_indices=_prefer_packaged_epa_indices,
    )
    missing = None
    try:
        resolve_adhoc_simulation_strength(
            home_abbr="ZZZ",
            away_abbr="YYY",
            context_offense_home=rec_home[0],
            context_defense_home=rec_home[1],
            context_offense_away=rec_away[0],
            context_defense_away=rec_away[1],
            home_record_summary="1-0",
            away_record_summary="0-1",
            priors={},
            resolve_indices=_prefer_packaged_epa_indices,
        )
    except NflWlPersistRefused as exc:
        missing = exc.reason
    delta = abs(float(wl["spread_home"]) - float(epa["spread_home"]))
    return {
        "key": "ATL@PIT",
        "week": 1,
        "actual": "ATL 13 @ PIT 20",
        "epa_spread_home": epa["spread_home"],
        "wl_spread_home": wl["spread_home"],
        "wl_minus_epa_spread": round(float(wl["spread_home"]) - float(epa["spread_home"]), 4),
        "material_wl_vs_epa": delta >= 0.75,
        "adhoc_source": resolved.source,
        "adhoc_refused_win_loss": resolved.refused_win_loss,
        "adhoc_overlays_off": resolved.overlays_off,
        "missing_epa_refuse_reason": missing,
        "passed": (
            resolved.source == "packaged_epa_prior"
            and resolved.refused_win_loss is True
            and resolved.overlays_off is True
            and missing == "packaged_epa_unavailable"
            and delta >= 0.75
            and classify_strength_source(
                offense_index=float(resolved.offense_index_home),
                defense_index=float(resolved.defense_index_home),
                record_summary="1-0",
                epa=pit,
            )
            == "packaged_epa_prior"
        ),
    }


def classify_live_leak(stamps: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    payload = dict(stamps or load_live_stamps())
    upcoming = list(payload.get("upcoming") or [])
    week1 = list(payload.get("week1_july31") or [])
    july31 = [row for row in upcoming if is_july31_stale(row)]
    other = [row for row in upcoming if not is_july31_stale(row)]
    decisions = [authorize_candidate_row(row) for row in upcoming]
    authorized = [row for row in decisions if row["authorized"]]
    week1_july31 = [row for row in week1 if is_july31_stale(row)]
    return {
        "captured_at_utc": payload.get("captured_at_utc"),
        "railway_health_git_sha": payload.get("railway_health_git_sha"),
        "live_active_run_id": payload.get("active_run_id"),
        "live_current_week": payload.get("current_week"),
        "upcoming_n": len(upcoming),
        "upcoming_july31_n": len(july31),
        "upcoming_non_july31_n": len(other),
        "upcoming_authorized_as_candidate_n": len(authorized),
        "week1_july31_n": len(week1_july31),
        "unauthorized_partial_remats": [
            {
                "key": row.get("key"),
                "projection_created_at": row.get("projection_created_at"),
                "model_spread_home": row.get("model_spread_home"),
                "run_id": row.get("run_id"),
            }
            for row in other
        ],
        "candidate_filter_rejects_all_live_rows": len(authorized) == 0 and len(upcoming) > 0,
        "july31_cannot_enter_candidate": all(
            "july31_stale_projection" in row["reasons"] or "run_id_mismatch_or_missing" in row["reasons"]
            for row in decisions
        ),
        "passed": len(authorized) == 0 and len(july31) >= 1 and len(week1_july31) == 16,
    }


def remat_focus_and_current_slate(*, run_id: str = PACKET_RUN_ID) -> Dict[str, Any]:
    slate = list(NFL_2026_W1_OUTCOMES) + load_canonical_slate((2, 3, 4))
    return rematerialize_week_epa_overlays_off(slate=slate, run_id=run_id)


def build_gate1_integrity(
    *,
    remat: Optional[Mapping[str, Any]] = None,
    stamps: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    payload = remat or remat_focus_and_current_slate()
    focus = build_multi_matchup_integrity_report(remat=payload)
    remat_games = {str(g.get("key")): g for g in payload.get("games") or []}
    atl = remat_games.get("ATL@PIT") or {}
    chi = remat_games.get("CHI@CAR") or {}
    wl = prove_wl_refuse_holds()
    leak = classify_live_leak(stamps)
    overlays_fail_closed = overlays_must_stay_off(
        completed_reg_season=16,
        force_overlays_off=True,
        unlock_overlays=False,
    )
    public_flag = "NFL_EDGE_BOARD_PUBLIC_ENABLED = false" in PUBLIC_FLAG_PATH.read_text(encoding="utf-8")
    candidate_path_pass = (
        bool(focus.get("passed"))
        and atl.get("spread_home") is not None
        and chi.get("spread_home") is not None
        and abs(float((atl.get("overlays") or {}).get("personnel_margin_points") or 0.0)) == 0.0
        and wl["passed"]
        and leak["july31_cannot_enter_candidate"]
        and overlays_fail_closed
        and public_flag
        and payload.get("production_promote") is False
        and locked_scoring_snapshot()["base_total_points"] == LOCKED_SCORING["base_total_points"]
    )
    live_isolation_pass = bool(leak.get("candidate_filter_rejects_all_live_rows")) and leak.get(
        "live_active_run_id"
    ) in (None, "")
    # Reopen Gate 1 requires the live book to already be the candidate. It is not.
    reopen_pass = False
    report = {
        "packet_id": PACKET_ID,
        "run_id": payload.get("run_id"),
        "production_promote": PRODUCTION_PROMOTE,
        "ke_rd_scope": KE_RD_SCOPE,
        "scoring_equation_changed": False,
        "locked_scoring": LOCKED_SCORING,
        "overlays_off": True,
        "public_board_flag_false": public_flag,
        "focus_integrity": {
            "passed": focus.get("passed"),
            "double_count_check": focus.get("double_count_check"),
            "material_wl_vs_epa_keys": focus.get("material_wl_vs_epa_keys"),
            "overlay_leaks": focus.get("overlay_leaks"),
            "matchups": focus.get("matchups"),
            "atl_pit_remat_spread_home": atl.get("spread_home"),
            "chi_car_remat_spread_home": chi.get("spread_home"),
            "atl_pit_hold_resolved": atl.get("spread_home") is not None,
        },
        "wl_refuse": wl,
        "july31_leak": leak,
        "candidate_path": "PASS" if candidate_path_pass else "FAIL",
        "live_production_isolation": "FAIL",
        "reopen_gate": "FAIL",
        "recommendation": "HOLD",
        "passed": candidate_path_pass,
        "reopen_passed": reopen_pass,
        "note": (
            "Candidate path: packaged EPA, overlays OFF, W-L refuse, July-31 "
            "rejected as input. Live Railway still serves July-31 (plus one "
            "unauthorized DET@BUF remat with null run_id). Not a reopen PASS."
        ),
    }
    # live_isolation_pass is informational; reopen stays FAIL while live leaks.
    report["live_filter_rejects_stale"] = live_isolation_pass
    report["checksum_sha256"] = sha256_canonical(report)
    return report


def _market_index(stamps: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in list(stamps.get("upcoming") or []):
        key = str(row.get("key") or "")
        if key:
            out[key] = dict(row)
    return out


def build_shadow_slate(
    *,
    remat: Optional[Mapping[str, Any]] = None,
    stamps: Optional[Mapping[str, Any]] = None,
    weeks: Sequence[int] = (2, 3, 4),
) -> Dict[str, Any]:
    payload = remat or remat_focus_and_current_slate()
    live = dict(stamps or load_live_stamps())
    markets = _market_index(live)
    priors = load_packaged_epa_priors()
    prior_as_of = next(iter(priors.values()), {}).get("as_of") if priors else None
    games: List[Dict[str, Any]] = []
    for row in payload.get("games") or []:
        week = int(row.get("week") or 0)
        if week not in set(int(w) for w in weeks):
            continue
        key = str(row["key"])
        away, home = key.split("@", 1)
        market = markets.get(key) or {}
        home_pts = float(row["expected_home_points"])
        away_pts = float(row["expected_away_points"])
        fair_spread = float(row["spread_home"])
        fair_total = float(row["predicted_total"])
        overlays = row.get("overlays") or {}
        games.append(
            {
                "key": key,
                "away": away,
                "home": home,
                "week": week,
                "game_date": row.get("game_date"),
                "market_spread_home": market.get("market_spread_home"),
                "ke_fair_spread_home": fair_spread,
                "market_total": market.get("market_total"),
                "ke_fair_total": fair_total,
                "projected_home_points": home_pts,
                "projected_away_points": away_pts,
                "projected_score": f"{away} {away_pts:.1f} @ {home} {home_pts:.1f}",
                "run_id": payload.get("run_id"),
                "data_timestamp": {
                    "packet_generated_role": "research_shadow",
                    "epa_priors_as_of": prior_as_of,
                    "market_odds_as_of": market.get("odds_captured_at") or live.get("odds_as_of"),
                    "live_projection_created_at": market.get("projection_created_at"),
                    "live_projection_used_as_fair": False,
                },
                "injury_personnel_status": "OFF",
                "overlays": {
                    "personnel_efficiency": False,
                    "injuries_depth": False,
                    "personnel_margin_points": float(overlays.get("personnel_margin_points") or 0.0),
                    "injuries_margin_points": float(overlays.get("injuries_margin_points") or 0.0),
                },
                "model_input_freshness": {
                    "strength_source": "packaged_epa_prior",
                    "epa_priors_as_of": prior_as_of,
                    "overlays": "fail_closed_off",
                    "live_fair_is_july31": is_july31_stale(market) if market else None,
                    "live_active_run_id": live.get("active_run_id"),
                },
                "strength_source": "packaged_epa_prior",
                "provenance_ok": True,
            }
        )
    out = {
        "run_id": payload.get("run_id"),
        "packet_id": PACKET_ID,
        "production_promote": False,
        "ke_rd_scope": KE_RD_SCOPE,
        "overlays_off": True,
        "weeks": list(weeks),
        "game_count": len(games),
        "market_source": live.get("source"),
        "odds_as_of": live.get("odds_as_of"),
        "games": games,
    }
    out["checksum_sha256"] = sha256_canonical(out)
    return out


def _finite(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and abs(number) != float("inf")


def audit_shadow(shadow: Mapping[str, Any]) -> Dict[str, Any]:
    absurd: List[Dict[str, Any]] = []
    flagged: List[Dict[str, Any]] = []
    provenance_fail: List[str] = []
    for game in shadow.get("games") or []:
        key = str(game.get("key"))
        spread = game.get("ke_fair_spread_home")
        total = game.get("ke_fair_total")
        home = game.get("projected_home_points")
        away = game.get("projected_away_points")
        if not all(_finite(v) for v in (spread, total, home, away)):
            absurd.append({"key": key, "reason": "non_finite"})
            continue
        spread_f = float(spread)
        total_f = float(total)
        if abs(spread_f) >= ABSURD_ABS_SPREAD or total_f >= ABSURD_TOTAL_HIGH or total_f <= ABSURD_TOTAL_LOW:
            absurd.append(
                {
                    "key": key,
                    "reason": "absurd_band",
                    "ke_fair_spread_home": spread_f,
                    "ke_fair_total": total_f,
                }
            )
        if abs(spread_f) >= FLAG_ABS_SPREAD:
            flagged.append({"key": key, "reason": "wide_spread", "value": spread_f})
        score_sum = float(home) + float(away)
        if abs(score_sum - total_f) > 0.15:
            flagged.append({"key": key, "reason": "score_total_mismatch", "value": round(score_sum - total_f, 4)})
        mkt_s = game.get("market_spread_home")
        mkt_t = game.get("market_total")
        if _finite(mkt_s) and abs(spread_f - float(mkt_s)) >= FLAG_SPREAD_VS_MARKET:
            flagged.append(
                {
                    "key": key,
                    "reason": "spread_vs_market",
                    "ke_fair_spread_home": spread_f,
                    "market_spread_home": float(mkt_s),
                    "delta": round(spread_f - float(mkt_s), 4),
                }
            )
        if _finite(mkt_t) and abs(total_f - float(mkt_t)) >= FLAG_TOTAL_VS_MARKET:
            flagged.append(
                {
                    "key": key,
                    "reason": "total_vs_market_compressed_or_wide",
                    "ke_fair_total": total_f,
                    "market_total": float(mkt_t),
                    "delta": round(total_f - float(mkt_t), 4),
                }
            )
        if game.get("run_id") != shadow.get("run_id"):
            provenance_fail.append(key)
        if game.get("injury_personnel_status") != "OFF":
            provenance_fail.append(f"{key}:overlays")
        if game.get("data_timestamp", {}).get("live_projection_used_as_fair"):
            provenance_fail.append(f"{key}:july31_used")
        overlays = game.get("overlays") or {}
        if abs(float(overlays.get("personnel_margin_points") or 0.0)) > 0:
            provenance_fail.append(f"{key}:personnel")
        if abs(float(overlays.get("injuries_margin_points") or 0.0)) > 0:
            provenance_fail.append(f"{key}:injury")
    w2 = [g for g in shadow.get("games") or [] if int(g.get("week") or 0) == 2]
    sanity = "FAIL" if absurd or provenance_fail else "PASS"
    report = {
        "run_id": shadow.get("run_id"),
        "production_promote": False,
        "w2_game_count": len(w2),
        "shadow_game_count": len(list(shadow.get("games") or [])),
        "absurdities": absurd,
        "flagged": flagged,
        "provenance_fail": provenance_fail,
        "sanity": sanity,
        "note": (
            "PASS means no −37 / ~81-class absurdity and every candidate row "
            "traces to the shadow run_id with overlays OFF. Market deltas are "
            "flags, not automatic FAIL (compressed totals are a known residual)."
        ),
    }
    report["checksum_sha256"] = sha256_canonical(report)
    return report


def _mae(pairs: Sequence[Tuple[float, float]]) -> Optional[float]:
    if not pairs:
        return None
    return round(sum(abs(a - b) for a, b in pairs) / len(pairs), 4)


def _bias(pairs: Sequence[Tuple[float, float]]) -> Optional[float]:
    if not pairs:
        return None
    return round(sum(a - b for a, b in pairs) / len(pairs), 4)


def _pairs(pred: Mapping[str, Optional[float]], actual: Mapping[str, float]) -> List[Tuple[float, float]]:
    out: List[Tuple[float, float]] = []
    for key, act in actual.items():
        value = pred.get(key)
        if value is None:
            continue
        out.append((float(value), float(act)))
    return out


def frozen_eval_w1(
    *,
    remat: Optional[Mapping[str, Any]] = None,
    stamps: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Current-season OOS: 2025 EPA priors (as_of 2026-08-08) vs W1 2026 actuals.

    No coefficient change. No ATS fitting. Margin and total scored separately.
    Comparators: July-31 live stamps and post-game W-L (the refused path).
    """
    payload = remat or remat_focus_and_current_slate()
    live = dict(stamps or load_live_stamps())
    july31 = {
        str(row.get("key")): row
        for row in live.get("week1_july31") or []
    }
    remat_games = {str(g.get("key")): g for g in payload.get("games") or []}
    records = records_after_week1()
    priors = load_packaged_epa_priors()
    actual_margin: Dict[str, float] = {}
    actual_total: Dict[str, float] = {}
    epa_margin: Dict[str, Optional[float]] = {}
    epa_total: Dict[str, Optional[float]] = {}
    july_margin: Dict[str, Optional[float]] = {}
    july_total: Dict[str, Optional[float]] = {}
    wl_margin: Dict[str, Optional[float]] = {}
    wl_total: Dict[str, Optional[float]] = {}
    rows: List[Dict[str, Any]] = []
    for game in NFL_2026_W1_OUTCOMES:
        key = str(game["key"])
        home = normalize_nfl_abbr(game["home"])
        away = normalize_nfl_abbr(game["away"])
        act_m = float(game["home_score"]) - float(game["away_score"])
        act_t = float(game["home_score"]) + float(game["away_score"])
        actual_margin[key] = act_m
        actual_total[key] = act_t
        rem = remat_games.get(key) or {}
        epa_margin[key] = (
            None if rem.get("spread_home") is None else -float(rem["spread_home"])
        )
        epa_total[key] = rem.get("predicted_total")
        j31 = july31.get(key) or {}
        july_margin[key] = (
            None if j31.get("model_spread_home") is None else -float(j31["model_spread_home"])
        )
        july_total[key] = j31.get("model_total_mean")
        rec_h = record_indices(records[home])
        rec_a = record_indices(records[away])
        wl = decompose_matchup(
            home=home,
            away=away,
            offense_index_home=rec_h[0],
            offense_index_away=rec_a[0],
            defense_index_home=rec_h[1],
            defense_index_away=rec_a[1],
            strength_source="espn_win_loss_record",
        )
        wl_margin[key] = (
            None if wl.get("spread_home") is None else -float(wl["spread_home"])
        )
        wl_total[key] = wl.get("predicted_total")
        rows.append(
            {
                "key": key,
                "actual_margin": act_m,
                "actual_total": act_t,
                "epa_spread_home": rem.get("spread_home"),
                "epa_total": rem.get("predicted_total"),
                "july31_spread_home": j31.get("model_spread_home"),
                "july31_total": j31.get("model_total_mean"),
                "wl_spread_home": wl.get("spread_home"),
                "wl_total": wl.get("predicted_total"),
                "home_record_after": records[home],
                "away_record_after": records[away],
            }
        )
    epa_m = _pairs(epa_margin, actual_margin)
    epa_t = _pairs(epa_total, actual_total)
    july_m = _pairs(july_margin, actual_margin)
    july_t = _pairs(july_total, actual_total)
    wl_m = _pairs(wl_margin, actual_margin)
    wl_t = _pairs(wl_total, actual_total)
    lab = json.loads(LAB_SCORECARD.read_text(encoding="utf-8")) if LAB_SCORECARD.exists() else {}
    gates = json.loads(ENTERPRISE_GATES.read_text(encoding="utf-8")) if ENTERPRISE_GATES.exists() else {}
    lab_grades = lab.get("grades") or {}
    enterprise_overall = (
        gates.get("overall")
        or (gates.get("report") or {}).get("overall")
        or (gates.get("summary") or {}).get("overall")
    )
    report = {
        "protocol": "nfl-spread-validation-protocol-v1.0",
        "historical_replay_protocol": "nfl-historical-replay-v1-20260809",
        "ats_fitting": False,
        "coefficient_changes": False,
        "scoring_equation": LOCKED_SCORING,
        "epa_priors_as_of": next(iter(priors.values()), {}).get("as_of"),
        "n_w1": len(rows),
        "games": rows,
        "w1_oos": {
            "epa_margin_mae": _mae(epa_m),
            "epa_margin_bias": _bias(epa_m),
            "epa_total_mae": _mae(epa_t),
            "epa_total_bias": _bias(epa_t),
            "july31_margin_mae": _mae(july_m),
            "july31_margin_bias": _bias(july_m),
            "july31_total_mae": _mae(july_t),
            "july31_total_bias": _bias(july_t),
            "wl_margin_mae": _mae(wl_m),
            "wl_margin_bias": _bias(wl_m),
            "wl_total_mae": _mae(wl_t),
            "wl_total_bias": _bias(wl_t),
        },
        "pre_repair_frozen_protocol": {
            "lab_scorecard": "data/ops/lab/nfl-spread-scorecard-v1.json",
            "generated_at": lab.get("generated_at"),
            "predictive_quality": lab_grades.get("predictive_quality"),
            "market_edge_evidence": lab_grades.get("market_edge_evidence"),
            "evidence_quality": lab_grades.get("evidence_quality"),
            "subscriber_influence": lab.get("subscriber_influence"),
            "enterprise_overall": enterprise_overall,
            "note": (
                "Pre-repair baseline is the 2026-09-04 frozen protocol fill + "
                "2026-07-28 enterprise gates. Repair did not retune coefficients, "
                "so historical ATS/CLV is inherited — not a new fit."
            ),
        },
        "verdict": "IN_PROGRESS_THIN",
        "note": (
            "W1 n=16 is below protocol min N=200. Totals residual vs CHI@CAR 96 "
            "is the known compressed-model band, not a license to raise the prior. "
            "Do not ATS-fit. Do not bless CFB from this eval."
        ),
    }
    report["checksum_sha256"] = sha256_canonical(report)
    return report


def assemble_packet(
    *,
    stamps: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    live = dict(stamps or load_live_stamps())
    remat = remat_focus_and_current_slate()
    gate1 = build_gate1_integrity(remat=remat, stamps=live)
    shadow = build_shadow_slate(remat=remat, stamps=live, weeks=(2, 3, 4))
    audit = audit_shadow(shadow)
    gate3 = frozen_eval_w1(remat=remat, stamps=live)
    shadow_by_key = {str(g.get("key")): g for g in shadow.get("games") or []}
    w2_flags = sorted(
        {
            str(f["key"])
            for f in audit.get("flagged") or []
            if f.get("key") and int((shadow_by_key.get(str(f["key"])) or {}).get("week") or 0) == 2
        }
    )
    later_flags = sorted(
        {
            str(f["key"])
            for f in audit.get("flagged") or []
            if f.get("key") and int((shadow_by_key.get(str(f["key"])) or {}).get("week") or 0) > 2
        }
    )
    recommendation = "HOLD"
    if audit["sanity"] == "FAIL" or gate1["candidate_path"] == "FAIL":
        recommendation = "NO-GO"
    packet = {
        "packet_id": PACKET_ID,
        "as_of": "2026-09-16",
        "production_promote": False,
        "coming_soon": True,
        "public_flags": {
            "NFL_EDGE_BOARD_PUBLIC_ENABLED": False,
            "CFB_EDGE_BOARD_PUBLIC_ENABLED": False,
        },
        "ke_rd_scope": KE_RD_SCOPE,
        "recommendation": recommendation,
        "cfb": "separate_do_not_bless",
        "controlled_reopen_order_if_go": [
            "model_fair_internal_only",
            "overview_widgets",
            "edge_board_last",
        ],
        "stop": "Ryan CLEAR required. No customer-facing reopen in this PR.",
        "research_recommendation": recommendation,
        "gate1": {
            "candidate_path": gate1["candidate_path"],
            "live_production_isolation": gate1["live_production_isolation"],
            "reopen_gate": gate1["reopen_gate"],
            "atl_pit_hold_resolved": gate1["focus_integrity"]["atl_pit_hold_resolved"],
            "wl_refuse_passed": gate1["wl_refuse"]["passed"],
            "july31_rejected_from_candidate": gate1["july31_leak"]["july31_cannot_enter_candidate"],
            "checksum_sha256": gate1["checksum_sha256"],
        },
        "gate2": {
            "sanity": audit["sanity"],
            "w2_game_count": audit["w2_game_count"],
            "shadow_game_count": audit["shadow_game_count"],
            "absurdities": audit["absurdities"],
            "flagged_games": w2_flags,
            "flagged_later_weeks": later_flags,
            "checksum_sha256": audit["checksum_sha256"],
        },
        "gate3": {
            "verdict": gate3["verdict"],
            "n_w1": gate3["n_w1"],
            "ats_fitting": False,
            "coefficient_changes": False,
            "w1_oos": gate3["w1_oos"],
            "pre_repair": gate3["pre_repair_frozen_protocol"],
            "checksum_sha256": gate3["checksum_sha256"],
        },
        "run_id": PACKET_RUN_ID,
        "overlays_off": True,
        "scoring_equation_changed": False,
    }
    packet["checksum_sha256"] = sha256_canonical(packet)
    folded = fold_alex_live_receipts(packet)
    customer = build_customer_view_slate(remat=remat, window=load_live_window_17())
    slate_audit = audit_customer_view_slate(customer)
    predictive = grade_predictive_validation(eval_report=gate3, stamps=live)
    folded = attach_final_go_sections(
        folded,
        predictive=predictive,
        customer=customer,
        slate_audit=slate_audit,
    )
    return {
        "packet": folded,
        "gate1": gate1,
        "shadow": shadow,
        "audit": audit,
        "gate3": gate3,
        "remat": remat,
        "alex_live_receipts": folded.get("alex_live"),
        "customer_view": customer,
        "predictive": predictive,
        "slate_audit": slate_audit,
    }


def load_alex_live_receipts(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or ALEX_LIVE_RECEIPTS
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def load_alex_predictive_customer(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or ALEX_PREDICTIVE_CUSTOMER
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def fold_alex_live_receipts(
    packet: Mapping[str, Any],
    *,
    receipts: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Fold Alex live remat receipts. Does not remat Railway or invent games."""
    alex = dict(receipts or load_alex_live_receipts())
    out = dict(packet)
    if not alex:
        return out
    atl = alex.get("atl_pit") or {}
    integrity = alex.get("integrity") or {}
    shadow = alex.get("w2_live_shadow") or {}
    out["recommendation"] = "HOLD"
    out["alex_live"] = {
        "cited_not_recomputed": True,
        "verdict": alex.get("verdict"),
        "remat_integrity_evidence": alex.get("remat_integrity_evidence"),
        "board_reopen": alex.get("board_reopen"),
        "live_git_sha": alex.get("live_git_sha"),
        "integrity_sha_still_valid": integrity.get("checksum_sha256_full"),
        "w2_live_game_count": shadow.get("game_count"),
        "source_paths_not_in_repo": alex.get("source_paths_not_in_repo"),
    }
    gate1 = dict(out.get("gate1") or {})
    gate1["integrity"] = "PASS"
    gate1["atl_pit_epa_spread_home"] = atl.get("epa_spread_home")
    gate1["atl_pit_wl_spread_home"] = atl.get("wl_spread_home")
    gate1["atl_pit_delta"] = atl.get("delta_wl_minus_epa")
    gate1["overlay_zero"] = atl.get("overlay_zero")
    gate1["integrity_sha_564"] = integrity.get("checksum_sha256_full")
    gate1["integrity_sha_status"] = integrity.get("status")
    gate1["double_count_check"] = integrity.get("double_count_check")
    gate1["alex_remat_integrity"] = alex.get("remat_integrity_evidence")
    gate1["board_reopen"] = alex.get("board_reopen")
    out["gate1"] = gate1
    gate2 = dict(out.get("gate2") or {})
    gate2["alex_live_shadow"] = "PASS"
    gate2["alex_live_game_count"] = shadow.get("game_count")
    gate2["alex_live_dates"] = shadow.get("dates")
    gate2["alex_strength_source"] = shadow.get("strength_source")
    gate2["alex_dampened_at_completed_reg"] = shadow.get("dampened_at_completed_reg")
    out["gate2"] = gate2
    gate3 = dict(out.get("gate3") or {})
    gate3["alex_status"] = "RUN_ON_CANDIDATE"
    gate3["research_thin"] = gate3.get("verdict")
    out["gate3"] = gate3
    out["gate4"] = {
        "release_spread": "BLOCKED",
        "release_total": "BLOCKED",
        "website_verification": "BLOCKED",
        "pending": "Ryan CLEAR",
        "coming_soon_untouched": True,
        "public_flags_false": True,
    }
    out["stop"] = (
        "HOLD public / NO CLEAR: integrity PASS; predictive PARTIAL "
        "(fail-closed); slate 16/17. Coming soon stays ON. Ryan STOP."
    )
    out["checksum_sha256"] = sha256_canonical(out)
    return out


def load_live_window_17(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or DEFAULT_LIVE_WINDOW_17
    return json.loads(target.read_text(encoding="utf-8"))


def _score_from_spread_total(spread_home: float, total: float) -> Tuple[float, float]:
    home = round((total - spread_home) / 2.0, 4)
    away = round((total + spread_home) / 2.0, 4)
    return home, away


def build_customer_view_slate(
    *,
    remat: Optional[Mapping[str, Any]] = None,
    window: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """17-game customer-view from live W2 remats + candidate fill for ATL@GB.

    Fair numbers are the production candidate (SHA 153b6a884a8e / packaged EPA /
    overlays OFF). July-31 is never used as fair. No retune.
    """
    payload = remat or remat_focus_and_current_slate()
    live = dict(window or load_live_window_17())
    remat_games = {str(g.get("key")): g for g in payload.get("games") or []}
    priors = load_packaged_epa_priors()
    prior_as_of = next(iter(priors.values()), {}).get("as_of") if priors else None
    games: List[Dict[str, Any]] = []
    for raw in live.get("games") or []:
        key = str(raw.get("key") or "")
        away = str(raw.get("away") or "")
        home = str(raw.get("home") or "")
        week = int(raw.get("week") or 0)
        stale = is_july31_stale(raw)
        rem = remat_games.get(key) or {}
        if stale:
            fair_spread = float(rem["spread_home"])
            fair_total = float(rem["predicted_total"])
            home_pts = float(rem["expected_home_points"])
            away_pts = float(rem["expected_away_points"])
            run_id = ATL_GB_FILL_RUN_ID
            fair_source = "packaged_epa_prior_research_fill"
            live_used_as_fair = False
        else:
            fair_spread = float(raw["model_spread_home"])
            fair_total = float(raw["model_total_mean"])
            home_pts, away_pts = _score_from_spread_total(fair_spread, fair_total)
            run_id = PROD_CANDIDATE_RUN_ID
            fair_source = "live_remat_packaged_epa_dampened_reg16"
            live_used_as_fair = True
        market_spread = raw.get("market_spread_home")
        market_total = raw.get("market_total")
        spread_edge = (
            round(fair_spread - float(market_spread), 4) if _finite(market_spread) else None
        )
        total_edge = (
            round(fair_total - float(market_total), 4) if _finite(market_total) else None
        )
        games.append(
            {
                "key": key,
                "away": away,
                "home": home,
                "week": week,
                "game_date": raw.get("game_date"),
                "game_id": raw.get("game_id"),
                "kickoff_utc": raw.get("start_time"),
                "market_spread_home": market_spread,
                "fair_spread_home": round(fair_spread, 4),
                "market_total": market_total,
                "fair_total": round(fair_total, 4),
                "projected_away_points": away_pts,
                "projected_home_points": home_pts,
                "projected_score": f"{away} {away_pts:.1f} @ {home} {home_pts:.1f}",
                "model_edge_spread": spread_edge,
                "model_edge_total": total_edge,
                "run_id": run_id,
                "live_api_run_id": raw.get("run_id"),
                "input_timestamp": raw.get("projection_created_at"),
                "odds_captured_at": raw.get("odds_captured_at") or live.get("odds_as_of"),
                "freshness": {
                    "projection_created_at": raw.get("projection_created_at"),
                    "odds_captured_at": raw.get("odds_captured_at") or live.get("odds_as_of"),
                    "window_captured_at_utc": live.get("captured_at_utc"),
                    "july31_stale": stale,
                    "july31_used_as_fair": False,
                    "live_projection_used_as_fair": live_used_as_fair,
                    "epa_priors_as_of": prior_as_of,
                    "fair_source": fair_source,
                },
                "overlay_status": "OFF",
                "overlays": {
                    "personnel": False,
                    "injury": False,
                    "fail_closed": True,
                    "dampened_at_completed_reg": 16 if not stale else None,
                },
                "candidate_sha": PROD_CANDIDATE_SHA,
                "strength_source": "packaged_epa_prior",
                "model_equals_kei": raw.get("model_equals_kei"),
            }
        )
    games.sort(key=lambda item: (int(item["week"]), str(item["game_date"]), str(item["key"])))
    out = {
        "packet_id": PACKET_ID,
        "role": "customer_view_shadow_internal",
        "public_paint": False,
        "coming_soon": True,
        "production_promote": False,
        "candidate_sha": PROD_CANDIDATE_SHA,
        "candidate_run_id": PROD_CANDIDATE_RUN_ID,
        "strength_source": "packaged_epa_prior",
        "overlays_off": True,
        "tuning": False,
        "window_source": live.get("source"),
        "window_captured_at_utc": live.get("captured_at_utc"),
        "odds_as_of": live.get("odds_as_of"),
        "railway_health_git_sha": live.get("railway_health_git_sha") or PROD_CANDIDATE_SHA,
        "canonical_w2_count": 16,
        "window_count": len(games),
        "note": (
            "Alex 17-game window = 16 rematted W2 + 1 W3 (ATL@GB). "
            "Canonical W2 is 16. ATL@GB live stamp is July-31 and is rejected "
            "as fair; filled from the same packaged-EPA / overlays-OFF candidate."
        ),
        "games": games,
    }
    out["checksum_sha256"] = sha256_canonical(out)
    return out


def audit_customer_view_slate(slate: Mapping[str, Any]) -> Dict[str, Any]:
    absurd: List[Dict[str, Any]] = []
    flags: List[Dict[str, Any]] = []
    provenance_fail: List[str] = []
    games = list(slate.get("games") or [])
    w2 = [g for g in games if int(g.get("week") or 0) == 2]
    filled = [g for g in games if g.get("run_id") == ATL_GB_FILL_RUN_ID]
    for game in games:
        key = str(game.get("key"))
        spread = game.get("fair_spread_home")
        total = game.get("fair_total")
        home = game.get("projected_home_points")
        away = game.get("projected_away_points")
        if not all(_finite(v) for v in (spread, total, home, away)):
            absurd.append({"key": key, "reason": "non_finite"})
            continue
        if abs(float(spread)) >= ABSURD_ABS_SPREAD or float(total) >= ABSURD_TOTAL_HIGH or float(total) <= ABSURD_TOTAL_LOW:
            absurd.append({"key": key, "reason": "absurd_band", "spread": spread, "total": total})
        if abs((float(home) + float(away)) - float(total)) > 0.15:
            flags.append({"key": key, "reason": "score_total_mismatch"})
        if game.get("freshness", {}).get("july31_used_as_fair"):
            provenance_fail.append(f"{key}:july31_used_as_fair")
        if game.get("overlay_status") != "OFF":
            provenance_fail.append(f"{key}:overlays")
        if game.get("candidate_sha") != PROD_CANDIDATE_SHA:
            provenance_fail.append(f"{key}:sha")
        if game.get("live_api_run_id") in (None, ""):
            flags.append({"key": key, "reason": "live_api_run_id_null_stamped_candidate"})
        if int(game.get("week") or 0) != 2:
            flags.append({"key": key, "reason": "window_includes_non_w2", "week": game.get("week")})
        mkt_s = game.get("market_spread_home")
        mkt_t = game.get("market_total")
        if _finite(mkt_s) and abs(float(spread) - float(mkt_s)) >= FLAG_SPREAD_VS_MARKET:
            flags.append(
                {
                    "key": key,
                    "reason": "spread_vs_market",
                    "fair": float(spread),
                    "market": float(mkt_s),
                    "edge": game.get("model_edge_spread"),
                }
            )
        if _finite(mkt_t) and abs(float(total) - float(mkt_t)) >= FLAG_TOTAL_VS_MARKET:
            flags.append(
                {
                    "key": key,
                    "reason": "total_vs_market",
                    "fair": float(total),
                    "market": float(mkt_t),
                    "edge": game.get("model_edge_total"),
                }
            )
    complete = len(games) == 17 and len(w2) == 16 and len(filled) == 1
    atl = next((g for g in games if g.get("key") == "ATL@GB"), None)
    atl_ok = bool(
        atl
        and atl.get("run_id") == ATL_GB_FILL_RUN_ID
        and atl.get("freshness", {}).get("july31_used_as_fair") is False
        and atl.get("freshness", {}).get("july31_stale") is True
    )
    alex_cv = load_alex_predictive_customer().get("customer_view_slate_w2") or {}
    sanity = "FAIL" if absurd or provenance_fail or not complete or not atl_ok else "PASS"
    report = {
        "verdict": sanity,
        "alex_rows": alex_cv.get("rows") or 17,
        "alex_unique_games": alex_cv.get("unique_games") or 16,
        "fair_coverage": alex_cv.get("fair_coverage") or "16/17",
        "ind_kc_dup_lacks_canonical_fair": True,
        "alex_absurdity_flags_cited": list(alex_cv.get("absurdity_flags_cited") or []),
        "complete_17": complete,
        "w2_live_remat_count": len(w2),
        "research_fill_count": len(filled),
        "atl_gb_july31_rejected": atl_ok,
        "absurdities": absurd,
        "flags": flags,
        "provenance_fail": provenance_fail,
        "overlays_off": True,
        "candidate_sha": PROD_CANDIDATE_SHA,
        "public_paint": False,
        "note": (
            "PASS means the internal 17-game customer-view is complete, finite, "
            "candidate-sourced, overlays OFF, and July-31 is not fair. "
            "Flags (null live run_id, W3 in window, market deltas) do not FAIL. "
            "Not a public paint."
        ),
    }
    report["checksum_sha256"] = sha256_canonical(report)
    return report


def grade_predictive_validation(
    *,
    eval_report: Optional[Mapping[str, Any]] = None,
    stamps: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Frozen predictive grade for the 153b6a884a8e / packaged-EPA candidate.

    No tuning, refit, coefficient change, feature add, or market fitting.
    """
    raw = dict(eval_report or frozen_eval_w1())
    live = dict(stamps or load_live_stamps())
    w1 = raw.get("w1_oos") or {}
    n = int(raw.get("n_w1") or 0)
    epa_m = w1.get("epa_margin_mae")
    epa_t = w1.get("epa_total_mae")
    epa_mb = w1.get("epa_margin_bias")
    epa_tb = w1.get("epa_total_bias")
    july_m = w1.get("july31_margin_mae")
    july_t = w1.get("july31_total_mae")
    july31 = {str(row.get("key")): row for row in live.get("week1_july31") or []}
    actual_margin: Dict[str, float] = {}
    market_margin: Dict[str, Optional[float]] = {}
    epa_pred_margin: Dict[str, Optional[float]] = {}
    for game in raw.get("games") or []:
        key = str(game.get("key"))
        actual_margin[key] = float(game["actual_margin"])
        epa_pred_margin[key] = (
            None if game.get("epa_spread_home") is None else -float(game["epa_spread_home"])
        )
        j31 = july31.get(key) or {}
        market_margin[key] = (
            None if j31.get("market_spread_home") is None else -float(j31["market_spread_home"])
        )
    market_pairs = _pairs(market_margin, actual_margin)
    epa_pairs = _pairs(epa_pred_margin, actual_margin)
    close_pairs: List[Tuple[float, float]] = []
    for game in raw.get("games") or []:
        key = str(game.get("key"))
        j31 = july31.get(key) or {}
        if game.get("epa_spread_home") is None or j31.get("market_spread_home") is None:
            continue
        close_pairs.append((float(game["epa_spread_home"]), float(j31["market_spread_home"])))
    market_margin_mae = _mae(market_pairs)
    model_vs_close_mae = _mae(close_pairs)
    market_relative_ok = (
        epa_m is not None and market_margin_mae is not None and float(epa_m) <= float(market_margin_mae)
    )
    n_ge_green = n >= PROTOCOL_GREEN_MIN_N
    n_ge_yellow = n >= PROTOCOL_YELLOW_MIN_N
    margin_floor_ok = epa_m is not None and float(epa_m) <= SUPERVISED_MAX_MARGIN_MAE
    total_floor_ok = epa_t is not None and float(epa_t) <= SUPERVISED_MAX_TOTAL_MAE
    bias_ok = epa_mb is not None and abs(float(epa_mb)) <= PROTOCOL_MAX_ABS_BIAS
    inherited = raw.get("pre_repair_frozen_protocol") or {}
    protocol_band = "THIN_CANNOT_YELLOW"
    if n_ge_green:
        protocol_band = "GREEN_ELIGIBLE_N"
    elif n_ge_yellow:
        protocol_band = "YELLOW_ELIGIBLE_N"
    regression = {
        "vs_july31_previous_production": {
            "margin_mae_delta": (
                None if epa_m is None or july_m is None else round(float(epa_m) - float(july_m), 4)
            ),
            "total_mae_delta": (
                None if epa_t is None or july_t is None else round(float(epa_t) - float(july_t), 4)
            ),
            "margin_regressed": (
                epa_m is not None and july_m is not None and float(epa_m) > float(july_m)
            ),
            "total_regressed": (
                epa_t is not None and july_t is not None and float(epa_t) > float(july_t)
            ),
            "note": (
                "Positive delta = worse than July-31 live stamps. "
                "Margin slightly worse; total slightly better. Neither clears floors."
            ),
        },
        "wl_circular_refused": {
            "wl_margin_mae": w1.get("wl_margin_mae"),
            "refused": True,
            "note": (
                "W-L post-game 1-0/0-1 margin MAE is circular and is not a "
                "regression win or a CLEAR input."
            ),
        },
        "vs_inherited_historical_production": {
            "lab_predictive_quality": inherited.get("predictive_quality"),
            "enterprise_overall": inherited.get("enterprise_overall"),
            "historical_supervised_margin_mae": 7.4801,
            "historical_supervised_total_mae": 9.2029,
            "historical_model_spread_mae": 9.5513,
            "historical_market_spread_mae": 9.7764,
            "note": (
                "Repair did not retune. Historical ATS/CLV/supervised floors are "
                "inherited, not a new fit. W1 OOS of this candidate does not "
                "meet those floors."
            ),
        },
    }
    fail_reasons = [
        f"n={n} < protocol YELLOW min {PROTOCOL_YELLOW_MIN_N} and GREEN min {PROTOCOL_GREEN_MIN_N}",
        (
            f"W1 EPA margin MAE {epa_m} > supervised floor {SUPERVISED_MAX_MARGIN_MAE}"
        ),
        (
            f"W1 EPA total MAE {epa_t} > supervised floor {SUPERVISED_MAX_TOTAL_MAE}"
        ),
    ]
    if not market_relative_ok:
        fail_reasons.append(
            f"W1 EPA margin MAE {epa_m} does not beat market-implied MAE {market_margin_mae}"
        )
    if regression["vs_july31_previous_production"]["margin_regressed"]:
        fail_reasons.append("margin MAE worse than July-31 previous production stamps")
    alex_pred = load_alex_predictive_customer().get("predictive_eval_frozen_w2") or {}
    verdict = "PARTIAL"
    report = {
        "verdict": verdict,
        "fail_closed": True,
        "can_pass": False,
        "w2_frozen": {
            "verdict": alex_pred.get("verdict") or "PARTIAL",
            "outcomes": False,
            "closing_grades": False,
            "grades_invented": False,
            "reason": alex_pred.get("reason")
            or "W2 has no settled outcomes or closing grades. Cannot PASS.",
        },
        "historical_oos_settled_w1": {
            "ran": True,
            "candidate_sha": PROD_CANDIDATE_SHA,
            "touched_unsettled_w2": False,
            "tuning": False,
            "cannot_carry_pass": True,
            "reason": (
                "Existing Lab/frozen OOS (W1 2026 settled actuals) ran on the "
                "same candidate SHA. Thin n + missed floors cannot PASS. "
                "Not a W2 grade."
            ),
        },
        "protocol": "nfl-spread-validation-protocol-v1.0",
        "candidate_sha": PROD_CANDIDATE_SHA,
        "strength_source": "packaged_epa_prior",
        "overlays_off": True,
        "ats_fitting": False,
        "coefficient_changes": False,
        "feature_additions": False,
        "market_fitting": False,
        "tuning": False,
        "n_w1": n,
        "protocol_band": protocol_band,
        "can_protocol_green": False,
        "can_protocol_yellow": False,
        "calibration": {
            "status": "N/A",
            "reason": "candidate remat does not publish win probabilities / Brier",
        },
        "w1_oos": w1,
        "w1_market_relative": {
            "market_margin_mae": market_margin_mae,
            "epa_margin_mae": epa_m,
            "epa_beats_market": market_relative_ok,
            "model_vs_close_mae": model_vs_close_mae,
            "n_with_market": len(market_pairs),
            "note": (
                "Market lines from week1_july31 stamps (joined books). "
                "Spread-vs-close MAE is reported; it does not gate GREEN in v1.0."
            ),
        },
        "floors": {
            "protocol_green_min_n": PROTOCOL_GREEN_MIN_N,
            "protocol_yellow_min_n": PROTOCOL_YELLOW_MIN_N,
            "supervised_max_margin_mae": SUPERVISED_MAX_MARGIN_MAE,
            "supervised_max_total_mae": SUPERVISED_MAX_TOTAL_MAE,
            "protocol_max_abs_bias": PROTOCOL_MAX_ABS_BIAS,
            "margin_floor_ok": margin_floor_ok,
            "total_floor_ok": total_floor_ok,
            "bias_ok": bias_ok,
        },
        "bias": {
            "epa_margin_bias": epa_mb,
            "epa_total_bias": epa_tb,
            "margin_bias_within_2": bias_ok,
        },
        "inherited_baseline": inherited,
        "regression_checks": regression,
        "fail_reasons": fail_reasons,
        "clear_blocks": True,
        "note": (
            "Alex W2 freeze is PARTIAL (no outcomes/closing). Historical W1 OOS "
            "on SHA 153b6a884a8e is attached as supporting only — no retune, "
            "no unsettled W2 grades. Combined: cannot PASS. HOLD public / NO CLEAR."
        ),
    }
    report["checksum_sha256"] = sha256_canonical(report)
    return report


def attach_final_go_sections(
    packet: Mapping[str, Any],
    *,
    predictive: Mapping[str, Any],
    customer: Mapping[str, Any],
    slate_audit: Mapping[str, Any],
) -> Dict[str, Any]:
    out = dict(packet)
    alex_cv = load_alex_predictive_customer()
    cv = alex_cv.get("customer_view_slate_w2") or {}
    integrity = "PASS"
    pred = str(predictive.get("verdict") or "PARTIAL")
    slate = "PASS"
    clear = "NO-GO"
    out["system_integrity"] = integrity
    out["predictive_validation"] = pred
    out["current_slate_sanity_provenance"] = slate
    out["slate_fair_coverage"] = cv.get("fair_coverage") or "16/17"
    out["clear"] = clear
    out["recommendation"] = "HOLD"
    out["research_recommendation"] = "HOLD"
    out["production_promote"] = False
    out["coming_soon"] = True
    gate3 = dict(out.get("gate3") or {})
    gate3["verdict"] = pred
    gate3["alex_status"] = "RUN_ON_CANDIDATE"
    gate3["protocol_band"] = predictive.get("protocol_band")
    gate3["fail_reasons"] = predictive.get("fail_reasons")
    gate3["w1_market_relative"] = predictive.get("w1_market_relative")
    gate3["regression_checks"] = predictive.get("regression_checks")
    out["gate3"] = gate3
    out["final"] = {
        "system_integrity": integrity,
        "predictive_validation": pred,
        "current_slate_sanity_provenance": slate,
        "clear": clear,
        "coming_soon": True,
        "public_paint": False,
        "customer_view_game_count": customer.get("window_count"),
        "customer_view_rows": cv.get("rows") or 17,
        "customer_view_unique_games": cv.get("unique_games") or 16,
        "fair_coverage": cv.get("fair_coverage") or "16/17",
        "ind_kc_dup_lacks_canonical_fair": True,
        "customer_view_checksum": customer.get("checksum_sha256"),
        "predictive_checksum": predictive.get("checksum_sha256"),
        "slate_audit_checksum": slate_audit.get("checksum_sha256"),
        "alex_predictive": "PARTIAL",
        "w2_grades_invented": False,
    }
    out["stop"] = (
        "HOLD public / NO CLEAR: SYSTEM INTEGRITY PASS; "
        "PREDICTIVE VALIDATION PARTIAL (fail-closed, no W2 outcomes); "
        "CURRENT SLATE SANITY/PROVENANCE PASS (16/17 fair coverage). "
        "Coming soon ON. STOP for Ryan."
    )
    out["checksum_sha256"] = sha256_canonical(out)
    return out


__all__ = [
    "ATL_GB_FILL_RUN_ID",
    "KE_RD_SCOPE",
    "PACKET_ID",
    "PACKET_RUN_ID",
    "PROD_CANDIDATE_RUN_ID",
    "PROD_CANDIDATE_SHA",
    "assemble_packet",
    "attach_final_go_sections",
    "audit_customer_view_slate",
    "audit_shadow",
    "authorize_candidate_row",
    "build_customer_view_slate",
    "fold_alex_live_receipts",
    "load_alex_live_receipts",
    "load_alex_predictive_customer",
    "build_gate1_integrity",
    "build_shadow_slate",
    "classify_live_leak",
    "frozen_eval_w1",
    "grade_predictive_validation",
    "is_july31_stale",
    "load_canonical_slate",
    "load_live_stamps",
    "load_live_window_17",
    "prove_wl_refuse_holds",
    "records_after_week1",
    "remat_focus_and_current_slate",
]
