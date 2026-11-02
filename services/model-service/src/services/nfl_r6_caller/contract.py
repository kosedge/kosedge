"""t5208u R6_CALLER_V1 — frozen pins + refuse enum (CERT=0).

Algorithm literals from #701 tip 455a8e43 (recon_contract / if_produce / q2).
Does not import nfl_t5107u orchestration, writers, or SEALED_SEASONS.
Does not open science data or run IF/Q2.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, Literal, Tuple

PACKAGE_ID = "t5208u-r6-caller-v1"
SCHEMA_VERSION = "r6-caller-v1"
ALGORITHM_TIP = "455a8e43eccc1ed2c39e91821790cce968ffdadb"
PRESERVE_PACKAGE = "8f3c5580"

# Scientific pins (OWNER CLEAR / if_produce.py@455a8e43 / q2.py@455a8e43)
IF_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"
SIM_SHA256 = "52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385"
FW_SHA256 = "a0051cc423bd733c3342272fdb297ea8f22cf2a4569fe0f9ca0ec47eda04d0e3"
SIMULATIONS = 4000
SEED_BASE = 201710
MARKET_BLEND = 0
A_Q2 = 2.5637441292077354
B_Q2 = 1.660624056183471
RIDGE_LAMBDA = 20.0
PRIOR_CARRY = 0.5
INITIAL_PRIOR = None
C_WEIGHT_IF = 0.5
C_WEIGHT_Q2 = 0.5

OUTPUT_KIND: Literal["POINT_MARGIN"] = "POINT_MARGIN"
SYNTHETIC_CHANNEL: Literal["SYNTHETIC"] = "SYNTHETIC"

# Paper protocol (document only — this CLEAR does not EXEC)
PAPER_SEAL_OFFSET_BEFORE_KICKOFF_MINUTES = 60  # KO−60
FIXTURE_KO_OFFSET_MINUTES = 90  # #664 fixture; do not mix

# CONTRACT_27 @ recon_contract.py@455a8e43 — frozen literal
CONTRACT_27: Tuple[str, ...] = (
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_red_zone_td_rate_5g",
)

PAIRED_ARMS: FrozenSet[str] = frozenset({"IF", "C"})


class R6RefuseCode:
    REFUSE_REAL_MODE = "REFUSE_REAL_MODE"
    REFUSE_DUPLICATE = "REFUSE_DUPLICATE"
    REFUSE_RACE = "REFUSE_RACE"
    REFUSE_PARTIAL = "REFUSE_PARTIAL"
    REFUSE_A_OUTPUT = "REFUSE_A_OUTPUT"
    REFUSE_SYNTHETIC = "REFUSE_SYNTHETIC"
    REFUSE_PIN = "REFUSE_PIN"
    REFUSE_FORMULA = "REFUSE_FORMULA"
    REFUSE_OUTPUT = "REFUSE_OUTPUT"
    REFUSE_IDENTITY = "REFUSE_IDENTITY"
    REFUSE_MISSING = "REFUSE_MISSING"
    REFUSE_VERSION = "REFUSE_VERSION"


class R6Refuse(Exception):
    """Hard refuse. No partial success object. No fabricated IF mean."""

    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        self.partial = False
        super().__init__(f"R6 HARD REFUSE [{code}] {reason}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "reason": self.reason,
            "partial": False,
            "package": PACKAGE_ID,
            "output_kind": OUTPUT_KIND,
        }


def expected_c_mean(if_mean: float, q2_mean: float) -> float:
    return C_WEIGHT_IF * float(if_mean) + C_WEIGHT_Q2 * float(q2_mean)


def pin_block() -> Dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "schema_version": SCHEMA_VERSION,
        "algorithm_tip": ALGORITHM_TIP,
        "preserve_package": PRESERVE_PACKAGE,
        "if_tip": IF_TIP,
        "sim_sha256": SIM_SHA256,
        "fw_sha256": FW_SHA256,
        "simulations": SIMULATIONS,
        "seed_base": SEED_BASE,
        "market_blend": MARKET_BLEND,
        "a_q2": A_Q2,
        "b_q2": B_Q2,
        "ridge_lambda": RIDGE_LAMBDA,
        "prior_carry": PRIOR_CARRY,
        "initial_prior": INITIAL_PRIOR,
        "c_formula": "0.5*IF+0.5*Q2",
        "c_weight_if": C_WEIGHT_IF,
        "c_weight_q2": C_WEIGHT_Q2,
        "output_kind": OUTPUT_KIND,
        "contract_27": list(CONTRACT_27),
        "paper_seal_offset_minutes": PAPER_SEAL_OFFSET_BEFORE_KICKOFF_MINUTES,
        "fixture_ko_offset_minutes": FIXTURE_KO_OFFSET_MINUTES,
        "real_mode_authorized": False,
    }
