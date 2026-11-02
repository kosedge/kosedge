"""Frozen pins for t5208u R6_CALLER_V1. Do not invent fields or coeffs."""

from __future__ import annotations

from src.services.nfl_t5107u.recon_contract import CONTRACT_27 as _RECON_CONTRACT_27

PACKAGE = "t5208u"
ROLE = "A_PURE_CALLER"
CERT = 0
SCHEMA_ID = "nfl-t5208u-r6-caller-v1"
OUTPUT_KIND = "POINT_MARGIN"
C_FORMULA = "C=0.5*IF+0.5*Q2"
CHANNEL_SYNTHETIC = "SYNTHETIC"
PURE_SOURCE_TIP = "455a8e43eccc1ed2c39e91821790cce968ffdadb"
IF_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"
SIM_SHA256 = "52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385"
FW_SHA256 = "a0051cc423bd733c3342272fdb297ea8f22cf2a4569fe0f9ca0ec47eda04d0e3"
OWNER_CLEAR_SHA8 = "84308754"
COS_LAUNCH_SHA8 = "a0a88a33"

# Literal 27-field tuple frozen from recon_contract.py@455a8e43.
CONTRACT_27 = (
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
if CONTRACT_27 != _RECON_CONTRACT_27:
    raise RuntimeError("CONTRACT_27 drifted from recon_contract.py@455a8e43")

# From r5_496_freeze.py@455a8e43 (algorithm constant only; module not imported).
CANDIDATE_WEIGHT = 0.5
KO_MINUS_MINUTES = 60
REPLAY_REL = 1e-9

# if_produce.py@455a8e43
SIMULATIONS = 4000
SEED_BASE = 201710
SEED_MOD = 1000003
MARKET_BLEND = 0

# q2.py@455a8e43
A_Q2 = 2.5637441292077354
B_Q2 = 1.660624056183471
RIDGE = 20.0
PRIOR_CARRY = 0.5
INITIAL_PRIOR = None  # None@2013; 2013–16 transfer coeffs unchanged

ENVELOPE_FIELDS = (
    "game_id",
    "season",
    "week",
    "season_type",
    "home_team",
    "away_team",
    "kickoff_utc",
    "venue_id",
    "identity_kind",
)
CELL_META_FIELDS = (
    "status",
    "reconstructed_value",
    "source",
    "available_at",
    "observed_at",
    "source_byte_hash",
)
FORBIDDEN_OUTPUT_KEYS = (
    "moneyline",
    "ml",
    "total",
    "totals",
    "probability",
    "prob",
    "brier",
    "log_loss",
    "joint",
    "sim_q2s_joint",
    "play",
    "lean",
    "stake",
)
DEFAULT_IF_TREES = (
    "/tmp/t5108u-if-6ca03716",
    "/tmp/t5044u-if-6ca03716",
    "/tmp/t4910u-if-6ca03716",
)
ALLOWED_ALGO_MODULES = (
    "if_produce",
    "q2",
    "builder",
    "recon_contract",
    "if_control",
)
