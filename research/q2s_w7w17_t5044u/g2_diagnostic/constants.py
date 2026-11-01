"""Frozen pins + protocol constants for t5075u G2. CERT=0."""

from __future__ import annotations

from pathlib import Path

G2 = Path(__file__).resolve().parent
PACKET = G2.parent
JOINT = PACKET / "joint"

PROTOCOL_ID = "g2-diagnostic-t5075u-v1"
NAMESPACE = "research.q2s.g2_diagnostic"
LABEL = "RETRO_FIT / DEV_RESEARCH"
CERT = 0
NFL = "NO-GO"
TICKET = "t5075u"
CONSUME_HEAD = "43b5a62233b3d1d03ad2b25f5ec7dc52be29b31b"
CONSUME_HEAD_SHA8 = "43b5a622"

N_GAMES = 141
N_DRAWS = 4000
N_T2_SEALED = 24
N_WEEK_BLOCKS = 11
WEEK_BLOCKS = tuple(range(7, 18))
ELIGIBLE_SEASON = 2017
PROTECTED_SEASONS = frozenset({2024, 2025})
OTHER_EVAL_SEASONS = frozenset({2018, 2019, 2020, 2021, 2022})
Q2_EVAL_CLOSED = "03a4dd90"

# Log-loss clip — predeclared. Originals retained.
LOGLOSS_N = N_DRAWS
LOGLOSS_EPS = 1.0 / (2.0 * LOGLOSS_N)  # 1/8000 = 0.000125

COVERAGE_LEVELS = (0.50, 0.80, 0.90)

JOINT_JSON_SHA256 = (
    "5076421ef1fba943df9c1e8eeaefede4f7a7e30a36ae2ed792a7f2bc295c4e27"
)
JOINT_NPZ_SHA256 = (
    "ce6b1244895df065ea8428851261becbb8012c7379d6184770116a7dfbcb0fc5"
)
IF_MUS_SHA256 = (
    "32e9743483259f2a9c13efe9826e550f610a6068995fad3bc9fdb6b1698d5d43"
)
Q2S_ROWS_SHA256 = (
    "55d8c8bc2155705c04e9ef88ba5637ea491bf5c245e4f7bb8fcfb3523f9ec925"
)
OUTCOMES_SHA256 = (
    "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081"
)
LOOK_CONSUMED_SHA256 = (
    "013d270a815511ebe6a77dc559eb2e2df47c47670c9dfc6b1f2a0f0193a46331"
)

LOOK_TIP = "8bea4ca3"
ACCEPT_TIP = "bd51eb3e"
LOOK_CONSUMED_SHA8 = "013d270a"
Q2_EVAL_TIP = "03a4dd90"

JOINT_JSON_PATH = JOINT / "artifacts" / "Q2S_JOINT_W7W17.json"
JOINT_NPZ_PATH = JOINT / "artifacts" / "Q2S_JOINT_DRAWS_W7W17.npz"
IF_MUS_PATH = PACKET / "phase4" / "artifacts" / "IF_MUS_W7W17.json"
Q2S_ROWS_PATH = PACKET / "phase4" / "artifacts" / "q2s_rows_w7w17.json"
OUTCOMES_PATH = PACKET / "pins" / "outcomes_2013_2022_score_only.csv"
LOOK_CONSUMED_PATH = PACKET / "phase4" / "artifacts" / "LOOK_CONSUMED.json"

PROTOCOL_PATH = G2 / "PROTOCOL.md"
MANIFEST_PATH = G2 / "FROZEN_MANIFEST.json"
MANIFEST_SHA_PATH = G2 / "FROZEN_MANIFEST.json.sha256"
ALEX_GO_PATH = G2 / "ALEX_PRECOMPUTE_GO.json"
RESULTS_PATH = G2 / "artifacts" / "G2_DIAGNOSTIC_RESULT.json"
CURSOR_DONE_PATH = G2 / "CURSOR_DONE.md"
BLOCKER_PATH = G2 / "BLOCKER.json"

UNAVAILABLE = "UNAVAILABLE"

IF_DIST_NOTE = (
    "IF_MUS is means-only (no persisted draw arrays). "
    "IF distribution comparison is UNAVAILABLE. Do not regenerate."
)
POINT_TOTAL_NOTE = (
    "Point-candidate is a margin blend only; no persisted total mean."
)
POINT_WP_NOTE = (
    "q2s rows set no_candidate_probabilities=true; no persisted candidate WP."
)
LEGACY_WP_NOTE = (
    "IF if_forecast_wp_home is persisted at legacy 4-decimal rounding. "
    "Joint home_wp is persisted as #(D>0)/N; forecast-side D=0 counts away."
)

CLAIM_KEYS = ("pass", "edge", "retune", "selection", "play", "lean")

FORBIDDEN_RESULT_TOKENS = (
    "FQ PASS",
    "NOT FQ PASS",
    "PLAY",
    "LEAN",
    "EDGE_CLAIM",
    "RETUNE",
    "SELECT_CANDIDATE",
)
