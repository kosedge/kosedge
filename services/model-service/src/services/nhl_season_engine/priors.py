"""NHL season-engine priors (Ch1–Ch2 + Ch5 residual cap).

NHL_TEAM_CARRY_SHRINK is NHL-named — do not import or alias NBA/WNBA shrink.
Ch1 shrinks 2025–26 team GF/GA. Ch2 builds TOI grid + goalie tandem — no emit.
Ch5 PlayerProjection uses NHL_TEAM_REBASE_RESIDUAL_CAP for ΣG identity.
Do not retune NHL_TEAM_CARRY_SHRINK in Ch2/Ch5.
"""

from __future__ import annotations

ENGINE_VERSION = "nhl-season-engine-v0.1"

# Shrink 2025–26 team box toward league mean (Ch1 shell).
# Paper-sim set {0.70, 0.80, 0.85, 0.90}; chosen 0.85. Do not retune in Ch2.
NHL_TEAM_CARRY_SHRINK = 0.85

PAPER_SIM_S_SET = (0.70, 0.80, 0.85, 0.90)

# Ch0 register — player talent year labels (2023 / 2024 / 2025 ≈ 23–24 / 24–25 / 25–26).
PLAYER_YEAR_WEIGHTS = {
    "2023": 0.20,
    "2024": 0.30,
    "2025": 0.50,
}

# Ch2 — same weights keyed by NHL seasonId.
PLAYER_YEAR_WEIGHTS_BY_SEASON_ID = {
    20232024: 0.20,
    20242025: 0.30,
    20252026: 0.50,
}

# Ch2 identity: 5 skaters on ice × 60 minutes. Shares always sum to 1.0;
# toi_min = share × NHL_TOI_GRID_SKATER_MINUTES (optional display).
NHL_TOI_GRID_SKATER_MINUTES = 300.0
NHL_GOALIE_TANDEM_SHARE_SUM = 1.0

# Ch5 — |Σ skater G − team GF/G| after identity scale (per-game).
# ~3% of league GF/G (~3.1) ≈ 0.10; pad to 0.15. Do not retune 0.85 for this.
NHL_TEAM_REBASE_RESIDUAL_CAP = 0.15

PROP_PLAY_CAP_PER_SLATE = 6
ODDS_SPORT_KEY = "icehockey_nhl"
STARTER_GATE = "unknown"  # unknown starter → no goalie PLAY (later chapters)
