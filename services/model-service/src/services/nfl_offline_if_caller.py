"""Offline DRAFT Independent Fair caller (t4838u).

Engineering-only. Non-production. Not an E1 emit path.

Authority: DECISION_RYAN_t4838u sha256 1aeb63ee… · COS_ORDER t4838u.

Lineages (kept distinct in every record):
  SOURCE ONLY  — nfl_simulator.py @1b39f4e9 sha256 52d9e909… (ratified 75d1b695)
  ASOF         — PASS_ASOF_BOUNDARY cf514078 · tip 1010b86f · module 7dc6afea…
  CONTRACT     — Alex v2 b41f4b43 (PASS_CONTRACT 1a53bbd3 on file ≠ DATA ACCEPT)

≠E1 emit ≠admit ≠merge ≠C10 ≠Odds ≠CERT ≠subscriber ≠historical rescoring
≠model fit. NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from src.services.nfl_pregame_asof import (
    IF_MATCHUP_ASOF_CONTRACT,
    PINNED_IF_INGEST_SHA,
    PregameAsofReject,
    reject_if_not_pregame_game,
    resolve_pregame_rating_week,
)
from src.services.nfl_simulator import (
    INDEPENDENT_FAIR_FORECAST_LABEL,
    NflGameInputs,
    independent_fair_mus,
    simulate_nfl_game_independent_fair,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODEL_SERVICE_ROOT = Path(__file__).resolve().parents[2]
SIMULATOR_PY = MODEL_SERVICE_ROOT / "src" / "services" / "nfl_simulator.py"
ASOF_PY = MODEL_SERVICE_ROOT / "src" / "services" / "nfl_pregame_asof.py"
OPS_DIR = REPO_ROOT / "data" / "ops" / "nfl-offline-if-caller-t4838u"
THROUGH_W8_ACCEPT_PATH = OPS_DIR / "THROUGH_W8_DATA_ACCEPT.json"
PACKET_JSON_PATH = OPS_DIR / "CALLER_PACKET.json"
PACKET_MD_PATH = OPS_DIR / "CALLER_PACKET.md"
EVIDENCE_PATH = OPS_DIR / "EVIDENCE.json"
DRY_RUN_PATH = OPS_DIR / "DRY_RUN.json"

DECISION_SHA256 = (
    "1aeb63ee926955109409bfbdb5cea79b7f940b50e5ddae6cf51bd1ccd4e9c17a"
)
COS_ORDER_SHA256 = (
    "40634a3ebcf799368e0d950f98cb1840d7b87dfb40de6ec98d18a90f8da93dd4"
)

# SOURCE ONLY — implementation reference. Not an as-of identity.
IF_SOURCE_COMMIT = "1b39f4e9"
IF_SOURCE_COMMIT_FULL = "1b39f4e9f6b2e04c264a41831f3bb7273e475011"
IF_SOURCE_PIN_SHA8 = "52d9e909"
IF_SOURCE_PIN_SHA256 = (
    "52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385"
)
IF_SOURCE_PIN_OBJECT = "services/model-service/src/services/nfl_simulator.py"
IF_SOURCE_PIN_STATUS = "SOURCE_ONLY"
IF_SOURCE_PIN_RATIFIED = "75d1b695"

# Corrected as-of lineage — distinct from 52d9e909 in all evidence.
ASOF_BOUNDARY_SHA8 = "cf514078"
ASOF_BOUNDARY_STATUS = "PASS_ASOF_BOUNDARY"
ASOF_TIP = "1010b86f"
ASOF_TIP_LINEAGE = "1010b86f+"
ASOF_MODULE_SHA256 = (
    "7dc6afea2f13705b02683a5d16e53193adb7acd5441bde8494268fe850c50c98"
)
ASOF_MODULE_OBJECT = "services/model-service/src/services/nfl_pregame_asof.py"
ASOF_RESEARCH_ID_REPAIR_TIP = "ef209d35"
ASOF_RESEARCH_ID_REPAIR_SCOPE = (
    "acknowledged; out of scope for this PR except citing as-of"
)

# Input contract. PASS_CONTRACT ≠ DATA ACCEPT.
CONTRACT_SHA8 = "b41f4b43"
CONTRACT_SHA256 = (
    "b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4"
)
PASS_CONTRACT_SHA8 = "1a53bbd3"
PASS_CONTRACT_SHA256 = (
    "1a53bbd33f32fec8d25a102f2abea7b975a92fbd55edbaaaafe020055c25b9f8"
)
PASS_CONTRACT_NOTE = "PASS_CONTRACT 1a53bbd3 on file ≠ DATA ACCEPT"

# W8 citation only — do not invent W8 rows.
W8_STATUS = "DATA_PARTIAL"
W8_COMPLETE = "1/14"
W8_TIP = "ba9e8426"
W8_PR = 663
W8_IMV_PARTIAL = "c674da77"
W8_STANDBY = "COS_ORDER_CURSOR_t4770u_STANDBY_DATA_READY"

CALLER_ID = "offline-if-caller-t4838u"
CALLER_MODE_OPERATIONAL = "operational"
CALLER_MODE_DRY_RUN = "dry_run_wiring"
FORECAST_CLASS_WIRING_ONLY = "WIRING_ONLY"
FORECAST_CLASS_NONE = "NONE"

REQUIRED_20 = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
)

REQUIRED_CONTEXT = (
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
)

ALLOWED_INPUT_FIELDS = frozenset(REQUIRED_20 + REQUIRED_CONTEXT)

SPORTSBOOK_KEYS = frozenset(
    {
        "market_spread_home",
        "market_total",
        "market_spread",
        "market_line",
        "sportsbook",
        "odds",
        "dk_total",
        "dk_spread",
        "book",
        "close_spread",
        "close_total",
        "open_spread",
        "open_total",
    }
)

UNAPPROVED_HL_FIELDS = frozenset(
    name
    for name in (f.name for f in fields(NflGameInputs))
    if name not in ALLOWED_INPUT_FIELDS
)

DRY_RUN_SEED = 48380
DRY_RUN_SIMULATIONS = 300
DRY_RUN_GAME_ID = "SYN-2099-09-WIRING"
DRY_RUN_CUTOFF = "2099-11-01T00:00:00Z"

REJECT_THROUGH_W8 = "THROUGH_W8_DATA_ACCEPT_MISSING"
REJECT_SOURCE_PIN = "SOURCE_PIN_MISSING_OR_MISMATCH"
REJECT_TARGET_ID = "TARGET_GAME_ID_MISSING"
REJECT_CUTOFF = "FORECAST_CUTOFF_MISSING"
REJECT_HISTORY = "HISTORY_UNAVAILABLE"
REJECT_INPUTS = "INPUTS_INCOMPLETE"
REJECT_SPORTSBOOK = "SPORTSBOOK_FORBIDDEN"
REJECT_HL = "UNAPPROVED_HL"
REJECT_BLEND = "BLEND_NOT_ZERO"
REJECT_E1 = "E1_LABEL_FORBIDDEN"
REJECT_ASOF = "ASOF_BOUNDARY"


class OfflineIfCallerReject(Exception):
    """Fail-closed caller reject. Never impute, never emit E1."""

    def __init__(self, code: str, message: str) -> None:
        self.code = str(code)
        self.message = str(message)
        super().__init__(f"{self.code}: {self.message}")


@dataclass
class OfflineIfRequest:
    game_id: str
    home_team: str
    away_team: str
    matchup_season: int
    matchup_week: int
    rest_days_home: float
    rest_days_away: float
    forecast_cutoff_ts: str
    rating_week: Optional[int] = None
    available_rating_weeks: Optional[Sequence[int]] = None
    history_games: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    efficiency: Mapping[str, Any] = field(default_factory=dict)
    extra: Mapping[str, Any] = field(default_factory=dict)
    mode: str = CALLER_MODE_OPERATIONAL
    simulations: int = 4000
    seed: Optional[int] = None


@dataclass
class OfflineIfResult:
    blocked: bool
    status: str
    codes: list[str]
    messages: list[str]
    independent_fair_invoked: bool
    forecast_class: str
    e1_admissible: bool
    market_blend: Optional[int]
    evidence: Dict[str, Any]
    wiring: Optional[Dict[str, Any]] = None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_sha256(obj: object) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return sha256_bytes(blob)


def lineage_pins() -> Dict[str, Any]:
    """Report source, as-of, and contract identities as three distinct rows."""
    return {
        "source_only": {
            "status": IF_SOURCE_PIN_STATUS,
            "sha8": IF_SOURCE_PIN_SHA8,
            "sha256": IF_SOURCE_PIN_SHA256,
            "object": IF_SOURCE_PIN_OBJECT,
            "lineage_commit": IF_SOURCE_COMMIT,
            "lineage_commit_full": IF_SOURCE_COMMIT_FULL,
            "ratified": IF_SOURCE_PIN_RATIFIED,
            "note": "SOURCE ONLY — ratified 75d1b695; not an operational caller authorization; not the as-of identity",
        },
        "as_of": {
            "status": ASOF_BOUNDARY_STATUS,
            "sha8": ASOF_BOUNDARY_SHA8,
            "tip": ASOF_TIP,
            "tip_lineage": ASOF_TIP_LINEAGE,
            "module_object": ASOF_MODULE_OBJECT,
            "module_sha256": ASOF_MODULE_SHA256,
            "ingest_pin_cited_as_contrast_only": PINNED_IF_INGEST_SHA,
            "contract": IF_MATCHUP_ASOF_CONTRACT,
            "research_id_repair_tip": ASOF_RESEARCH_ID_REPAIR_TIP,
            "research_id_repair_scope": ASOF_RESEARCH_ID_REPAIR_SCOPE,
            "distinct_from_source_pin_52d9e909": True,
            "note": "PASS_ASOF_BOUNDARY cf514078 is the as-of identity. Do not report 52d9e909 as as-of.",
        },
        "contract": {
            "sha8": CONTRACT_SHA8,
            "sha256": CONTRACT_SHA256,
            "pass_contract_sha8": PASS_CONTRACT_SHA8,
            "pass_contract_sha256": PASS_CONTRACT_SHA256,
            "pass_contract_note": PASS_CONTRACT_NOTE,
            "required_20": list(REQUIRED_20),
            "required_context": list(REQUIRED_CONTEXT),
        },
        "w8": {
            "status": W8_STATUS,
            "complete": W8_COMPLETE,
            "tip": W8_TIP,
            "pr": W8_PR,
            "imv_data_partial": W8_IMV_PARTIAL,
            "standby": W8_STANDBY,
            "invent_w8": False,
        },
    }


def verify_source_pin(*, simulator_path: Path = SIMULATOR_PY) -> str:
    if not simulator_path.is_file():
        raise OfflineIfCallerReject(
            REJECT_SOURCE_PIN, f"source pin object missing: {simulator_path}"
        )
    digest = sha256_file(simulator_path)
    if digest != IF_SOURCE_PIN_SHA256:
        raise OfflineIfCallerReject(
            REJECT_SOURCE_PIN,
            f"{IF_SOURCE_PIN_OBJECT} sha256 {digest} != SOURCE ONLY pin "
            f"{IF_SOURCE_PIN_SHA256} (52d9e909 @ {IF_SOURCE_COMMIT})",
        )
    return digest


def verify_asof_module(*, asof_path: Path = ASOF_PY) -> str:
    if not asof_path.is_file():
        raise OfflineIfCallerReject(
            REJECT_ASOF, f"as-of module missing: {asof_path}"
        )
    digest = sha256_file(asof_path)
    if digest != ASOF_MODULE_SHA256:
        raise OfflineIfCallerReject(
            REJECT_ASOF,
            f"{ASOF_MODULE_OBJECT} sha256 {digest} != as-of module pin "
            f"{ASOF_MODULE_SHA256} (lineage {ASOF_TIP}; grade {ASOF_BOUNDARY_SHA8})",
        )
    if digest == IF_SOURCE_PIN_SHA256:
        raise OfflineIfCallerReject(
            REJECT_ASOF,
            "as-of module digest collided with SOURCE ONLY pin 52d9e909 — lineages must stay distinct",
        )
    return digest


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return path.name


def load_through_w8_accept(path: Path = THROUGH_W8_ACCEPT_PATH) -> Dict[str, Any]:
    rel = _repo_rel(path)
    if not path.is_file():
        return {
            "present": False,
            "data_accept": False,
            "status": "ABSENT",
            "path": rel,
        }
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {
            "present": True,
            "data_accept": False,
            "status": "INVALID",
            "path": rel,
        }
    status = str(raw.get("status") or "")
    accepted = bool(raw.get("data_accept") is True and status == "DATA_ACCEPT")
    return {
        "present": True,
        "data_accept": accepted,
        "status": status or "UNKNOWN",
        "record": raw,
        "path": rel,
    }


def require_through_w8_data_accept(path: Path = THROUGH_W8_ACCEPT_PATH) -> Dict[str, Any]:
    record = load_through_w8_accept(path)
    if not record.get("data_accept"):
        raise OfflineIfCallerReject(
            REJECT_THROUGH_W8,
            "through-W8 DATA ACCEPT flag absent "
            f"(status={record.get('status')}; W8={W8_STATUS} {W8_COMPLETE} "
            f"tip {W8_TIP} #663; PASS_CONTRACT {PASS_CONTRACT_SHA8} ≠ DATA ACCEPT)",
        )
    return record


def _finite_number(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or value is None:
        raise OfflineIfCallerReject(
            REJECT_INPUTS, f"{field_name} missing or non-numeric (no impute)"
        )
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise OfflineIfCallerReject(
            REJECT_INPUTS, f"{field_name} not finite (no impute)"
        ) from exc
    if not math.isfinite(number):
        raise OfflineIfCallerReject(
            REJECT_INPUTS, f"{field_name} not finite (no impute)"
        )
    return number


def _require_text(value: Any, *, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise OfflineIfCallerReject(
            REJECT_TARGET_ID, f"{field_name} missing (no impute)"
        )
    return str(value).strip()


def reject_sportsbook(extra: Mapping[str, Any]) -> None:
    hits = sorted(SPORTSBOOK_KEYS.intersection(extra))
    populated = [key for key in hits if extra.get(key) is not None]
    if populated:
        raise OfflineIfCallerReject(
            REJECT_SPORTSBOOK,
            f"sportsbook/market keys forbidden on IF(blend=0): {populated}",
        )


def reject_unapproved_hl(payload: Mapping[str, Any]) -> None:
    hits = [
        name
        for name in sorted(UNAPPROVED_HL_FIELDS)
        if payload.get(name) is not None
    ]
    if hits:
        raise OfflineIfCallerReject(
            REJECT_HL,
            f"unapproved HL / out-of-contract NflGameInputs populated: {hits}",
        )


def require_forecast_cutoff(value: Any) -> str:
    if value is None or not str(value).strip():
        raise OfflineIfCallerReject(
            REJECT_CUTOFF, "forecast_cutoff_ts required (no silent pass)"
        )
    raw = str(value).strip()
    if raw.endswith("Z"):
        parse = raw[:-1] + "+00:00"
    else:
        parse = raw
    try:
        dt = datetime.fromisoformat(parse)
    except ValueError as exc:
        raise OfflineIfCallerReject(
            REJECT_CUTOFF, f"forecast_cutoff_ts unparseable: {value!r}"
        ) from exc
    if dt.tzinfo is None:
        raise OfflineIfCallerReject(
            REJECT_CUTOFF,
            "naive forecast_cutoff_ts rejected (no impute to UTC); offset or Z required",
        )
    return raw


def require_target_identifiers(request: OfflineIfRequest) -> None:
    _require_text(request.game_id, field_name="game_id")
    _require_text(request.home_team, field_name="home_team")
    _require_text(request.away_team, field_name="away_team")
    if not isinstance(request.matchup_season, int) or isinstance(
        request.matchup_season, bool
    ):
        raise OfflineIfCallerReject(
            REJECT_TARGET_ID, "matchup_season must be a positive int (no impute)"
        )
    if request.matchup_season < 1:
        raise OfflineIfCallerReject(
            REJECT_TARGET_ID, "matchup_season must be a positive int (no impute)"
        )
    if not isinstance(request.matchup_week, int) or isinstance(
        request.matchup_week, bool
    ):
        raise OfflineIfCallerReject(
            REJECT_TARGET_ID, "matchup_week must be a positive int (no impute)"
        )
    if request.matchup_week < 1:
        raise OfflineIfCallerReject(
            REJECT_TARGET_ID, "matchup_week must be a positive int (no impute)"
        )


def enforce_asof_and_history(request: OfflineIfRequest) -> int:
    cutoff = require_forecast_cutoff(request.forecast_cutoff_ts)
    try:
        rating_week = resolve_pregame_rating_week(
            target_week=request.matchup_week,
            rating_week=request.rating_week,
            available_rating_weeks=request.available_rating_weeks,
        )
    except PregameAsofReject as exc:
        code = REJECT_HISTORY if exc.code.endswith("UNRESOLVED") else REJECT_ASOF
        if exc.code == "TARGET_WEEK_INVALID":
            code = REJECT_TARGET_ID
        raise OfflineIfCallerReject(code, exc.message) from exc
    if request.available_rating_weeks is None:
        raise OfflineIfCallerReject(
            REJECT_HISTORY,
            "available_rating_weeks required (unavailable history fail-closed; no impute)",
        )
    for game in request.history_games:
        try:
            reject_if_not_pregame_game(
                game_week=int(game["week"]),
                target_week=request.matchup_week,
                forecast_cutoff_ts=cutoff,
                game_id=game.get("game_id"),
                target_game_id=request.game_id,
                game_date=game.get("game_date"),
                target_game_date=game.get("target_game_date"),
                game_kickoff_ts=game.get("kickoff_ts"),
            )
        except PregameAsofReject as exc:
            raise OfflineIfCallerReject(REJECT_ASOF, exc.message) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise OfflineIfCallerReject(
                REJECT_HISTORY, f"history game incomplete: {exc}"
            ) from exc
    return rating_week


def build_contract_inputs(request: OfflineIfRequest) -> NflGameInputs:
    reject_sportsbook(request.extra)
    reject_unapproved_hl(request.extra)
    reject_unapproved_hl(request.efficiency)
    missing = [name for name in REQUIRED_20 if name not in request.efficiency]
    if missing:
        raise OfflineIfCallerReject(
            REJECT_INPUTS, f"required contract fields missing: {missing}"
        )
    values: Dict[str, Any] = {
        "game_id": _require_text(request.game_id, field_name="game_id"),
        "home_team": _require_text(request.home_team, field_name="home_team"),
        "away_team": _require_text(request.away_team, field_name="away_team"),
        "matchup_season": request.matchup_season,
        "matchup_week": request.matchup_week,
        "rest_days_home": _finite_number(
            request.rest_days_home, field_name="rest_days_home"
        ),
        "rest_days_away": _finite_number(
            request.rest_days_away, field_name="rest_days_away"
        ),
    }
    for name in REQUIRED_20:
        values[name] = _finite_number(
            request.efficiency[name], field_name=name
        )
    leftover = [
        name
        for name in request.efficiency
        if name not in ALLOWED_INPUT_FIELDS and request.efficiency.get(name) is not None
    ]
    if leftover:
        raise OfflineIfCallerReject(
            REJECT_HL,
            f"efficiency payload has out-of-contract fields: {sorted(leftover)}",
        )
    inputs = NflGameInputs(**values)
    populated_outside = [
        item.name
        for item in fields(inputs)
        if item.name not in ALLOWED_INPUT_FIELDS and getattr(inputs, item.name) is not None
    ]
    if populated_outside:
        raise OfflineIfCallerReject(
            REJECT_HL,
            f"NflGameInputs catch-all violated: {populated_outside}",
        )
    return inputs


def _assert_if_blend_zero(projection: Mapping[str, Any]) -> int:
    block = projection.get("independent_fair")
    if not isinstance(block, dict):
        raise OfflineIfCallerReject(REJECT_BLEND, "Independent Fair block missing")
    blend = block.get("market_blend")
    if blend is True or blend != 0:
        raise OfflineIfCallerReject(
            REJECT_BLEND, f"IF market_blend must be exact 0, got {blend!r}"
        )
    diagnostics = projection.get("diagnostics")
    if isinstance(diagnostics, dict):
        market = diagnostics.get("market_blend")
        if isinstance(market, dict):
            spread_weight = market.get("spread_weight")
            total_weight = market.get("total_weight")
            if spread_weight not in (None, 0, 0.0) or total_weight not in (
                None,
                0,
                0.0,
            ):
                raise OfflineIfCallerReject(
                    REJECT_BLEND,
                    f"diagnostics market weights must be 0, got spread={spread_weight} total={total_weight}",
                )
    if projection.get("forecast_label") != INDEPENDENT_FAIR_FORECAST_LABEL:
        raise OfflineIfCallerReject(
            REJECT_BLEND, "IF path failed to label forecast_label=independent_fair"
        )
    return 0


def _forbid_e1_label(payload: Mapping[str, Any]) -> None:
    forbidden = (
        payload.get("e1"),
        payload.get("e1_admissible"),
        payload.get("e1_label"),
        payload.get("scoring_admissible"),
        payload.get("admissible_e1"),
    )
    if any(flag is True for flag in forbidden):
        raise OfflineIfCallerReject(
            REJECT_E1, "caller must not label output as admissible E1"
        )
    if str(payload.get("forecast_class") or "") in {"E1", "ADMISSIBLE", "O4"}:
        raise OfflineIfCallerReject(
            REJECT_E1, "caller must not classify output as E1/O4 admissible"
        )


def invoke_independent_fair(
    request: OfflineIfRequest,
    *,
    through_w8_path: Path = THROUGH_W8_ACCEPT_PATH,
    simulator_path: Path = SIMULATOR_PY,
    asof_path: Path = ASOF_PY,
) -> Dict[str, Any]:
    """Real non-test invocation path. Fail-closed. Never E1-admissible here."""
    if request.mode != CALLER_MODE_OPERATIONAL:
        raise OfflineIfCallerReject(
            REJECT_E1, "invoke_independent_fair is operational-only (no dry-run bypass)"
        )
    source_sha = verify_source_pin(simulator_path=simulator_path)
    asof_sha = verify_asof_module(asof_path=asof_path)
    w8 = require_through_w8_data_accept(through_w8_path)
    require_target_identifiers(request)
    reject_sportsbook(request.extra)
    rating_week = enforce_asof_and_history(request)
    inputs = build_contract_inputs(request)
    projection = simulate_nfl_game_independent_fair(
        inputs,
        simulations=request.simulations,
        seed=request.seed,
        market_spread_home=None,
        market_total=None,
    )
    blend = _assert_if_blend_zero(projection)
    wrapped = {
        "caller_id": CALLER_ID,
        "mode": CALLER_MODE_OPERATIONAL,
        "forecast_class": FORECAST_CLASS_NONE,
        "e1": False,
        "e1_admissible": False,
        "e1_label": None,
        "scoring_admissible": False,
        "independent_fair_invoked": True,
        "market_blend": blend,
        "rating_week": rating_week,
        "source_pin_sha256": source_sha,
        "asof_module_sha256": asof_sha,
        "through_w8": w8,
        "projection": projection,
    }
    _forbid_e1_label(wrapped)
    return wrapped


def synthetic_wiring_request() -> OfflineIfRequest:
    """Deterministic synthetic row. Not a 2026 W8/W9 game. Not E1."""
    efficiency = {
        "offense_index_home": 1.04,
        "offense_index_away": 0.97,
        "defense_index_home": 0.99,
        "defense_index_away": 1.03,
        "home_off_epa_5g": 0.04,
        "away_off_epa_5g": -0.02,
        "home_def_epa_allowed_5g": -0.01,
        "away_def_epa_allowed_5g": 0.03,
        "home_pass_rate_5g": 0.58,
        "away_pass_rate_5g": 0.55,
        "home_success_offense_5g": 0.46,
        "away_success_offense_5g": 0.43,
        "home_success_defense_allowed_5g": 0.44,
        "away_success_defense_allowed_5g": 0.45,
        "matchup_diff_off_epa_5g": 0.06,
        "matchup_diff_def_epa_allowed_5g": 0.04,
        "matchup_diff_success_rate_5g": 0.02,
        "matchup_diff_pressure_generated_5g": 0.01,
        "matchup_diff_pressure_allowed_5g": -0.01,
        "matchup_diff_red_zone_td_rate_5g": 0.03,
    }
    history = tuple(
        {
            "week": week,
            "game_id": f"SYN-2099-{week:02d}",
            "game_date": f"2099-09-{week:02d}",
            "kickoff_ts": f"2099-09-{week:02d}T17:00:00Z",
        }
        for week in (4, 5, 6, 7, 8)
    )
    return OfflineIfRequest(
        game_id=DRY_RUN_GAME_ID,
        home_team="SYN",
        away_team="OPP",
        matchup_season=2099,
        matchup_week=9,
        rest_days_home=7.0,
        rest_days_away=7.0,
        forecast_cutoff_ts=DRY_RUN_CUTOFF,
        rating_week=8,
        available_rating_weeks=(4, 5, 6, 7, 8),
        history_games=history,
        efficiency=efficiency,
        extra={},
        mode=CALLER_MODE_DRY_RUN,
        simulations=DRY_RUN_SIMULATIONS,
        seed=DRY_RUN_SEED,
    )


def wiring_probe(request: Optional[OfflineIfRequest] = None) -> Dict[str, Any]:
    """Invoke IF on a synthetic row to prove wiring. Never E1-admissible."""
    req = request or synthetic_wiring_request()
    if req.mode != CALLER_MODE_DRY_RUN:
        raise OfflineIfCallerReject(
            REJECT_E1, "wiring_probe requires dry_run_wiring mode"
        )
    source_sha = verify_source_pin()
    asof_sha = verify_asof_module()
    require_target_identifiers(req)
    reject_sportsbook(req.extra)
    rating_week = enforce_asof_and_history(req)
    inputs = build_contract_inputs(req)
    projection = simulate_nfl_game_independent_fair(
        inputs,
        simulations=req.simulations,
        seed=req.seed,
        market_spread_home=None,
        market_total=None,
    )
    blend = _assert_if_blend_zero(projection)
    margin_mu, total_mu = independent_fair_mus(projection)
    probe = {
        "caller_id": CALLER_ID,
        "mode": CALLER_MODE_DRY_RUN,
        "forecast_class": FORECAST_CLASS_WIRING_ONLY,
        "e1": False,
        "e1_admissible": False,
        "e1_label": None,
        "scoring_admissible": False,
        "independent_fair_invoked": True,
        "market_blend": blend,
        "rating_week": rating_week,
        "source_pin_sha256": source_sha,
        "asof_module_sha256": asof_sha,
        "game_id": req.game_id,
        "matchup_season": req.matchup_season,
        "matchup_week": req.matchup_week,
        "simulations": req.simulations,
        "seed": req.seed,
        "margin_mu": margin_mu,
        "total_mu": total_mu,
        "note": (
            "Synthetic dry-run wiring probe only. Not an admissible E1 forecast. "
            "Not a 2026 slate row. Do not score, publish, or merge as emit."
        ),
    }
    _forbid_e1_label(probe)
    probe["digest"] = canonical_sha256(
        {
            "game_id": probe["game_id"],
            "market_blend": probe["market_blend"],
            "margin_mu": probe["margin_mu"],
            "total_mu": probe["total_mu"],
            "seed": probe["seed"],
            "simulations": probe["simulations"],
            "forecast_class": probe["forecast_class"],
            "e1_admissible": probe["e1_admissible"],
        }
    )
    return probe


def remaining_owner_e1_clear_conditions() -> list[Dict[str, str]]:
    return [
        {
            "id": "W8_DATA_READY",
            "status": "OPEN",
            "detail": (
                "Cursor: re-fetch+archive PBP + pin fetched_at_utc → rebuild "
                "through-W8 panel → seal DATA_READY (O-a…O-d). Current W8="
                f"{W8_STATUS} {W8_COMPLETE} tip {W8_TIP} #{W8_PR} IMV "
                f"{W8_IMV_PARTIAL}. Do not invent W8. Do not delay that lane."
            ),
        },
        {
            "id": "IMV_THROUGH_W8_DATA_ACCEPT",
            "status": "OPEN",
            "detail": (
                f"IMV through-W8 DATA ACCEPT vs contract {CONTRACT_SHA8}. "
                f"{PASS_CONTRACT_NOTE}."
            ),
        },
        {
            "id": "OWNER_E1_CLEAR",
            "status": "OPEN",
            "detail": (
                "OWNER / CoS CLEAR for first scoring-admissible E1 emit after "
                "W8 DATA_READY + IMV ACCEPT + caller technical checks. "
                "Path: W8 DATA_READY → IMV ACCEPT → OWNER E1 CLEAR → first "
                "verified IF forecast. This packet is not that CLEAR."
            ),
        },
        {
            "id": "NO_SAME_WEEK_LEAKAGE",
            "status": "HELD_BY_ASOF",
            "detail": (
                f"Keep PASS_ASOF_BOUNDARY {ASOF_BOUNDARY_SHA8} (tip {ASOF_TIP}) "
                "as the as-of identity, distinct from SOURCE ONLY 52d9e909. "
                "rating_week = target_week - 1; no sportsbook; IF(blend=0)."
            ),
        },
    ]


def evaluate_caller(
    request: Optional[OfflineIfRequest] = None,
    *,
    through_w8_path: Path = THROUGH_W8_ACCEPT_PATH,
    write: bool = False,
) -> OfflineIfResult:
    """Operational evaluate. Fail-closed. Writes BLOCKED/CALLER_READY packet."""
    codes: list[str] = []
    messages: list[str] = []
    invoked = False
    blend: Optional[int] = None
    wiring = None
    pins = lineage_pins()
    try:
        source_sha = verify_source_pin()
        asof_sha = verify_asof_module()
    except OfflineIfCallerReject as exc:
        source_sha = None
        asof_sha = None
        codes.append(exc.code)
        messages.append(exc.message)
    w8 = load_through_w8_accept(through_w8_path)
    if not w8.get("data_accept"):
        codes.append(REJECT_THROUGH_W8)
        messages.append(
            "through-W8 DATA ACCEPT missing "
            f"(status={w8.get('status')}; W8={W8_STATUS} {W8_COMPLETE})"
        )

    if request is not None and not codes:
        try:
            invoked_payload = invoke_independent_fair(
                request, through_w8_path=through_w8_path
            )
            invoked = True
            blend = invoked_payload["market_blend"]
        except OfflineIfCallerReject as exc:
            codes.append(exc.code)
            messages.append(exc.message)

    # Wiring probe is separate from operational emit and cannot clear E1.
    try:
        wiring = wiring_probe()
    except OfflineIfCallerReject as exc:
        codes.append(f"WIRING_{exc.code}")
        messages.append(exc.message)

    blocked = True
    # CALLER_READY only if engineering gates hold AND through-W8 ACCEPT is present.
    # Today ACCEPT is absent → BLOCKED. Wiring success does not ungate E1.
    engineering_pass = (
        source_sha == IF_SOURCE_PIN_SHA256
        and asof_sha == ASOF_MODULE_SHA256
        and wiring is not None
        and wiring.get("market_blend") == 0
        and wiring.get("e1_admissible") is False
    )
    status = "BLOCKED"
    if engineering_pass and w8.get("data_accept") and not codes:
        status = "CALLER_READY"
        blocked = False
    elif engineering_pass:
        status = "BLOCKED"
        blocked = True

    impl_files = [
        Path(__file__),
        ASOF_PY,
        SIMULATOR_PY,
        REPO_ROOT / "scripts" / "nfl" / "run_offline_if_caller_t4838u.py",
    ]
    impl_sha = canonical_sha256(
        {
            str(path.relative_to(REPO_ROOT)): sha256_file(path)
            for path in impl_files
            if path.is_file()
        }
    )
    evidence = {
        "caller_id": CALLER_ID,
        "decision_sha256": DECISION_SHA256,
        "cos_order_sha256": COS_ORDER_SHA256,
        "implementation_sha256": impl_sha,
        "data_identity": {
            "through_w8": w8,
            "w8_status": W8_STATUS,
            "w8_complete": W8_COMPLETE,
            "w8_tip": W8_TIP,
            "contract": CONTRACT_SHA8,
            "pass_contract": PASS_CONTRACT_SHA8,
            "source_pin": IF_SOURCE_PIN_SHA8,
            "as_of": ASOF_BOUNDARY_SHA8,
            "as_of_module": ASOF_MODULE_SHA256,
            "lineages_distinct": True,
        },
        "configuration": {
            "if_blend": 0,
            "sportsbook": False,
            "unapproved_hl": False,
            "e1_emit": False,
            "railway_required": False,
            "c10_required": False,
            "mode_operational_fail_closed": True,
        },
        "execution_path": {
            "module": "src.services.nfl_offline_if_caller",
            "cli": "scripts/nfl/run_offline_if_caller_t4838u.py",
            "if_entrypoint": "simulate_nfl_game_independent_fair",
            "asof_module": "src.services.nfl_pregame_asof",
            "contract": CONTRACT_SHA8,
            "production_routes": False,
            "tasks_py": False,
        },
        "pins": pins,
    }
    packet = {
        "status": status,
        "blocked": blocked,
        "caller_engineering": "PASS" if engineering_pass else "FAIL",
        "e1_admissible": False,
        "e1_emit": False,
        "codes": codes,
        "messages": messages,
        "independent_fair_invoked_operational": invoked,
        "market_blend": blend if invoked else (wiring or {}).get("market_blend"),
        "forecast_class": (
            FORECAST_CLASS_NONE if invoked else FORECAST_CLASS_WIRING_ONLY
        ),
        "remaining_conditions_for_owner_e1_clear": remaining_owner_e1_clear_conditions(),
        "evidence_sha256": canonical_sha256(evidence),
        "wiring_digest": None if wiring is None else wiring.get("digest"),
        "pins": pins,
        "locks": {
            "nfl": "NO-GO",
            "cert": 0,
            "coming_soon": "ON",
            "f2": "frozen",
            "c10": "HOLD",
            "odds": "HOLD",
        },
    }
    result = OfflineIfResult(
        blocked=blocked,
        status=status,
        codes=codes,
        messages=messages,
        independent_fair_invoked=invoked,
        forecast_class=packet["forecast_class"],
        e1_admissible=False,
        market_blend=packet["market_blend"],
        evidence=evidence,
        wiring=wiring,
    )
    if write:
        _write_sealed_outputs(packet, evidence, wiring)
    return result


def render_packet_markdown(packet: Mapping[str, Any]) -> str:
    remaining = packet.get("remaining_conditions_for_owner_e1_clear") or []
    lines = [
        "# CALLER PACKET t4838u — offline Independent Fair",
        "",
        f"**Status:** `{packet.get('status')}`",
        f"**Caller engineering:** `{packet.get('caller_engineering')}`",
        f"**E1 admissible:** `{packet.get('e1_admissible')}`",
        f"**E1 emit:** `{packet.get('e1_emit')}`",
        f"**IF(blend):** `{packet.get('market_blend')}`",
        "",
        "Authority: DECISION_RYAN_t4838u "
        f"`{DECISION_SHA256}` · COS_ORDER `{COS_ORDER_SHA256}`.",
        "",
        "Lineages (distinct):",
        f"- SOURCE ONLY `52d9e909` @ `1b39f4e9` ratified `75d1b695`",
        f"- ASOF `PASS_ASOF_BOUNDARY cf514078` tip `1010b86f` module `7dc6afea`",
        f"- CONTRACT `b41f4b43` / PASS_CONTRACT `1a53bbd3` ≠ DATA ACCEPT",
        f"- W8 `{W8_STATUS}` `{W8_COMPLETE}` tip `{W8_TIP}` #663 — not invented",
        "",
        "Codes:",
    ]
    for code in packet.get("codes") or []:
        lines.append(f"- `{code}`")
    lines.extend(["", "Remaining conditions for first OWNER E1 CLEAR:", ""])
    for item in remaining:
        lines.append(
            f"- **{item['id']}** ({item['status']}): {item['detail']}"
        )
    lines.extend(
        [
            "",
            "≠E1 emit ≠admit ≠merge ≠C10 exit ≠Odds ≠CERT ≠subscriber "
            "≠historical rescoring ≠model fit.",
            "",
            "NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10/Odds HOLD.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_sealed_outputs(
    packet: Mapping[str, Any],
    evidence: Mapping[str, Any],
    wiring: Optional[Mapping[str, Any]],
) -> None:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    PACKET_JSON_PATH.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    PACKET_MD_PATH.write_text(render_packet_markdown(packet), encoding="utf-8")
    if wiring is not None:
        DRY_RUN_PATH.write_text(
            json.dumps(wiring, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def request_from_mapping(raw: Mapping[str, Any]) -> OfflineIfRequest:
    return OfflineIfRequest(
        game_id=str(raw.get("game_id") or ""),
        home_team=str(raw.get("home_team") or ""),
        away_team=str(raw.get("away_team") or ""),
        matchup_season=raw.get("matchup_season"),  # type: ignore[arg-type]
        matchup_week=raw.get("matchup_week"),  # type: ignore[arg-type]
        rest_days_home=raw.get("rest_days_home"),  # type: ignore[arg-type]
        rest_days_away=raw.get("rest_days_away"),  # type: ignore[arg-type]
        forecast_cutoff_ts=str(raw.get("forecast_cutoff_ts") or ""),
        rating_week=raw.get("rating_week"),
        available_rating_weeks=raw.get("available_rating_weeks"),
        history_games=tuple(raw.get("history_games") or ()),
        efficiency=dict(raw.get("efficiency") or {}),
        extra=dict(raw.get("extra") or {}),
        mode=str(raw.get("mode") or CALLER_MODE_OPERATIONAL),
        simulations=int(raw.get("simulations") or 4000),
        seed=raw.get("seed"),
    )
