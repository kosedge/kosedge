"""Frozen pins for t5289u R7_CORRECTNESS_V1. CERT=0. Do not invent coeffs."""

from __future__ import annotations

from src.services.nfl_t5107u.q2 import PRIOR_ALIAS
from src.services.nfl_t5208u.pins import (
    CONTRACT_27,
    C_FORMULA,
    FW_SHA256,
    IF_TIP,
    SIM_SHA256,
)

PACKAGE = "R7_CORRECTNESS_V1"
ROLE = "A_INTEGRATION"
CERT = 0
SCHEMA_ID = "nfl-t5289u-r7-correctness-v1"
OWNER_CLEAR = "86257"
AUTHORITY = "t5289u"
SCOPE_ID = "chief-nflgreen-model-day-20261103-1700"
PLAN_FINGERPRINT = "b15d6cec143212067b896057a048cd51071981d6ea1b3561c08db89cb6355358"
WINDOW_EST = "2026-11-03 09:00-17:00 EST"
HARD_STOP_UTC = "2026-11-03T22:00:00Z"

R6_A_TIP = "54b08a301cf824c79ee3203180a51e2d832bb6f9"
R6_B_TIP = "afb13301b5c7e3b8780a8dd1f85145e91bebef55"
GATE_713_TIP = "679dbdaf8c9044edffb34ffca1543c33eea77db7"
PR_714_TIP = "5558890b5f8a66c16c658fce2971f0a7e2f2c7de"
PR_714_STATUS = "PARTIAL_NOT_WHOLESALE_BASE"
BASE_DEPLOY_VERCEL = "f5e3bb58ccbe5a8892fed2a01f347c2308394a2f"

CALENDAR_ID = "REST_ACTUAL_ET_CALENDAR_V1"
CALENDAR_TZ = "America/New_York"

# Franchise keys frozen to Q2 PRIOR_ALIAS plus product aliases. No new source.
FRANCHISE_ALIASES = {
    "LA": "LAR",
    "LAR": "LAR",
    "STL": "LAR",
    "SD": "LAC",
    "LAC": "LAC",
    "OAK": "LV",
    "LV": "LV",
    "WSH": "WAS",
    "WAS": "WAS",
    "JAC": "JAX",
    "JAX": "JAX",
}
if PRIOR_ALIAS.get("STL") != "LAR" or PRIOR_ALIAS.get("SD") != "LAC" or PRIOR_ALIAS.get("OAK") != "LV":
    raise RuntimeError("Q2 PRIOR_ALIAS drifted from frozen franchise keys")

CHANNEL_SYNTHETIC = "SYNTHETIC"
OUTPUT_KIND = "POINT_MARGIN"
KO_MINUS_MINUTES = 60

WORKER_A_ID = "bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8"
WORKER_B_ID = "bc-02a716be-429a-56c8-ab0f-5f262aa479df"

EXPECTED_COMMAND = (
    "PYTHONPATH=services/model-service python3 scripts/nfl/run_nfl_r7_correctness_v1.py"
)

CODE_FILES = (
    "services/model-service/src/services/nfl_r7_correctness_v1/pins.py",
    "services/model-service/src/services/nfl_r7_correctness_v1/calendar.py",
    "services/model-service/src/services/nfl_r7_correctness_v1/franchise.py",
    "services/model-service/src/services/nfl_r7_correctness_v1/packets.py",
    "services/model-service/src/services/nfl_r7_correctness_v1/produce.py",
    "services/model-service/src/services/nfl_r7_correctness_v1/consume_b.py",
    "services/model-service/src/services/nfl_r7_correctness_v1/recorder.py",
    "services/model-service/src/services/nfl_r7_correctness_v1/run.py",
    "services/model-service/src/services/nfl_ops_v1_evidence/profiles.py",
    "services/model-service/src/services/nfl_ops_v1_evidence/validate_r7.py",
)

OPS_REL = "data/ops/t5289u-r7-correctness-v1"

__all__ = [
    "AUTHORITY",
    "BASE_DEPLOY_VERCEL",
    "CALENDAR_ID",
    "CALENDAR_TZ",
    "CERT",
    "CHANNEL_SYNTHETIC",
    "CODE_FILES",
    "CONTRACT_27",
    "C_FORMULA",
    "EXPECTED_COMMAND",
    "FRANCHISE_ALIASES",
    "FW_SHA256",
    "GATE_713_TIP",
    "HARD_STOP_UTC",
    "IF_TIP",
    "KO_MINUS_MINUTES",
    "OPS_REL",
    "OUTPUT_KIND",
    "OWNER_CLEAR",
    "PACKAGE",
    "PLAN_FINGERPRINT",
    "PR_714_STATUS",
    "PR_714_TIP",
    "R6_A_TIP",
    "R6_B_TIP",
    "ROLE",
    "SCHEMA_ID",
    "SCOPE_ID",
    "SIM_SHA256",
    "WORKER_A_ID",
    "WORKER_B_ID",
]
