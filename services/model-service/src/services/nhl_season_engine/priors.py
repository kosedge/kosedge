"""NHL season-engine priors (Chapter 1 shell).

NHL_TEAM_CARRY_SHRINK is NHL-named — do not import or alias NBA/WNBA shrink.
Ch1 shrinks 2025–26 team GF/GA toward league mean for the 2026–27 shell.
Ch2 is TOI grid + goalie tandem — not this module.
"""

from __future__ import annotations

ENGINE_VERSION = "nhl-season-engine-v0.1"

# Shrink 2025–26 team box toward league mean (Ch1 shell).
# Paper-sim set {0.70, 0.80, 0.85, 0.90}; chosen 0.85. Do not retune in Ch2.
NHL_TEAM_CARRY_SHRINK = 0.85

PAPER_SIM_S_SET = (0.70, 0.80, 0.85, 0.90)

# Register only (Ch0) — not used in Ch1 pack emit.
PLAYER_YEAR_WEIGHTS = {
    "2023": 0.20,
    "2024": 0.30,
    "2025": 0.50,
}
PROP_PLAY_CAP_PER_SLATE = 6
ODDS_SPORT_KEY = "icehockey_nhl"
STARTER_GATE = "unknown"  # unknown starter → no goalie PLAY (later chapters)
