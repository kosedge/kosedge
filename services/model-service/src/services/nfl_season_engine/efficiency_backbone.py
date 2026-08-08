"""NFL in-house efficiency backbone (Sprint 2).

Football-native team efficiency package that feeds the **existing** Layer 1
strength slot (``TeamStrengthState`` / Edge Board ``offense_index`` /
``defense_index``). This is not a parallel ranking API and does not rewrite
the season engine hierarchy.

North star: ``data/ops/nfl-model-vision.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

EFFICIENCY_BACKBONE_VERSION = "v1"
BACKBONE_SOURCE_PACKAGED = "packaged_efficiency_backbone"
BACKBONE_SOURCE_ROLLING = "efficiency_backbone_rolling"
BACKBONE_SOURCE_BLEND = "efficiency_backbone_blend"

# League reference anchors (approx recent NFL REG). Used for relative rates.
_LEAGUE_SUCCESS_RATE = 0.44
_LEAGUE_EXPLOSIVE_PASS_RATE = 0.085
_LEAGUE_RZ_TD_RATE = 0.55
_LEAGUE_PASS_RATE = 0.58
_LEAGUE_PLAYS_PER_GAME = 62.0  # team offensive plays / game approx

# Soft additives on top of EPA→index (keep hierarchy smell tests intact).
_W_SUCCESS = 0.12
_W_EXPLOSIVE = 0.08
_W_RZ = 0.06
_W_ST = 0.04  # tiny bleed into composite diagnostics only via st_index path

# Same clamps as tasks._epa_to_strength_indices.
_OFF_CLAMP = (0.82, 1.22)
_DEF_CLAMP = (0.82, 1.24)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def epa_to_strength_indices(
    *,
    off_epa: float,
    def_epa_allowed: float,
    pressure_generated: float = 0.0,
    pressure_allowed: float = 0.0,
) -> Dict[str, float]:
    """Canonical EPA→index conversion (mirrors ``tasks._epa_to_strength_indices``)."""
    pressure_delta = float(pressure_generated) - float(pressure_allowed)
    offense_index = _clamp(
        1.0 + (float(off_epa) * 0.75) + (pressure_delta * 0.18), *_OFF_CLAMP
    )
    defense_index = _clamp(
        1.0 + ((-float(def_epa_allowed)) * 0.90) + (pressure_delta * 0.14), *_DEF_CLAMP
    )
    return {
        "offense_index": round(offense_index, 6),
        "defense_index": round(defense_index, 6),
    }


@dataclass(frozen=True)
class UnitEfficiency:
    """Offense or defense unit efficiency (NFL play-level)."""

    epa_per_play: float = 0.0
    success_rate: float = _LEAGUE_SUCCESS_RATE
    explosive_rate: float = _LEAGUE_EXPLOSIVE_PASS_RATE
    negative_rate: float = 0.0  # 1 - success_rate when success known
    pass_epa: float = 0.0
    run_epa: float = 0.0
    early_down_epa: float = 0.0
    late_down_conversion_rate: float = 0.40
    red_zone_td_rate: float = _LEAGUE_RZ_TD_RATE
    pressure_rate: float = 0.15
    plays: int = 0


@dataclass
class TeamEfficiencyPackage:
    """Inspectable team efficiency package → maps into Layer 1 strength."""

    team: str
    offense: UnitEfficiency = field(default_factory=UnitEfficiency)
    defense: UnitEfficiency = field(default_factory=UnitEfficiency)
    st_index: float = 1.0
    st_epa_per_play: float = 0.0
    pace: float = 1.0  # plays/game vs league (1.0 = average)
    pass_rate: float = _LEAGUE_PASS_RATE
    explosiveness: float = 0.0  # offense explosive vs league (signed)
    variance: float = 1.0  # >1 early / low sample; tightens with games
    qb_premium: float = 0.0  # hook for QB identity layer (0 until wired)
    games_played: int = 0
    as_of: str = ""
    version: str = EFFICIENCY_BACKBONE_VERSION
    source: str = BACKBONE_SOURCE_PACKAGED
    prior_season: int = 0
    notes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "offense": asdict(self.offense),
            "defense": asdict(self.defense),
            "st_index": self.st_index,
            "st_epa_per_play": self.st_epa_per_play,
            "pace": self.pace,
            "pass_rate": self.pass_rate,
            "explosiveness": self.explosiveness,
            "variance": self.variance,
            "qb_premium": self.qb_premium,
            "games_played": self.games_played,
            "as_of": self.as_of,
            "version": self.version,
            "source": self.source,
            "prior_season": self.prior_season,
            "notes": dict(self.notes),
        }


def uncertainty_from_games(games_played: int) -> float:
    """Wider uncertainty early; tightens toward 0.55 by ~16 games."""
    g = max(0, int(games_played))
    # 1.35 at 0 games → ~0.55 at 16 games
    return round(_clamp(1.35 - 0.05 * g, 0.55, 1.40), 4)


def prior_current_blend_weight(*, current_games: int, full_season_games: int = 17) -> float:
    """Weight on current-season sample (rest on prior)."""
    g = max(0, int(current_games))
    # Reach ~full current weight by week 8; still some prior early.
    return _clamp(g / 8.0, 0.0, 1.0)


def opponent_adjust_epa(raw_epa: float, *, league_epa: float = 0.0) -> float:
    """Simple NFL-results-only opponent adjustment: center vs league mean."""
    return float(raw_epa) - float(league_epa)


def _rate_delta(value: float, league: float) -> float:
    return float(value) - float(league)


def package_to_strength_indices(pkg: TeamEfficiencyPackage) -> Dict[str, float]:
    """Map a full efficiency package into the existing O/D index contract.

    Base = EPA + pressure (identical units to Edge Board). Soft additives from
    success / explosiveness / red-zone keep football context without inventing
    a second strength book. ST stays on ``st_index`` (small optional bleed).
    """
    base = epa_to_strength_indices(
        off_epa=pkg.offense.epa_per_play,
        def_epa_allowed=pkg.defense.epa_per_play,
        pressure_generated=pkg.defense.pressure_rate,  # generated on defense
        pressure_allowed=pkg.offense.pressure_rate,  # allowed on offense
    )
    off_add = (
        _W_SUCCESS * _rate_delta(pkg.offense.success_rate, _LEAGUE_SUCCESS_RATE)
        + _W_EXPLOSIVE * _rate_delta(pkg.offense.explosive_rate, _LEAGUE_EXPLOSIVE_PASS_RATE)
        + _W_RZ * _rate_delta(pkg.offense.red_zone_td_rate, _LEAGUE_RZ_TD_RATE)
    )
    # Defense: lower allowed success / explosive / RZ is better → invert deltas.
    def_add = (
        _W_SUCCESS * (-_rate_delta(pkg.defense.success_rate, _LEAGUE_SUCCESS_RATE))
        + _W_EXPLOSIVE * (-_rate_delta(pkg.defense.explosive_rate, _LEAGUE_EXPLOSIVE_PASS_RATE))
        + _W_RZ * (-_rate_delta(pkg.defense.red_zone_td_rate, _LEAGUE_RZ_TD_RATE))
    )
    # Tiny ST bleed (symmetric) so ST module is not decorative-only.
    st_bleed = _W_ST * (float(pkg.st_index) - 1.0)

    # Early-season: shrink additives toward 0 when variance high / few games.
    shrink = _clamp(1.0 / max(0.75, float(pkg.variance)), 0.55, 1.0)
    offense_index = _clamp(
        float(base["offense_index"]) + shrink * (off_add + 0.5 * st_bleed), *_OFF_CLAMP
    )
    defense_index = _clamp(
        float(base["defense_index"]) + shrink * (def_add + 0.5 * st_bleed), *_DEF_CLAMP
    )
    pass_rate_bias = _clamp(float(pkg.pass_rate) - _LEAGUE_PASS_RATE, -0.12, 0.12)
    pace_factor = _clamp(float(pkg.pace), 0.88, 1.12)
    return {
        "offense_index": round(offense_index, 6),
        "defense_index": round(defense_index, 6),
        "pace_factor": round(pace_factor, 6),
        "pass_rate_bias": round(pass_rate_bias, 6),
        "st_index": round(_clamp(pkg.st_index, 0.85, 1.15), 6),
        "explosiveness": round(float(pkg.explosiveness), 6),
        "variance": round(float(pkg.variance), 6),
        "qb_premium": round(float(pkg.qb_premium), 6),
    }


def strength_payload_from_package(
    pkg: TeamEfficiencyPackage,
    *,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Payload accepted by ``initialize_strengths`` / loaders."""
    indices = package_to_strength_indices(pkg)
    return {
        **indices,
        "source": str(source or pkg.source),
        "games_played": int(pkg.games_played),
        "as_of": str(pkg.as_of or ""),
        "version": str(pkg.version or EFFICIENCY_BACKBONE_VERSION),
        "off_epa_per_play": float(pkg.offense.epa_per_play),
        "def_epa_allowed_per_play": float(pkg.defense.epa_per_play),
    }


def build_unit_from_rates(
    *,
    epa_per_play: float,
    success_rate: float,
    explosive_rate: float,
    red_zone_td_rate: float,
    pressure_rate: float,
    plays: int = 0,
    pass_epa: Optional[float] = None,
    run_epa: Optional[float] = None,
    early_down_epa: Optional[float] = None,
    late_down_conversion_rate: float = 0.40,
) -> UnitEfficiency:
    sr = _safe_float(success_rate, _LEAGUE_SUCCESS_RATE)
    return UnitEfficiency(
        epa_per_play=_safe_float(epa_per_play),
        success_rate=sr,
        explosive_rate=_safe_float(explosive_rate, _LEAGUE_EXPLOSIVE_PASS_RATE),
        negative_rate=round(_clamp(1.0 - sr, 0.0, 1.0), 6),
        pass_epa=_safe_float(pass_epa, epa_per_play),
        run_epa=_safe_float(run_epa, epa_per_play),
        early_down_epa=_safe_float(early_down_epa, epa_per_play),
        late_down_conversion_rate=_safe_float(late_down_conversion_rate, 0.40),
        red_zone_td_rate=_safe_float(red_zone_td_rate, _LEAGUE_RZ_TD_RATE),
        pressure_rate=_safe_float(pressure_rate, 0.15),
        plays=int(plays or 0),
    )


def build_package_from_season_row(
    team: str,
    row: Mapping[str, Any],
    *,
    as_of: str = "",
    source: str = BACKBONE_SOURCE_PACKAGED,
    prior_season: int = 0,
    league_off_epa: float = 0.0,
    league_def_epa: float = 0.0,
    st_epa: Optional[float] = None,
) -> TeamEfficiencyPackage:
    """Build a package from play-weighted season (or rolling) aggregate row."""
    off_plays = int(row.get("offensive_plays") or row.get("off_plays") or 0)
    def_plays = int(row.get("defensive_plays") or row.get("def_plays") or 0)
    n_weeks = int(row.get("n_weeks") or row.get("games_played") or 0)
    games = n_weeks if n_weeks > 0 else int(row.get("games_played") or 0)

    off_epa_raw = _safe_float(row.get("off_epa_per_play", row.get("epa_per_play_offense")))
    def_epa_raw = _safe_float(
        row.get("def_epa_allowed_per_play", row.get("epa_per_play_defense_allowed"))
    )
    off_epa = opponent_adjust_epa(off_epa_raw, league_epa=league_off_epa)
    def_epa = opponent_adjust_epa(def_epa_raw, league_epa=league_def_epa)

    pass_plays = _safe_float(row.get("pass_plays"), 0.0)
    run_plays = _safe_float(row.get("run_plays"), 0.0)
    pass_rate = _safe_float(row.get("pass_rate"), _LEAGUE_PASS_RATE)
    if pass_rate <= 0 and (pass_plays + run_plays) > 0:
        pass_rate = pass_plays / (pass_plays + run_plays)

    off_explosive = _safe_float(row.get("explosive_rate_offense"))
    if off_explosive <= 0 and off_plays > 0:
        off_explosive = _safe_float(row.get("explosive_pass_plays")) / max(1.0, off_plays)
    if off_explosive <= 0:
        off_explosive = _LEAGUE_EXPLOSIVE_PASS_RATE

    def_explosive = _safe_float(row.get("explosive_rate_defense_allowed"))
    if def_explosive <= 0 and def_plays > 0:
        def_explosive = _safe_float(row.get("explosive_pass_allowed")) / max(1.0, def_plays)
    if def_explosive <= 0:
        def_explosive = _LEAGUE_EXPLOSIVE_PASS_RATE

    offense = build_unit_from_rates(
        epa_per_play=off_epa,
        success_rate=_safe_float(row.get("success_rate_offense"), _LEAGUE_SUCCESS_RATE),
        explosive_rate=off_explosive,
        red_zone_td_rate=_safe_float(row.get("red_zone_td_rate"), _LEAGUE_RZ_TD_RATE),
        pressure_rate=_safe_float(
            row.get("pressure_rate_allowed", row.get("pressure_allowed")), 0.15
        ),
        plays=off_plays,
        late_down_conversion_rate=_safe_float(
            row.get("third_down_conversion_rate"), 0.40
        ),
    )
    defense = build_unit_from_rates(
        epa_per_play=def_epa,
        success_rate=_safe_float(
            row.get("success_rate_defense_allowed"), _LEAGUE_SUCCESS_RATE
        ),
        explosive_rate=def_explosive,
        red_zone_td_rate=_safe_float(
            row.get("red_zone_td_rate_allowed"), _LEAGUE_RZ_TD_RATE
        ),
        pressure_rate=_safe_float(
            row.get("pressure_rate_generated", row.get("pressure_generated")), 0.15
        ),
        plays=def_plays,
        late_down_conversion_rate=_safe_float(
            row.get("third_down_conversion_rate_allowed"), 0.40
        ),
    )

    st_epa_val = _safe_float(st_epa if st_epa is not None else row.get("st_epa_per_play"), 0.0)
    st_index = _clamp(1.0 + st_epa_val * 0.55, 0.85, 1.15)

    plays_per_game = (
        (off_plays / games) if games > 0 and off_plays > 0 else _LEAGUE_PLAYS_PER_GAME
    )
    pace = plays_per_game / _LEAGUE_PLAYS_PER_GAME
    explosiveness = _rate_delta(offense.explosive_rate, _LEAGUE_EXPLOSIVE_PASS_RATE)

    return TeamEfficiencyPackage(
        team=str(team),
        offense=offense,
        defense=defense,
        st_index=round(st_index, 6),
        st_epa_per_play=round(st_epa_val, 6),
        pace=round(_clamp(pace, 0.88, 1.12), 6),
        pass_rate=round(_clamp(pass_rate, 0.35, 0.75), 6),
        explosiveness=round(explosiveness, 6),
        variance=uncertainty_from_games(games),
        qb_premium=_safe_float(row.get("qb_premium"), 0.0),
        games_played=int(games),
        as_of=str(as_of or row.get("as_of") or ""),
        version=EFFICIENCY_BACKBONE_VERSION,
        source=str(source),
        prior_season=int(prior_season or row.get("prior_season") or 0),
        notes={
            "off_epa_raw": round(off_epa_raw, 6),
            "def_epa_raw": round(def_epa_raw, 6),
            "league_off_epa": round(league_off_epa, 6),
            "league_def_epa": round(league_def_epa, 6),
        },
    )


def blend_packages(
    prior: TeamEfficiencyPackage,
    current: TeamEfficiencyPackage,
) -> TeamEfficiencyPackage:
    """Blend prior-season → current-season packages with sample-aware weights."""
    w_cur = prior_current_blend_weight(current_games=current.games_played)
    w_prior = 1.0 - w_cur

    def _blend_unit(a: UnitEfficiency, b: UnitEfficiency) -> UnitEfficiency:
        return UnitEfficiency(
            epa_per_play=w_prior * a.epa_per_play + w_cur * b.epa_per_play,
            success_rate=w_prior * a.success_rate + w_cur * b.success_rate,
            explosive_rate=w_prior * a.explosive_rate + w_cur * b.explosive_rate,
            negative_rate=w_prior * a.negative_rate + w_cur * b.negative_rate,
            pass_epa=w_prior * a.pass_epa + w_cur * b.pass_epa,
            run_epa=w_prior * a.run_epa + w_cur * b.run_epa,
            early_down_epa=w_prior * a.early_down_epa + w_cur * b.early_down_epa,
            late_down_conversion_rate=(
                w_prior * a.late_down_conversion_rate + w_cur * b.late_down_conversion_rate
            ),
            red_zone_td_rate=w_prior * a.red_zone_td_rate + w_cur * b.red_zone_td_rate,
            pressure_rate=w_prior * a.pressure_rate + w_cur * b.pressure_rate,
            plays=int(a.plays + b.plays),
        )

    games = max(int(prior.games_played), int(current.games_played))
    return TeamEfficiencyPackage(
        team=current.team or prior.team,
        offense=_blend_unit(prior.offense, current.offense),
        defense=_blend_unit(prior.defense, current.defense),
        st_index=w_prior * prior.st_index + w_cur * current.st_index,
        st_epa_per_play=w_prior * prior.st_epa_per_play + w_cur * current.st_epa_per_play,
        pace=w_prior * prior.pace + w_cur * current.pace,
        pass_rate=w_prior * prior.pass_rate + w_cur * current.pass_rate,
        explosiveness=w_prior * prior.explosiveness + w_cur * current.explosiveness,
        variance=uncertainty_from_games(current.games_played),
        qb_premium=w_prior * prior.qb_premium + w_cur * current.qb_premium,
        games_played=int(current.games_played),
        as_of=current.as_of or prior.as_of,
        version=EFFICIENCY_BACKBONE_VERSION,
        source=BACKBONE_SOURCE_BLEND,
        prior_season=int(prior.prior_season or 0),
        notes={
            "blend_current_weight": round(w_cur, 4),
            "blend_prior_weight": round(w_prior, 4),
            "prior_source": prior.source,
            "current_source": current.source,
        },
    )


def packages_from_team_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    as_of: str = "",
    source: str = BACKBONE_SOURCE_PACKAGED,
    prior_season: int = 0,
) -> Dict[str, TeamEfficiencyPackage]:
    """Build per-team packages with league-mean opponent centering."""
    if not rows:
        return {}
    off_epas = [
        _safe_float(r.get("off_epa_per_play", r.get("epa_per_play_offense"))) for r in rows
    ]
    def_epas = [
        _safe_float(r.get("def_epa_allowed_per_play", r.get("epa_per_play_defense_allowed")))
        for r in rows
    ]
    league_off = sum(off_epas) / max(1, len(off_epas))
    league_def = sum(def_epas) / max(1, len(def_epas))
    out: Dict[str, TeamEfficiencyPackage] = {}
    for r in rows:
        team = str(r.get("team") or "").strip().upper()
        if team == "LAR":
            team = "LA"
        if not team:
            continue
        out[team] = build_package_from_season_row(
            team,
            r,
            as_of=as_of,
            source=source,
            prior_season=prior_season,
            league_off_epa=league_off,
            league_def_epa=league_def,
            st_epa=_safe_float(r.get("st_epa_per_play"), 0.0) if "st_epa_per_play" in r else None,
        )
    return out


def hierarchy_composite(pkg: TeamEfficiencyPackage) -> float:
    """O+D composite used for smell-test ranking (same language as power)."""
    idx = package_to_strength_indices(pkg)
    return float(idx["offense_index"]) + float(idx["defense_index"])


def rank_packages(
    packages: Mapping[str, TeamEfficiencyPackage],
) -> List[Tuple[str, float]]:
    ranked = sorted(
        ((t, hierarchy_composite(p)) for t, p in packages.items()),
        key=lambda x: -x[1],
    )
    return ranked
