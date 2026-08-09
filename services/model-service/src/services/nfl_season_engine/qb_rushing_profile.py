"""General QB rushing profile → pass/rush volume + script tilt (Phase 2).

Replaces named-team pass-volume sculpture (ARI/BAL/SEA) with a player-trait
feature keyed by SoT ``player_id`` (GSIS) when known, else by role rush_share.

Formula (documented, modest):
  scramble_share   ∈ [0, 0.22]   — freelanced rushes / team rush plays
  designed_run_share ∈ [0, 0.14] — called QB runs / team rush plays
  rush_share       = scramble + designed  (team rush pool share for QB1)
  pass_volume_mult = 1 − 0.55 * (rush_share − 0.06)   clamped [0.86, 1.04]
  rush_volume_mult = 1 + 0.70 * (rush_share − 0.06)   clamped [0.94, 1.14]
  script_run_tilt  = 0.35 * designed_run_share        (lead-script run lean)
  rush_td_gl_mult  = 1 + 1.1 * designed_run_share     clamped [0.97, 1.12]

Tiers are priors from recent dual-threat seasons — not team hardcodes.
Pocket / bridge QBs use the default tier (no post-hoc yard clamps).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Tier templates (league-general)
# ---------------------------------------------------------------------------
_TIER_TEMPLATES: Dict[str, Dict[str, float]] = {
    "pocket": {
        "scramble_share": 0.025,
        "designed_run_share": 0.005,
    },
    "light_scramble": {
        "scramble_share": 0.055,
        "designed_run_share": 0.015,
    },
    "dual_threat": {
        "scramble_share": 0.10,
        "designed_run_share": 0.055,
    },
    "designed_run_heavy": {
        "scramble_share": 0.09,
        "designed_run_share": 0.11,
    },
}

# SoT GSIS → tier. Revisit by 2026-10-01 (Week-5 usage evidence).
# Expiry forces re-fit from observed rush_share rather than board aesthetics.
QB_RUSH_TIER_BY_PLAYER_ID: Dict[str, str] = {
    # designed_run_heavy
    "00-0034796": "designed_run_heavy",  # Lamar Jackson
    "00-0036389": "designed_run_heavy",  # Jalen Hurts
    # dual_threat
    "00-0034857": "dual_threat",  # Josh Allen
    "00-0039910": "dual_threat",  # Jayden Daniels
    "00-0035228": "dual_threat",  # Kyler Murray
    "00-0039918": "dual_threat",  # Caleb Williams
    "00-0039732": "dual_threat",  # Bo Nix
    "00-0039851": "dual_threat",  # Drake Maye
    # light_scramble
    "00-0033873": "light_scramble",  # Patrick Mahomes
    "00-0039150": "light_scramble",  # Bryce Young
    "00-0036971": "light_scramble",  # Trevor Lawrence
    "00-0036264": "light_scramble",  # Jordan Love
    "00-0034855": "light_scramble",  # Baker Mayfield
    "00-0040691": "light_scramble",  # Jaxson Dart
    "00-0040676": "light_scramble",  # Cam Ward
    # pocket (explicit for bridge / known pocket passers — default also pocket)
    "00-0033119": "pocket",  # Jacoby Brissett
    "00-0034869": "pocket",  # Sam Darnold
    "00-0036212": "pocket",  # Tua Tagovailoa
    "00-0033106": "pocket",  # Jared Goff
    "00-0026498": "pocket",  # Matthew Stafford
    "00-0029604": "pocket",  # Kirk Cousins
    "00-0023459": "pocket",  # Aaron Rodgers
}

QB_RUSH_PROFILE_REVISIT_BY = "2026-10-01"
QB_RUSH_PROFILE_VERSION = "qb-rushing-profile-v1"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class QbRushingProfile:
    """Inspectable QB1 rushing identity for volume / script features."""

    player_id: str
    player_name: str
    team: str
    tier: str
    scramble_share: float
    designed_run_share: float
    rush_share: float
    pass_volume_mult: float
    rush_volume_mult: float
    script_run_tilt: float
    rush_td_gl_mult: float
    source: str = "tier_prior"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team": self.team,
            "tier": self.tier,
            "scramble_share": round(self.scramble_share, 4),
            "designed_run_share": round(self.designed_run_share, 4),
            "rush_share": round(self.rush_share, 4),
            "pass_volume_mult": round(self.pass_volume_mult, 4),
            "rush_volume_mult": round(self.rush_volume_mult, 4),
            "script_run_tilt": round(self.script_run_tilt, 4),
            "rush_td_gl_mult": round(self.rush_td_gl_mult, 4),
            "source": self.source,
            "version": QB_RUSH_PROFILE_VERSION,
            "revisit_by": QB_RUSH_PROFILE_REVISIT_BY,
        }


def multipliers_from_rush_share(rush_share: float) -> Tuple[float, float, float, float]:
    """Map QB rush_share → (pass_mult, rush_mult, script_tilt, gl_mult)."""
    rs = _clamp(rush_share, 0.0, 0.30)
    pass_m = _clamp(1.0 - 0.55 * (rs - 0.06), 0.86, 1.04)
    rush_m = _clamp(1.0 + 0.70 * (rs - 0.06), 0.94, 1.14)
    # designed ≈ 40% of rush_share for unknown splits; script tilt uses that.
    designed = _clamp(0.40 * rs, 0.0, 0.14)
    script_tilt = _clamp(0.35 * designed, 0.0, 0.05)
    gl = _clamp(1.0 + 1.1 * designed, 0.97, 1.12)
    return pass_m, rush_m, script_tilt, gl


def profile_from_tier(
    *,
    player_id: str,
    player_name: str,
    team: str,
    tier: str,
    source: str = "tier_prior",
) -> QbRushingProfile:
    tmpl = _TIER_TEMPLATES.get(tier) or _TIER_TEMPLATES["pocket"]
    scramble = float(tmpl["scramble_share"])
    designed = float(tmpl["designed_run_share"])
    rush = scramble + designed
    pass_m, rush_m, script_tilt, gl = multipliers_from_rush_share(rush)
    # Prefer designed-aware GL mult when tier known.
    gl = _clamp(1.0 + 1.1 * designed, 0.97, 1.12)
    script_tilt = _clamp(0.35 * designed, 0.0, 0.05)
    return QbRushingProfile(
        player_id=str(player_id or ""),
        player_name=str(player_name or ""),
        team=str(team or "").upper(),
        tier=tier if tier in _TIER_TEMPLATES else "pocket",
        scramble_share=scramble,
        designed_run_share=designed,
        rush_share=rush,
        pass_volume_mult=pass_m,
        rush_volume_mult=rush_m,
        script_run_tilt=script_tilt,
        rush_td_gl_mult=gl,
        source=source,
    )


def profile_from_rush_share(
    *,
    player_id: str,
    player_name: str,
    team: str,
    rush_share: float,
    source: str = "role_rush_share",
) -> QbRushingProfile:
    rs = _clamp(float(rush_share), 0.0, 0.30)
    # Split unknown share: 60% scramble / 40% designed (league mobile mix).
    scramble = rs * 0.60
    designed = rs * 0.40
    pass_m, rush_m, script_tilt, gl = multipliers_from_rush_share(rs)
    gl = _clamp(1.0 + 1.1 * designed, 0.97, 1.12)
    script_tilt = _clamp(0.35 * designed, 0.0, 0.05)
    if rs >= 0.18:
        tier = "designed_run_heavy"
    elif rs >= 0.12:
        tier = "dual_threat"
    elif rs >= 0.06:
        tier = "light_scramble"
    else:
        tier = "pocket"
    return QbRushingProfile(
        player_id=str(player_id or ""),
        player_name=str(player_name or ""),
        team=str(team or "").upper(),
        tier=tier,
        scramble_share=scramble,
        designed_run_share=designed,
        rush_share=rs,
        pass_volume_mult=pass_m,
        rush_volume_mult=rush_m,
        script_run_tilt=script_tilt,
        rush_td_gl_mult=gl,
        source=source,
    )


def resolve_qb1_profile(
    *,
    player_id: str = "",
    player_name: str = "",
    team: str = "",
    rush_share: Optional[float] = None,
) -> QbRushingProfile:
    """Resolve profile: SoT player_id tier → else role rush_share → pocket."""
    pid = str(player_id or "").strip()
    if pid and pid in QB_RUSH_TIER_BY_PLAYER_ID:
        return profile_from_tier(
            player_id=pid,
            player_name=player_name,
            team=team,
            tier=QB_RUSH_TIER_BY_PLAYER_ID[pid],
            source="sot_player_id_tier",
        )
    if rush_share is not None and float(rush_share) > 0:
        return profile_from_rush_share(
            player_id=pid,
            player_name=player_name,
            team=team,
            rush_share=float(rush_share),
        )
    return profile_from_tier(
        player_id=pid,
        player_name=player_name,
        team=team,
        tier="pocket",
        source="default_pocket",
    )


def profiles_from_depth_rows(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, QbRushingProfile]:
    """QB1 profiles keyed by team from depth SoT rows."""
    out: Dict[str, QbRushingProfile] = {}
    for row in rows:
        if str(row.get("position") or "").upper() != "QB":
            continue
        try:
            depth = int(row.get("depth_order") or 99)
        except (TypeError, ValueError):
            continue
        if depth != 1:
            continue
        team = str(row.get("team") or "").strip().upper()
        if not team:
            continue
        out[team] = resolve_qb1_profile(
            player_id=str(row.get("player_id") or ""),
            player_name=str(row.get("player_name") or ""),
            team=team,
            rush_share=row.get("rush_share"),
        )
    return out


def apply_qb_rush_to_role_shares(
    rush_share: float,
    profile: QbRushingProfile,
) -> float:
    """Prefer profile rush_share when role still sits on the pocket default."""
    base = float(rush_share or 0.0)
    # Default QB1 prior in loaders is ~0.07; lift mobile QBs from SoT tier.
    if abs(base - 0.07) < 0.015 or base < profile.rush_share:
        return round(float(profile.rush_share), 4)
    return round(base, 4)
