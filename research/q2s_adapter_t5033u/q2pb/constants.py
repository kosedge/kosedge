"""Frozen windows, grids, and pins for Q2 Phase B t5009u (DEV_RESEARCH)."""

from __future__ import annotations

LABEL = "DEV_RESEARCH"
CERT = 0
TIP_ORDER = "dc78aa4e"
TIP_ACCEPT = "9c37d348"
TIP_DESIGN = "2702b295"
TIP_EVAL_SPEC = "349e081e"
TIP_GAMES = "4fe1cdd7"
TIP_ASOF_KICKOFF = "cf514078"
TIP_GATED_INDEX = "1ee90fac"
GATE_INDEX = "83646d78"
S1_KILL = "50f57195"
OWNER_CARD = "025d09ba"

DEV_SEASONS = (2013, 2014, 2015, 2016)
HISTORY_ONLY_SEASONS = (2017,)  # as-of carry into 2018; never fit / never EVAL-scored
EVAL_SEASONS = (2018, 2019, 2020, 2021, 2022)
RESERVE_SEASONS = (2023,)
SEALED_SEASONS = (2024, 2025)

EVAL_WEEKS = tuple(range(2, 18))  # REG W2–17
DEV_WEEKS = tuple(range(2, 18))

# Hyperparameter invention grid (DEV only). Selection: max Spearman ρ;
# tie-break min DEV MAE(pm_new, m) after the DEV OLS map.
LAMBDA_GRID = (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0)
REGRESS_GRID = (0.0, 0.25, 0.50, 0.75, 1.0)

DEV_RHO_EARLY_STOP = 0.10
EVAL_RHO_KEEP = 0.15

BOOT_B = 10000
BOOT_SEED = 4918

# Franchise identity for prior-season carry-over only (not a rating blend).
PRIOR_ALIAS = {
    "STL": "LAR",
    "SD": "LAC",
    "OAK": "LV",
}
PRIOR_ALIAS_REVERSE = {v: k for k, v in PRIOR_ALIAS.items()}

# games.csv 4fe1cdd7 has no score columns. Outcome join is score-only
# (season, week, home, away, home_score, away_score) for 2013–2022.
# Never load trailing_*/packaged_*/EPA/error/2023/2024/2025 from 1ee90fac.
OUTCOME_JOIN_NOTE = (
    "OUTCOME_JOIN_ONLY: games.csv tip 4fe1cdd7 has identity/kickoff/records "
    "but no home_score/away_score. Public finals for 2013–2022 were copied "
    "from the six identity+score columns of the gated hist file (tip 1ee90fac) "
    "after dropping every model/trailing/EPA/error column and every 2023–2026 "
    "row. This is not scored reuse of the hist index (gate 83646d78); Alex RO "
    "must confirm. 2023 reserve and 2024–25 sealed rows were never copied."
)

EXPECTED_GAMES_SHA256_PREFIX = "4fe1cdd7"
EXPECTED_GAMES_N = 2992
