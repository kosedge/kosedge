"""Team-level coaching / tendency profiles (v1.8).

Inspectable priors that nudge Layer-2 play-mix and red-zone pass preference
without replacing the four-layer hierarchy. Effects are intentionally modest
so BUF@KC sanity bands remain stable.

Profile fields
--------------
- ``pass_rate_bias`` — baseline pass-rate shift vs league (typical ±0.05)
- ``script_aggression`` — scales score/time script pass deltas (≈0.80–1.20)
- ``rz_pass_bias`` — red-zone pass preference vs the scripted RZ base (±0.04)
- ``early_down_pass_bias`` — additive early-down pass tilt (±0.025)
- ``two_minute_aggression`` — scales hurry-up when trailing late (≈0.80–1.20)

Profiles are curated priors for distinctive clubs + league-average defaults
for the rest. No heavy coach-year regressions — keep transparent and stable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from src.services.nfl_season_engine.types import ScriptDetail, TimeBucket

# Keep local to avoid import cycles with loaders / game_script.
_NFL_TEAMS = (
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
)

# ---------------------------------------------------------------------------
# Magnitude clamps — keep coaching overlays modest vs strength / script.
# ---------------------------------------------------------------------------
# v1.16: widen so coaching actually moves season pass volume (was ±0.035).
PASS_RATE_BIAS_CLAMP = (-0.055, 0.055)
SCRIPT_AGGRESSION_CLAMP = (0.80, 1.20)
RZ_PASS_BIAS_CLAMP = (-0.040, 0.040)
EARLY_DOWN_PASS_BIAS_CLAMP = (-0.025, 0.025)
TWO_MINUTE_AGGRESSION_CLAMP = (0.80, 1.20)

LEAGUE_DEFAULT_PROFILE_KWARGS: Dict[str, Any] = {
    "pass_rate_bias": 0.0,
    "script_aggression": 1.0,
    "rz_pass_bias": 0.0,
    "early_down_pass_bias": 0.0,
    "two_minute_aggression": 1.0,
    "label": "league_average",
    "source": "league_default",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class CoachingProfile:
    """Inspectable coaching identity for one franchise."""

    team: str
    pass_rate_bias: float = 0.0
    script_aggression: float = 1.0
    rz_pass_bias: float = 0.0
    early_down_pass_bias: float = 0.0
    two_minute_aggression: float = 1.0
    label: str = "league_average"
    source: str = "league_default"

    def clamped(self) -> "CoachingProfile":
        return CoachingProfile(
            team=self.team,
            pass_rate_bias=_clamp(self.pass_rate_bias, *PASS_RATE_BIAS_CLAMP),
            script_aggression=_clamp(self.script_aggression, *SCRIPT_AGGRESSION_CLAMP),
            rz_pass_bias=_clamp(self.rz_pass_bias, *RZ_PASS_BIAS_CLAMP),
            early_down_pass_bias=_clamp(
                self.early_down_pass_bias, *EARLY_DOWN_PASS_BIAS_CLAMP
            ),
            two_minute_aggression=_clamp(
                self.two_minute_aggression, *TWO_MINUTE_AGGRESSION_CLAMP
            ),
            label=self.label,
            source=self.source,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self.clamped())


# Curated priors for distinctive coaching identities.
# Values are small on purpose — overlays on top of Layer-1 pass_rate_bias
# and the v1.6 script response, not replacements.
_CURATED: Dict[str, Dict[str, Any]] = {
    # Andy Reid / Mahomes — pass-first, aggressive when trailing, RZ throwers.
    "KC": {
        "pass_rate_bias": 0.028,
        "script_aggression": 1.12,
        "rz_pass_bias": 0.030,
        "early_down_pass_bias": 0.018,
        "two_minute_aggression": 1.12,
        "label": "pass_aggressive",
        "source": "curated_prior",
    },
    # Buffalo — efficient pass tilt, push tempo when chasing.
    "BUF": {
        "pass_rate_bias": 0.018,
        "script_aggression": 1.10,
        "rz_pass_bias": 0.015,
        "early_down_pass_bias": 0.010,
        "two_minute_aggression": 1.10,
        "label": "pass_aggressive",
        "source": "curated_prior",
    },
    # Shanahan — early-down run identity, GL run lean, measured chase.
    "SF": {
        "pass_rate_bias": -0.022,
        "script_aggression": 0.90,
        "rz_pass_bias": -0.028,
        "early_down_pass_bias": -0.020,
        "two_minute_aggression": 0.95,
        "label": "run_scheme",
        "source": "curated_prior",
    },
    # Sirianni / Hurts — protect leads on ground, modest chase aggression.
    "PHI": {
        "pass_rate_bias": -0.025,
        "script_aggression": 0.92,
        "rz_pass_bias": -0.022,
        "early_down_pass_bias": -0.018,
        "two_minute_aggression": 0.95,
        "label": "run_protect",
        "source": "curated_prior",
    },
    # Harbaugh / Jackson — run-lean identity, RZ QB/RB lean.
    "BAL": {
        "pass_rate_bias": -0.030,
        "script_aggression": 0.88,
        "rz_pass_bias": -0.030,
        "early_down_pass_bias": -0.022,
        "two_minute_aggression": 0.92,
        "label": "run_scheme",
        "source": "curated_prior",
    },
    # Conservative New England identity (clock / early-down discipline).
    "NE": {
        "pass_rate_bias": -0.010,
        "script_aggression": 0.85,
        "rz_pass_bias": -0.010,
        "early_down_pass_bias": -0.012,
        "two_minute_aggression": 0.88,
        "label": "conservative",
        "source": "curated_prior",
    },
    # Burrow-era pass tilt.
    "CIN": {
        "pass_rate_bias": 0.025,
        "script_aggression": 1.08,
        "rz_pass_bias": 0.022,
        "early_down_pass_bias": 0.015,
        "two_minute_aggression": 1.08,
        "label": "pass_aggressive",
        "source": "curated_prior",
    },
    # Lions — balanced but aggressive script response (Campbell).
    "DET": {
        "pass_rate_bias": 0.008,
        "script_aggression": 1.14,
        "rz_pass_bias": 0.005,
        "early_down_pass_bias": 0.005,
        "two_minute_aggression": 1.15,
        "label": "script_aggressive",
        "source": "curated_prior",
    },
    # Dolphins — pace / pass identity.
    "MIA": {
        "pass_rate_bias": 0.030,
        "script_aggression": 1.06,
        "rz_pass_bias": 0.018,
        "early_down_pass_bias": 0.020,
        "two_minute_aggression": 1.05,
        "label": "pass_pace",
        "source": "curated_prior",
    },
    # Steelers — run/clock lean, low aggression.
    "PIT": {
        "pass_rate_bias": -0.020,
        "script_aggression": 0.86,
        "rz_pass_bias": -0.015,
        "early_down_pass_bias": -0.015,
        "two_minute_aggression": 0.88,
        "label": "conservative",
        "source": "curated_prior",
    },
    # Browns — run lean.
    "CLE": {
        "pass_rate_bias": -0.022,
        "script_aggression": 0.88,
        "rz_pass_bias": -0.018,
        "early_down_pass_bias": -0.015,
        "two_minute_aggression": 0.90,
        "label": "run_protect",
        "source": "curated_prior",
    },
    # Chargers — pass tilt (Herbert).
    "LAC": {
        "pass_rate_bias": 0.020,
        "script_aggression": 1.05,
        "rz_pass_bias": 0.015,
        "early_down_pass_bias": 0.012,
        "two_minute_aggression": 1.05,
        "label": "pass_tilt",
        "source": "curated_prior",
    },
    # Packers — balanced-pass.
    "GB": {
        "pass_rate_bias": 0.012,
        "script_aggression": 1.02,
        "rz_pass_bias": 0.008,
        "early_down_pass_bias": 0.008,
        "two_minute_aggression": 1.02,
        "label": "balanced_pass",
        "source": "curated_prior",
    },
    # Cowboys — pass tilt.
    "DAL": {
        "pass_rate_bias": 0.015,
        "script_aggression": 1.04,
        "rz_pass_bias": 0.012,
        "early_down_pass_bias": 0.010,
        "two_minute_aggression": 1.04,
        "label": "pass_tilt",
        "source": "curated_prior",
    },
    # Vikings — pass tilt (O'Connell).
    "MIN": {
        "pass_rate_bias": 0.022,
        "script_aggression": 1.06,
        "rz_pass_bias": 0.016,
        "early_down_pass_bias": 0.014,
        "two_minute_aggression": 1.06,
        "label": "pass_tilt",
        "source": "curated_prior",
    },
    # Rams — McVay early-down pass lean.
    "LA": {
        "pass_rate_bias": 0.018,
        "script_aggression": 1.05,
        "rz_pass_bias": 0.012,
        "early_down_pass_bias": 0.016,
        "two_minute_aggression": 1.04,
        "label": "pass_tilt",
        "source": "curated_prior",
    },
    # Titans — run lean.
    "TEN": {
        "pass_rate_bias": -0.018,
        "script_aggression": 0.90,
        "rz_pass_bias": -0.015,
        "early_down_pass_bias": -0.012,
        "two_minute_aggression": 0.92,
        "label": "run_protect",
        "source": "curated_prior",
    },
    # Bears — developing, slight run lean / measured.
    "CHI": {
        "pass_rate_bias": -0.008,
        "script_aggression": 0.95,
        "rz_pass_bias": -0.005,
        "early_down_pass_bias": -0.005,
        "two_minute_aggression": 0.98,
        "label": "balanced",
        "source": "curated_prior",
    },
    # Cardinals — LaFleur HC: balanced-to-pass lean (not pure volume pile).
    # Replaces ARI named pass soft-ceiling sculpture (Phase 2).
    "ARI": {
        "pass_rate_bias": 0.010,
        "script_aggression": 1.02,
        "rz_pass_bias": 0.004,
        "early_down_pass_bias": 0.006,
        "two_minute_aggression": 1.02,
        "label": "balanced_pass",
        "source": "curated_prior",
    },
    # Seahawks — new OC Shanahan-tree: efficient intermediate, mild pass tilt.
    # Replaces SEA Darnold/scheme named pass soft-floor sculpture (Phase 2).
    "SEA": {
        "pass_rate_bias": 0.012,
        "script_aggression": 1.04,
        "rz_pass_bias": 0.006,
        "early_down_pass_bias": 0.008,
        "two_minute_aggression": 1.03,
        "label": "balanced_pass",
        "source": "curated_prior",
    },
    # Commanders — Quinn staff: balanced; OL protection feature owns injury drag.
    "WAS": {
        "pass_rate_bias": 0.008,
        "script_aggression": 1.04,
        "rz_pass_bias": 0.005,
        "early_down_pass_bias": 0.004,
        "two_minute_aggression": 1.05,
        "label": "balanced_pass",
        "source": "curated_prior",
    },
}


def _normalize_team(team: str) -> str:
    t = (team or "").upper().strip()
    if t == "LAR":
        return "LA"
    return t


def profile_for_team(team: str) -> CoachingProfile:
    """Return the clamped coaching profile for ``team`` (always defined)."""
    key = _normalize_team(team)
    raw = _CURATED.get(key)
    if raw is None:
        return CoachingProfile(team=key, **LEAGUE_DEFAULT_PROFILE_KWARGS).clamped()
    return CoachingProfile(team=key, **raw).clamped()


def all_team_profiles() -> Dict[str, CoachingProfile]:
    """Profiles for all 32 NFL teams (curated or league default)."""
    return {t: profile_for_team(t) for t in _NFL_TEAMS}


def baseline_pass_rate(
    *,
    league_base: float,
    strength_pass_bias: float = 0.0,
    coaching: Optional[CoachingProfile] = None,
    team: Optional[str] = None,
    strength_bias_scale: float = 1.75,
    coach_bias_scale: float = 1.35,
) -> float:
    """League + Layer-1 strength bias + coaching pass_rate_bias (clamped).

    v1.16 amplifies strength/coaching identity so pass volume is not nearly
    identical across all 32 clubs (coherence failure mode).
    """
    profile = coaching or (profile_for_team(team) if team else None)
    coach_bias = float(profile.pass_rate_bias) if profile is not None else 0.0
    return _clamp(
        float(league_base)
        + float(strength_bias_scale) * float(strength_pass_bias)
        + float(coach_bias_scale) * coach_bias,
        0.38,
        0.72,
    )


def explain_tendency_effects(
    team: str,
    *,
    base_pass_rate_before_coaching: float,
    detail: ScriptDetail,
    intensity: float,
    time_bucket: TimeBucket,
    pass_rate: float,
    early_down_pass_rate: float,
    hurry_up: float,
    rz_pass_rate: Optional[float] = None,
    unscaled_pass_delta: Optional[float] = None,
) -> Dict[str, Any]:
    """Build an inspectable diagnostics block for one side."""
    profile = profile_for_team(team)
    effects: Dict[str, Any] = {
        "pass_rate_bias_applied": profile.pass_rate_bias,
        "script_aggression": profile.script_aggression,
        "early_down_pass_bias_applied": profile.early_down_pass_bias,
        "two_minute_aggression": profile.two_minute_aggression,
        "rz_pass_bias": profile.rz_pass_bias,
        "pass_rate_after": round(float(pass_rate), 4),
        "early_down_pass_rate_after": round(float(early_down_pass_rate), 4),
        "hurry_up_after": round(float(hurry_up), 4),
        "base_pass_rate_before_coaching_bias": round(
            float(base_pass_rate_before_coaching), 4
        ),
        "script_detail": detail,
        "script_intensity": round(float(intensity), 4),
        "time_bucket": time_bucket,
    }
    if unscaled_pass_delta is not None:
        effects["pass_rate_delta_from_script_aggression"] = round(
            float(unscaled_pass_delta) * (profile.script_aggression - 1.0), 4
        )
    if rz_pass_rate is not None:
        effects["rz_pass_rate_after"] = round(float(rz_pass_rate), 4)
        effects["rz_pass_bias_applied"] = profile.rz_pass_bias
    return {
        "coaching_profile": profile.to_dict(),
        "tendency_effects": effects,
    }


def coaching_tendencies_documentation() -> Dict[str, Any]:
    """Serialize knobs / examples for /status and ops dumps."""
    examples = {
        t: profile_for_team(t).to_dict()
        for t in ("KC", "BUF", "SF", "PHI", "BAL", "NE", "DET", "MIA")
    }
    return {
        "module": "src.services.nfl_season_engine.coaching_tendencies",
        "engine_layer": (
            "Overlays Layer 2 play-mix + RZ pass rate; usage reacts via "
            "existing script→usage matrix (no opaque usage multipliers)."
        ),
        "fields": {
            "pass_rate_bias": "Baseline pass-rate shift (clamped ±0.035)",
            "script_aggression": "Scales script pass deltas (0.80–1.20)",
            "rz_pass_bias": "Additive RZ pass preference (clamped ±0.040)",
            "early_down_pass_bias": "Additive early-down pass tilt (±0.025)",
            "two_minute_aggression": "Scales hurry-up when chasing (0.80–1.20)",
        },
        "clamps": {
            "pass_rate_bias": list(PASS_RATE_BIAS_CLAMP),
            "script_aggression": list(SCRIPT_AGGRESSION_CLAMP),
            "rz_pass_bias": list(RZ_PASS_BIAS_CLAMP),
            "early_down_pass_bias": list(EARLY_DOWN_PASS_BIAS_CLAMP),
            "two_minute_aggression": list(TWO_MINUTE_AGGRESSION_CLAMP),
        },
        "curated_teams": sorted(_CURATED.keys()),
        "examples": examples,
        "seed_policy": (
            "Explicit curated priors for distinctive clubs; "
            "league-average defaults for remaining franchises. "
            "No fitted coach-year regressions."
        ),
    }
