"""t4850u EVAL_ONLY — diagnostic W8 IF consume at rating_week=7.

Minimum #667 DRAFT path. Does not ungate E1, W9 emit, publication, Odds, or C10.

Authority: OWNER CLEAR t4850u EVAL_ONLY · Alex coverage d5d6a3aa · CoS ACCEPT 6685d848.

Uses through-W7 DATA_PARTIAL_ACCEPT c674da77 (panel 340a06dd). Preserves
DATA_PARTIAL. TNF CAR@GB cannot enter ratings. W9 operational caller path
is untouched and still fail-closes on through-W8 DATA ACCEPT.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo

from src.services.nfl_offline_if_caller import (
    ASOF_BOUNDARY_SHA8,
    ASOF_MODULE_SHA256,
    ASOF_TIP,
    CALLER_MODE_DRY_RUN,
    CONTRACT_SHA8,
    IF_SOURCE_COMMIT,
    IF_SOURCE_PIN_SHA256,
    IF_SOURCE_PIN_SHA8,
    OfflineIfCallerReject,
    OfflineIfRequest,
    PASS_CONTRACT_SHA8,
    REJECT_BLEND,
    REJECT_HISTORY,
    REJECT_INPUTS,
    REJECT_THROUGH_W8,
    W8_STATUS,
    build_contract_inputs,
    canonical_sha256,
    enforce_asof_and_history,
    evaluate_caller,
    invoke_independent_fair,
    lineage_pins,
    sha256_file,
    verify_asof_module,
    verify_source_pin,
    wiring_probe,
)
from src.services.nfl_simulator import (
    independent_fair_mus,
    simulate_nfl_game_independent_fair,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
OPS_DIR = REPO_ROOT / "data" / "ops" / "nfl-offline-if-caller-t4838u"
EVAL_DIR = OPS_DIR / "eval_w8_t4850u"
INPUTS_DIR = EVAL_DIR / "inputs"
PANEL_PATH = INPUTS_DIR / "team_efficiency_current_through_w7.json"
ACCEPT_PATH = INPUTS_DIR / "ACCEPT.json"
SCHEDULE_PATH = (
    REPO_ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "nfl_season_engine"
    / "data"
    / "nfl-canonical-schedule-2026.json"
)

OWNER_CLEAR = "t4850u"
ALEX_COVERAGE_SHA256 = (
    "d5d6a3aa5adee28e60069f2775817ceb87c3cd924f02784abd46aec3f59dd4f6"
)
COS_ACCEPT = "6685d848"
THROUGH_W7_ACCEPT = "c674da77"
THROUGH_W7_ACCEPT_SHA256 = (
    "c674da77dd7419851b63357ffd64028b1d2c2d3d98039a200177da7188eba115"
)
PANEL_SHA256 = (
    "340a06dd81e25eece87a4d8475feca918e1ccb3c5d9663edfe5063a85ba3fa9e"
)
SCHEDULE_SHA256 = (
    "d88ae73440d3da87198ddb9d8986e0a19773cd3626215e495138907c44ff43fe"
)
CALLER_TIP = "b6d019b0"
CALLER_TIP_FULL = "b6d019b051f13156354504097d1635b64ab7ceae"
PANEL_AS_OF_TS = "2026-10-30T14:40:22Z"
TARGET_WEEK = 8
RATING_WEEK = 7
SEASON = 2026
EVAL_SIMULATIONS = 4000
EVAL_SEED_BASE = 48500
TNF_GAME_ID = "2026-W08-CAR@GB"
TNF_TEAMS = frozenset({"CAR", "GB"})
BYE_ROLLING_AS_OF = {"BUF": 6, "JAX": 6, "LAC": 6, "WAS": 6}
TEAM_TO_PANEL = {"LAR": "LA", "WSH": "WAS"}
SUPPORTED_GAMES = (
    "2026-W08-ARI@DAL",
    "2026-W08-ATL@TB",
    "2026-W08-BAL@BUF",
    "2026-W08-CLE@PIT",
    "2026-W08-IND@JAX",
    "2026-W08-LV@NYJ",
    "2026-W08-MIN@DET",
    "2026-W08-TEN@CIN",
    "2026-W08-LAC@LAR",
    "2026-W08-KC@DEN",
    "2026-W08-NE@MIA",
    "2026-W08-PHI@WAS",
    "2026-W08-CHI@SEA",
)

REJECT_TNF = "TNF_EXCLUDED"
REJECT_PANEL = "PANEL_PIN_MISMATCH"
REJECT_BYE = "BYE_ROLLING_AS_OF"
REJECT_ALIAS = "TEAM_ALIAS"
REJECT_PUBLICATION = "PUBLICATION_REFUSED"

ET = ZoneInfo("America/New_York")


def rest_days_from_schedule(game_time_iso: str | None) -> float:
    """Exact nfl_data.rest_days_from_schedule (no requests import)."""
    if not game_time_iso:
        return 7.0
    try:
        raw = game_time_iso[:-1] + "+00:00" if game_time_iso.endswith("Z") else game_time_iso
        game_dt = datetime.fromisoformat(raw)
    except Exception:
        return 7.0
    dow = game_dt.astimezone(timezone.utc).weekday()
    if dow == 3:
        return 4.0
    if dow == 0:
        return 6.0
    return 7.0


class EvalW8Reject(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = str(code)
        self.message = str(message)
        super().__init__(f"{self.code}: {self.message}")


def _as_utc(value: str) -> datetime:
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        raise EvalW8Reject("CUTOFF", "naive timestamp rejected")
    return dt.astimezone(timezone.utc)


def panel_team(token: str) -> str:
    return TEAM_TO_PANEL.get(str(token), str(token))


def load_panel(path: Path = PANEL_PATH) -> Dict[str, Any]:
    digest = sha256_file(path)
    if digest != PANEL_SHA256:
        raise EvalW8Reject(
            REJECT_PANEL,
            f"through-W7 panel sha256 {digest} != {PANEL_SHA256}",
        )
    panel = json.loads(path.read_text(encoding="utf-8"))
    if int(panel.get("as_of_week") or 0) != RATING_WEEK:
        raise EvalW8Reject(REJECT_PANEL, "panel as_of_week must be 7")
    if panel.get("2025_prior_used") is True:
        raise EvalW8Reject(REJECT_PANEL, "2025 prior forbidden")
    if TNF_GAME_ID in json.dumps(panel):
        raise EvalW8Reject(REJECT_TNF, "TNF CAR@GB must not appear in through-W7 panel")
    for team, row in panel["teams"].items():
        rolling = int(row.get("rolling_as_of_week") or 0)
        if rolling >= TARGET_WEEK:
            raise EvalW8Reject(
                REJECT_TNF,
                f"{team} rolling_as_of_week={rolling} is not < target 8",
            )
    return panel


def load_schedule(path: Path = SCHEDULE_PATH) -> Dict[str, Any]:
    digest = sha256_file(path)
    if digest != SCHEDULE_SHA256:
        raise EvalW8Reject(
            REJECT_PANEL,
            f"schedule sha256 {digest} != {SCHEDULE_SHA256}",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def history_w1_w7(schedule: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for game in schedule.get("games") or []:
        week = int(game.get("week") or 0)
        game_id = str(game.get("game_id") or "")
        if week < 1 or week > 7:
            continue
        if game_id == TNF_GAME_ID or week >= TARGET_WEEK:
            raise EvalW8Reject(REJECT_TNF, f"W8/TNF leaked into W1–W7 history: {game_id}")
        rows.append(
            {
                "week": week,
                "game_id": game_id,
                "game_date": str(game.get("kickoff_utc") or "")[:10],
                "kickoff_ts": game.get("kickoff_utc"),
            }
        )
    if not rows:
        raise EvalW8Reject(REJECT_HISTORY, "W1–W7 schedule history empty")
    return rows


def verify_rest_days(kickoff_utc: str) -> Dict[str, Any]:
    days = float(rest_days_from_schedule(kickoff_utc))
    utc = _as_utc(kickoff_utc)
    et = utc.astimezone(ET)
    return {
        "rest_days_home": days,
        "rest_days_away": days,
        "source": "nfl_data.rest_days_from_schedule",
        "status": "VERIFY_AT_CONSUME",
        "kickoff_utc": kickoff_utc,
        "dow_utc": utc.weekday(),
        "dow_et": et.weekday(),
        "utc_et_dow_mismatch": utc.weekday() != et.weekday(),
        "note": (
            "UTC DOW heuristic (Thu=4, Mon=6, else=7). "
            "Bye rest is not added. Record mismatch; do not invent rest."
        ),
    }


def _t3_pack(home: Mapping[str, Any], away: Mapping[str, Any]) -> Dict[str, Any]:
    def minus(left: Any, right: Any) -> Optional[float]:
        if left is None or right is None:
            return None
        return float(left) - float(right)

    return {
        "home_off_epa_5g": home.get("off_epa_5g"),
        "away_off_epa_5g": away.get("off_epa_5g"),
        "home_def_epa_allowed_5g": home.get("def_epa_allowed_5g"),
        "away_def_epa_allowed_5g": away.get("def_epa_allowed_5g"),
        "home_pass_rate_5g": home.get("pass_rate_5g"),
        "away_pass_rate_5g": away.get("pass_rate_5g"),
        "home_success_offense_5g": home.get("success_5g"),
        "away_success_offense_5g": away.get("success_5g"),
        "home_success_defense_allowed_5g": home.get("success_defense_allowed_5g"),
        "away_success_defense_allowed_5g": away.get("success_defense_allowed_5g"),
        "diff_off_epa_5g": minus(home.get("off_epa_5g"), away.get("off_epa_5g")),
        "diff_def_epa_allowed_5g": minus(
            away.get("def_epa_allowed_5g"), home.get("def_epa_allowed_5g")
        ),
        "diff_pressure_generated_5g": minus(
            home.get("pressure_rate_generated_5g"),
            away.get("pressure_rate_generated_5g"),
        ),
        "diff_pressure_allowed_5g": minus(
            away.get("pressure_rate_allowed_5g"),
            home.get("pressure_rate_allowed_5g"),
        ),
        "diff_red_zone_td_rate_5g": minus(
            home.get("red_zone_td_rate_5g"), away.get("red_zone_td_rate_5g")
        ),
    }


def _t4_success(pack: Mapping[str, Any]) -> Optional[float]:
    terms: List[float] = []
    ho, ao = pack.get("home_success_offense_5g"), pack.get("away_success_offense_5g")
    hd, ad = (
        pack.get("home_success_defense_allowed_5g"),
        pack.get("away_success_defense_allowed_5g"),
    )
    if ho is not None and ao is not None:
        terms.append(float(ho) - float(ao))
    if ad is not None and hd is not None:
        terms.append(float(ad) - float(hd))
    if len(terms) != 2:
        return None
    return sum(terms) / 2.0


def publication_controls(packet: Mapping[str, Any]) -> Dict[str, Any]:
    """#8 — prepare and test publication controls. Do not enable public delivery."""
    reasons = [
        "EVAL_ONLY t4850u — FREE_PUBLIC pending separate OWNER decision",
        "Coming Soon ON / CERT=0 / NFL NO-GO",
        "e1_admissible=false; scoring_admissible=false; DATA_PARTIAL",
        "Odds HOLD; no sportsbook; no betting language",
        "diagnostic label is not a controlled public surface",
    ]
    if packet.get("e1_admissible") is True or packet.get("scoring_admissible") is True:
        reasons.append("admissible flags must stay false")
    if packet.get("public_delivery") is True:
        raise EvalW8Reject(
            REJECT_PUBLICATION, "public_delivery cannot be enabled on EVAL_ONLY"
        )
    decision = {
        "coming_soon": "ON",
        "cert": 0,
        "nfl": "NO-GO",
        "public_delivery": False,
        "free_public": "REFUSED",
        "betting": "BLOCKED",
        "odds": "HOLD",
        "c10": "HOLD",
        "surface": "OFFLINE_DIAGNOSTIC_ONLY",
        "paid_edge_language": False,
        "cert_claim": False,
        "reasons": reasons,
        "enabled": False,
    }
    return decision


def refuse_public_delivery(packet: Mapping[str, Any]) -> Dict[str, Any]:
    controls = publication_controls(packet)
    if controls["enabled"] or controls["public_delivery"] or controls["free_public"] != "REFUSED":
        raise EvalW8Reject(REJECT_PUBLICATION, "publication control failed closed")
    return controls


def _eligibility_row(
    *,
    game_id: str,
    schedule_game: Mapping[str, Any],
    panel: Mapping[str, Any],
) -> Dict[str, Any]:
    if game_id == TNF_GAME_ID:
        raise EvalW8Reject(REJECT_TNF, "TNF CAR@GB must not enter ratings")
    home_sched = str(schedule_game["home_team_id"])
    away_sched = str(schedule_game["away_team_id"])
    home = panel_team(home_sched)
    away = panel_team(away_sched)
    if home_sched == "LAR" and home != "LA":
        raise EvalW8Reject(REJECT_ALIAS, "LAR must map to panel LA")
    teams = panel["teams"]
    if home not in teams or away not in teams:
        raise EvalW8Reject(REJECT_ALIAS, f"panel missing {home} or {away}")
    h, a = teams[home], teams[away]
    for team_token, row in ((home_sched, h), (away_sched, a)):
        expected = BYE_ROLLING_AS_OF.get(panel_team(team_token))
        rolling = int(row["rolling_as_of_week"])
        if expected is not None and rolling != expected:
            raise EvalW8Reject(
                REJECT_BYE,
                f"{team_token} rolling_as_of={rolling} != bye expected {expected}",
            )
        if expected is None and rolling != RATING_WEEK:
            raise EvalW8Reject(
                REJECT_BYE,
                f"{team_token} rolling_as_of={rolling} != {RATING_WEEK}",
            )
        if rolling >= TARGET_WEEK:
            raise EvalW8Reject(REJECT_TNF, f"{team_token} rolling week leaked into W8")
        if int(row.get("as_of_week") or 0) != RATING_WEEK:
            raise EvalW8Reject(REJECT_PANEL, f"{team_token} as_of_week != 7")
        if row.get("2025_prior_used") is True:
            raise EvalW8Reject(REJECT_PANEL, f"{team_token} used 2025 prior")
        if not row.get("t5_ok"):
            raise EvalW8Reject(REJECT_INPUTS, f"{team_token} t5_ok is false")
        if int(row.get("games_in_window_5") or 0) != 5:
            raise EvalW8Reject(REJECT_INPUTS, f"{team_token} games_in_window_5 != 5")
    rest = verify_rest_days(str(schedule_game["kickoff_utc"]))
    return {
        "game_id": game_id,
        "status": "SUPPORTED",
        "home_team": home_sched,
        "away_team": away_sched,
        "panel_home": home,
        "panel_away": away,
        "kickoff_utc": schedule_game["kickoff_utc"],
        "home_rolling_as_of": int(h["rolling_as_of_week"]),
        "away_rolling_as_of": int(a["rolling_as_of_week"]),
        "rest": rest,
        "tnf_excluded": True,
    }


def build_eval_request(
    *,
    game_id: str,
    schedule_game: Mapping[str, Any],
    panel: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
) -> tuple[OfflineIfRequest, Dict[str, Any]]:
    elig = _eligibility_row(game_id=game_id, schedule_game=schedule_game, panel=panel)
    home = elig["panel_home"]
    away = elig["panel_away"]
    h = panel["teams"][home]
    a = panel["teams"][away]
    pack = _t3_pack(h, a)
    success = _t4_success(pack)
    if success is None:
        raise EvalW8Reject(REJECT_INPUTS, f"{game_id} T4 both success terms required")
    efficiency = {
        "offense_index_home": h["offense_index"],
        "offense_index_away": a["offense_index"],
        "defense_index_home": h["defense_index"],
        "defense_index_away": a["defense_index"],
        "home_off_epa_5g": pack["home_off_epa_5g"],
        "away_off_epa_5g": pack["away_off_epa_5g"],
        "home_def_epa_allowed_5g": pack["home_def_epa_allowed_5g"],
        "away_def_epa_allowed_5g": pack["away_def_epa_allowed_5g"],
        "home_pass_rate_5g": pack["home_pass_rate_5g"],
        "away_pass_rate_5g": pack["away_pass_rate_5g"],
        "home_success_offense_5g": pack["home_success_offense_5g"],
        "away_success_offense_5g": pack["away_success_offense_5g"],
        "home_success_defense_allowed_5g": pack["home_success_defense_allowed_5g"],
        "away_success_defense_allowed_5g": pack["away_success_defense_allowed_5g"],
        "matchup_diff_off_epa_5g": pack["diff_off_epa_5g"],
        "matchup_diff_def_epa_allowed_5g": pack["diff_def_epa_allowed_5g"],
        "matchup_diff_success_rate_5g": success,
        "matchup_diff_pressure_generated_5g": pack["diff_pressure_generated_5g"],
        "matchup_diff_pressure_allowed_5g": pack["diff_pressure_allowed_5g"],
        "matchup_diff_red_zone_td_rate_5g": pack["diff_red_zone_td_rate_5g"],
    }
    req = OfflineIfRequest(
        game_id=game_id,
        home_team=elig["home_team"],
        away_team=elig["away_team"],
        matchup_season=SEASON,
        matchup_week=TARGET_WEEK,
        rest_days_home=elig["rest"]["rest_days_home"],
        rest_days_away=elig["rest"]["rest_days_away"],
        forecast_cutoff_ts=str(schedule_game["kickoff_utc"]).replace(".000Z", "Z"),
        rating_week=RATING_WEEK,
        available_rating_weeks=(RATING_WEEK,),
        history_games=tuple(history),
        efficiency=efficiency,
        extra={},
        mode=CALLER_MODE_DRY_RUN,
        simulations=EVAL_SIMULATIONS,
        seed=EVAL_SEED_BASE + SUPPORTED_GAMES.index(game_id),
    )
    return req, elig


def _invoke_diagnostic(req: OfflineIfRequest) -> Dict[str, Any]:
    """IF invoke labeled DIAGNOSTIC. Never operational E1. Never sportsbook."""
    if req.mode != CALLER_MODE_DRY_RUN:
        raise EvalW8Reject("E1_LABEL_FORBIDDEN", "eval path is dry_run_wiring / DIAGNOSTIC only")
    verify_source_pin()
    verify_asof_module()
    enforce_asof_and_history(req)
    inputs = build_contract_inputs(req)
    projection = simulate_nfl_game_independent_fair(
        inputs,
        simulations=req.simulations,
        seed=req.seed,
        market_spread_home=None,
        market_total=None,
    )
    blend = projection["independent_fair"]["market_blend"]
    if blend != 0:
        raise EvalW8Reject(REJECT_BLEND, f"blend {blend} != 0")
    margin_mu, total_mu = independent_fair_mus(projection)
    sigma = float(projection["independent_fair"]["sigma"])
    return {
        "game_id": req.game_id,
        "forecast_class": "DIAGNOSTIC",
        "e1": False,
        "e1_admissible": False,
        "e1_label": None,
        "scoring_admissible": False,
        "public_delivery": False,
        "independent_fair_invoked": True,
        "market_blend": 0,
        "rating_week": RATING_WEEK,
        "target_week": TARGET_WEEK,
        "simulations": req.simulations,
        "seed": req.seed,
        "margin_mu": margin_mu,
        "total_mu": total_mu,
        "sigma": sigma,
        "spread_home": round(-margin_mu, 2),
        "note": (
            "EVAL_ONLY diagnostic. Not an admissible E1 forecast. "
            "Not FREE_PUBLIC. Not betting. Do not score or publish."
        ),
    }


def operational_w8_still_blocked() -> Dict[str, Any]:
    """Prove the W9/E1 operational path is untouched and still fail-closed."""
    req, _ = build_eval_request(
        game_id=SUPPORTED_GAMES[0],
        schedule_game={
            "home_team_id": "DAL",
            "away_team_id": "ARI",
            "kickoff_utc": "2026-11-01T18:00:00.000Z",
        },
        panel=load_panel(),
        history=history_w1_w7(load_schedule()),
    )
    req.mode = "operational"
    try:
        invoke_independent_fair(req)
        return {"blocked": False, "code": None, "message": "operational invoke unexpectedly passed"}
    except OfflineIfCallerReject as exc:
        return {"blocked": exc.code == REJECT_THROUGH_W8, "code": exc.code, "message": exc.message}


def run_eval_slate(*, write: bool = False) -> Dict[str, Any]:
    verify_source_pin()
    verify_asof_module()
    panel = load_panel()
    schedule = load_schedule()
    history = history_w1_w7(schedule)
    by_id = {str(g["game_id"]): g for g in schedule.get("games") or []}
    if TNF_GAME_ID not in by_id:
        raise EvalW8Reject(REJECT_TNF, "schedule missing TNF id for exclusion check")

    eligibility: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []

    # TNF must fail closed if asked.
    try:
        _eligibility_row(
            game_id=TNF_GAME_ID,
            schedule_game=by_id[TNF_GAME_ID],
            panel=panel,
        )
        unresolved.append({"game_id": TNF_GAME_ID, "code": "TNF_NOT_REJECTED"})
    except EvalW8Reject as exc:
        if exc.code != REJECT_TNF:
            unresolved.append({"game_id": TNF_GAME_ID, "code": exc.code, "message": exc.message})

    for game_id in SUPPORTED_GAMES:
        sched = by_id.get(game_id)
        if sched is None:
            unresolved.append({"game_id": game_id, "code": "SCHEDULE_MISSING"})
            eligibility.append({"game_id": game_id, "status": "INPUT_GAP", "code": "SCHEDULE_MISSING"})
            continue
        try:
            req, elig = build_eval_request(
                game_id=game_id,
                schedule_game=sched,
                panel=panel,
                history=history,
            )
            eligibility.append(elig)
            results.append(_invoke_diagnostic(req))
        except (EvalW8Reject, OfflineIfCallerReject) as exc:
            eligibility.append(
                {
                    "game_id": game_id,
                    "status": "FAIL_CLOSED",
                    "code": exc.code,
                    "message": exc.message,
                }
            )
            unresolved.append(
                {"game_id": game_id, "code": exc.code, "message": exc.message}
            )
            results.append(
                {
                    "game_id": game_id,
                    "forecast_class": "NONE",
                    "e1_admissible": False,
                    "fail_closed": True,
                    "code": exc.code,
                    "message": exc.message,
                }
            )

    operational = operational_w8_still_blocked()
    if not operational["blocked"]:
        unresolved.append(
            {
                "game_id": "*",
                "code": "OPERATIONAL_PATH_NOT_BLOCKED",
                "message": operational["message"],
            }
        )
    caller = evaluate_caller(write=False)
    if caller.status != "BLOCKED" or REJECT_THROUGH_W8 not in caller.codes:
        unresolved.append(
            {
                "game_id": "*",
                "code": "CALLER_PACKET_NOT_BLOCKED",
                "message": f"status={caller.status} codes={caller.codes}",
            }
        )

    invoked = [row for row in results if row.get("independent_fair_invoked")]
    coherence = {
        "status": "DIAGNOSTIC_IF_ONLY",
        "joint_st_ml_packet": "INSUFFICIENT",
        "market_compare": "INSUFFICIENT",
        "n_if_invoked": len(invoked),
        "all_blend_zero": all(row.get("market_blend") == 0 for row in invoked),
        "all_finite_mus": all(
            math.isfinite(float(row["margin_mu"])) and math.isfinite(float(row["total_mu"]))
            for row in invoked
        )
        if invoked
        else False,
        "note": (
            "No sealed joint ST/ML coherence packet and no market-beat evidence. "
            "Do not treat omitted failed coherence outputs as validation of remaining prices. "
            "Odds HOLD — no invented market evidence."
        ),
    }
    if not invoked or not coherence["all_blend_zero"] or not coherence["all_finite_mus"]:
        unresolved.append({"game_id": "*", "code": "COHERENCE_IF_MUS", "detail": coherence})

    packet = {
        "status": "DIAGNOSTIC_SEALED" if invoked and not any(
            u.get("code") in {"OPERATIONAL_PATH_NOT_BLOCKED", "CALLER_PACKET_NOT_BLOCKED"}
            for u in unresolved
        )
        else "BLOCKED",
        "eval_class": "EVAL_ONLY",
        "e1_admissible": False,
        "scoring_admissible": False,
        "public_delivery": False,
        "data_status": W8_STATUS,
        "through_w8_declared_complete": False,
        "n_supported": sum(1 for row in eligibility if row.get("status") == "SUPPORTED"),
        "n_invoked": len(invoked),
        "n_fail_closed": sum(1 for row in results if row.get("fail_closed")),
        "tnf_excluded": TNF_GAME_ID,
        "pins": eval_pins(),
        "operational_path": operational,
        "caller_engineering_packet": caller.status,
        "coherence": coherence,
    }
    controls = refuse_public_delivery(packet)
    packet["publication_controls"] = controls

    findings = {
        "readiness_1_wired_admissible_run": {
            "wired_diagnostic_run": len(invoked) == 13,
            "scoring_admissible": False,
            "e1_admissible": False,
            "fact": (
                f"{len(invoked)}/13 remaining W8 games invoked Independent Fair "
                f"(blend=0, rating_week=7, through-W7 {THROUGH_W7_ACCEPT}). "
                "This is DIAGNOSTIC wiring, not a scoring-admissible / OWNER E1 run."
            ),
        },
        "readiness_4_coherence": {
            "status": coherence["status"],
            "joint_st_ml": "INSUFFICIENT",
            "market": "INSUFFICIENT",
            "fact": coherence["note"],
        },
        "readiness_6_fail_closed": {
            "tnf_excluded": True,
            "operational_through_w8_still_blocked": operational["blocked"],
            "publication_refused": controls["free_public"] == "REFUSED",
            "fact": (
                "TNF CAR@GB rejected; operational invoke still THROUGH_W8_DATA_ACCEPT_MISSING; "
                "publication controls refuse FREE_PUBLIC/BETTING; same-week rolling >=8 rejected."
            ),
        },
        "readiness_8_publication_controls": {
            "prepared": True,
            "enabled": False,
            "coming_soon": "ON",
            "cert": 0,
            "public_delivery": False,
            "fact": "Controls tested. Public delivery not enabled.",
        },
    }

    artifacts = {
        "eligibility": eligibility,
        "results": results,
        "unresolved": unresolved,
        "packet": packet,
        "findings": findings,
        "publication_controls": controls,
        "wiring_digest": (wiring_probe() or {}).get("digest"),
    }
    if write:
        _write_artifacts(artifacts)
    return artifacts


def eval_pins() -> Dict[str, Any]:
    pins = lineage_pins()
    pins["eval"] = {
        "owner_clear": OWNER_CLEAR,
        "alex_coverage_sha256": ALEX_COVERAGE_SHA256,
        "cos_accept": COS_ACCEPT,
        "through_w7_accept": THROUGH_W7_ACCEPT,
        "through_w7_accept_sha256": THROUGH_W7_ACCEPT_SHA256,
        "panel_sha256": PANEL_SHA256,
        "schedule_sha256": SCHEDULE_SHA256,
        "caller_tip": CALLER_TIP,
        "caller_tip_full": CALLER_TIP_FULL,
        "source_only": IF_SOURCE_PIN_SHA8,
        "source_only_sha256": IF_SOURCE_PIN_SHA256,
        "source_commit": IF_SOURCE_COMMIT,
        "as_of": ASOF_BOUNDARY_SHA8,
        "as_of_tip": ASOF_TIP,
        "as_of_module": ASOF_MODULE_SHA256,
        "contract": CONTRACT_SHA8,
        "pass_contract": PASS_CONTRACT_SHA8,
        "rating_week": RATING_WEEK,
        "target_week": TARGET_WEEK,
        "panel_as_of_ts": PANEL_AS_OF_TS,
        "w8_status": W8_STATUS,
        "distinct_lineages": True,
    }
    return pins


def render_packet_md(artifacts: Mapping[str, Any]) -> str:
    packet = artifacts["packet"]
    lines = [
        "# DIAGNOSTIC PACKET t4850u — EVAL_ONLY W8 (through-W7 / rating_week=7)",
        "",
        f"**Status:** `{packet['status']}`",
        f"**Class:** EVAL_ONLY · DIAGNOSTIC · e1_admissible=`False`",
        f"**Invoked:** {packet['n_invoked']}/13 · SUPPORTED {packet['n_supported']}",
        f"**TNF:** excluded `{TNF_GAME_ID}`",
        f"**Public delivery:** `False` · Coming Soon ON · CERT=0",
        "",
        "Pins:",
        f"- SOURCE ONLY `{IF_SOURCE_PIN_SHA8}` @ `{IF_SOURCE_COMMIT}`",
        f"- ASOF `PASS_ASOF_BOUNDARY {ASOF_BOUNDARY_SHA8}` tip `{ASOF_TIP}`",
        f"- CONTRACT `{CONTRACT_SHA8}` / PASS_CONTRACT `{PASS_CONTRACT_SHA8}` ≠ DATA ACCEPT",
        f"- through-W7 `{THROUGH_W7_ACCEPT}` panel `{PANEL_SHA256[:8]}`",
        f"- caller tip `{CALLER_TIP}` · schedule `{SCHEDULE_SHA256[:8]}`",
        f"- W8 remains `{W8_STATUS}` · through-W8 complete=`False`",
        "",
        "Per-game results are DIAGNOSTIC. ≠FREE_PUBLIC ≠BETTING ≠E1.",
        "",
        "NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10/Odds HOLD.",
        "",
    ]
    return "\n".join(lines)


def _write_artifacts(artifacts: Mapping[str, Any]) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {
        "ELIGIBILITY.json": artifacts["eligibility"],
        "RESULTS.json": artifacts["results"],
        "UNRESOLVED.json": artifacts["unresolved"],
        "FINDINGS.json": artifacts["findings"],
        "PUBLICATION_CONTROLS.json": artifacts["publication_controls"],
        "DIAGNOSTIC_PACKET.json": artifacts["packet"],
        "PINS.json": artifacts["packet"]["pins"],
    }
    for name, payload in mapping.items():
        (EVAL_DIR / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
    (EVAL_DIR / "DIAGNOSTIC_PACKET.md").write_text(
        render_packet_md(artifacts), encoding="utf-8"
    )
    (EVAL_DIR / "FINDINGS.md").write_text(_render_findings(artifacts), encoding="utf-8")
    (EVAL_DIR / "UNRESOLVED.md").write_text(_render_unresolved(artifacts), encoding="utf-8")
    lines = []
    for path in sorted(EVAL_DIR.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{sha256_file(path)}  {path.name}")
    for path in sorted((EVAL_DIR / "inputs").iterdir()):
        lines.append(f"{sha256_file(path)}  inputs/{path.name}")
    (EVAL_DIR / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_findings(artifacts: Mapping[str, Any]) -> str:
    findings = artifacts["findings"]
    unresolved = artifacts["unresolved"]
    lines = [
        "# Engineering findings t4850u (facts only)",
        "",
        "## #1 wired admissible run",
        findings["readiness_1_wired_admissible_run"]["fact"],
        "",
        "## #4 coherence",
        findings["readiness_4_coherence"]["fact"],
        "",
        "## #6 fail-closed",
        findings["readiness_6_fail_closed"]["fact"],
        "",
        "## #8 publication controls",
        findings["readiness_8_publication_controls"]["fact"],
        "",
        "## Unresolved",
    ]
    if not unresolved:
        lines.append("None beyond known PARTIAL / INSUFFICIENT market+joint-ST/ML gaps.")
    else:
        for item in unresolved:
            lines.append(f"- `{item.get('game_id')}` `{item.get('code')}` {item.get('message', '')}")
    lines.extend(["", "≠FREE_PUBLIC ≠BETTING. NFL NO-GO · CERT=0.", ""])
    return "\n".join(lines)


def _render_unresolved(artifacts: Mapping[str, Any]) -> str:
    invocation = artifacts["unresolved"]
    rest_mismatch = [
        row
        for row in artifacts["eligibility"]
        if row.get("status") == "SUPPORTED" and row.get("rest", {}).get("utc_et_dow_mismatch")
    ]
    lines = [
        "# Unresolved t4850u",
        "",
        "## Invocation failures",
        "None." if not invocation else "",
    ]
    for item in invocation:
        lines.append(f"- `{item.get('game_id')}` `{item.get('code')}` {item.get('message', '')}")
    lines.extend(
        [
            "",
            "## Evidence / decision gaps (not invocation failures)",
            "- through-W8 DATA ACCEPT absent — DATA_PARTIAL preserved; operational E1 path remains BLOCKED",
            "- #4 joint ST/ML coherence packet INSUFFICIENT — IF mus only; do not infer remaining prices are valid",
            "- #5/#7 market-beat INSUFFICIENT — Odds HOLD; no market evidence invented",
            "- FREE_PUBLIC not CLEARed — publication controls refuse delivery (Coming Soon ON, CERT=0)",
            "- rest_days VERIFY_AT_CONSUME — UTC DOW heuristic; bye rest not added",
        ]
    )
    for row in rest_mismatch:
        rest = row["rest"]
        lines.append(
            f"- `{row['game_id']}` rest={rest['rest_days_home']} "
            f"dow_utc={rest['dow_utc']} dow_et={rest['dow_et']} UTC/ET mismatch"
        )
    lines.extend(["", "≠FREE_PUBLIC ≠BETTING. NFL NO-GO · CERT=0.", ""])
    return "\n".join(lines)
