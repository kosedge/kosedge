"""nfl-model-forecast-artifact-v1 — schema constants and dest policy.

CERT_CANDIDATE is hard-locked at 0. RESEARCH/ENG only.
Not a prospective Odds seal. Does not reopen NFL public numbers.

Alex forecast eval-record paper ACCEPTED sha8 ``f1fa86e7`` is the
field contract (G1–G8). Missing a required gap → fail-closed reject.
"""

from __future__ import annotations

SCHEMA_VERSION = "nfl-model-forecast-artifact-v1"
CERT_CANDIDATE = 0
SPORT = "nfl"
PURPOSE = "research_eng_only"
LABEL = "RESEARCH_ENG"
SEAL_BINDING_STATUS_UNBOUND = "unbound"
EVAL_RECORD_PAPER_SHA8 = "f1fa86e7"

# Later join key for a prospective seal. Binding is a hook, not a seal write.
SEAL_BIND_HOOK = "game_id + forecast_ts_utc + record_sha256"

MODEL_IDENTITY_SEASON_ENGINE = "nfl-season-engine"

# G1 — home spread: negative = home favored (same as model_markets / KEI).
SPREAD_ORIENTATION = "home"
SPREAD_SIGN_CONVENTION = "home_negative_favored"
GAME_ID_FORMAT = "YYYY-Www-AWAY@HOME"

# G7 — reserved empty; emitter must never populate close.
CLOSE_ANCHOR_RESERVED = {
    "status": "reserved_empty",
    "close_spread_home": None,
    "close_total": None,
    "close_ml_home": None,
    "close_captured_at": None,
    "close_source": None,
}
EMPTY_GRADES = {
    "ats": None,
    "ou": None,
    "su": None,
}

UNSET_TOKENS = frozenset({"unset", "UNSET", "null", "NULL", "none", "NONE", ""})

FORBIDDEN_CLOSE_KEYS = frozenset(
    {
        "close_spread",
        "close_spread_home",
        "close_total",
        "close_ml",
        "close_ml_home",
        "close_ml_away",
        "close_captured_at",
        "close_source",
        "close_anchor",
        "grade_ats",
        "grade_ou",
        "grade_su",
        "grades",
    }
)

REQUIRED_TOP_LEVEL = (
    "schema_version",
    "label",
    "cert_candidate",
    "purpose",
    "sport",
    "forecast_ts_utc",
    "emitted_at_utc",
    "game_id",
    "home_team",
    "away_team",
    "kickoff_utc",
    "lead_seconds",
    "pre_kickoff",
    "latest_input_as_of",
    "code_tip_sha",
    "config_sha256",
    "model",
    "markets",
    "orientation",
    "input_provenance",
    "grades",
    "close_anchor",
    "seal_binding",
    "eval_record_paper_sha8",
)

REQUIRED_MODEL_FIELDS = ("identity", "version")
REQUIRED_PROVENANCE_FIELDS = ("fingerprints",)
REQUIRED_MARKET_FIELDS = ("prediction", "ref_line", "ref_line_source")
MARKET_KEYS = ("spread", "total", "moneyline")

SECRET_KEY_TOKENS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
    "bearer",
    "credential",
    "odds_api",
    "oddsapikey",
)

# Refuse writes that would mutate W8 / holdout seal dests (#641 tip 385767a2).
SEAL_DEST_MARKERS = (
    "/seals/",
    "/seal/",
    "\\seals\\",
    "\\seal\\",
    "w8_first_seal",
    "w8_first_seal_b_t4525u",
    "w8_first_seal_b_t4525u_a896cfd0",
    ".seal.json",
    "seal_receipt",
)

FIRST_SEAL_SLUG = "w8_first_seal_b_t4525u_a896cfd0"
PR_641_TIP = "385767a2"
SCHEMA_PATH = (
    "services/model-service/src/services/nfl_model_forecast_emit/schema.py"
)
FILE_MODE_READONLY = 0o444
RECORD_SHA256_SUFFIX = ".record_sha256"
