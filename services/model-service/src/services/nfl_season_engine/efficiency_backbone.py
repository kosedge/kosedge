"""NFL in-house efficiency backbone (Sprint 2 → v1.1).

Football-native team efficiency package that feeds the **existing** Layer 1
strength slot (``TeamStrengthState`` / Edge Board ``offense_index`` /
``defense_index``). This is not a parallel ranking API and does not rewrite
the season engine hierarchy.

North star: ``data/ops/nfl-model-vision.md``.

v1.1 adds real special-teams contribution (ST KAV / ST EPA) and true
pass / run / early-down EPA splits as soft Off drivers with visible labels.
Thin samples are labeled — never invented certainty.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

EFFICIENCY_BACKBONE_VERSION = "v1.1"
BACKBONE_SOURCE_PACKAGED = "packaged_efficiency_backbone"
BACKBONE_SOURCE_ROLLING = "efficiency_backbone_rolling"
BACKBONE_SOURCE_BLEND = "efficiency_backbone_blend"

# League reference anchors (approx recent NFL REG). Used for relative rates.
_LEAGUE_SUCCESS_RATE = 0.44
_LEAGUE_EXPLOSIVE_PASS_RATE = 0.085
_LEAGUE_RZ_TD_RATE = 0.55
_LEAGUE_PASS_RATE = 0.58
_LEAGUE_PLAYS_PER_GAME = 62.0  # team offensive plays / game approx
_LEAGUE_PASS_EPA = 0.0
_LEAGUE_RUN_EPA = -0.02
_LEAGUE_EARLY_DOWN_EPA = 0.0

# Soft additives on top of EPA→index (keep hierarchy smell tests intact).
_W_SUCCESS = 0.12
_W_EXPLOSIVE = 0.08
_W_RZ = 0.06
_W_ST = 0.065  # v1.1: modest ST bleed (was 0.04); still subordinate to Off/Def
_W_PASS_EPA = 0.05
_W_RUN_EPA = 0.035
_W_EARLY_DOWN = 0.04

# Sample floors for labeling thin splits (season aggregates).
_THIN_PASS_PLAYS = 200
_THIN_RUN_PLAYS = 150
_THIN_EARLY_PLAYS = 250
_THIN_ST_PLAYS = 40

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
    pass_plays: int = 0
    run_plays: int = 0
    early_down_plays: int = 0


@dataclass
class TeamEfficiencyPackage:
    """Inspectable team efficiency package → maps into Layer 1 strength."""

    team: str
    offense: UnitEfficiency = field(default_factory=UnitEfficiency)
    defense: UnitEfficiency = field(default_factory=UnitEfficiency)
    st_index: float = 1.0
    st_epa_per_play: float = 0.0
    st_plays: int = 0
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
            "st_plays": self.st_plays,
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


def _split_confidence(*, plays: int, floor: int) -> Tuple[float, str]:
    """Return (weight 0..1, label) for a split sample."""
    n = max(0, int(plays))
    if n <= 0:
        return 0.0, "missing"
    if n < floor:
        return _clamp(n / float(floor), 0.15, 0.85), "thin"
    return 1.0, "ok"


def visible_drivers(pkg: TeamEfficiencyPackage) -> Dict[str, Any]:
    """Inspectable Off/Def/ST drivers for Edge Board / ops (v1.1)."""
    off = pkg.offense
    pass_w, pass_lbl = _split_confidence(plays=off.pass_plays, floor=_THIN_PASS_PLAYS)
    run_w, run_lbl = _split_confidence(plays=off.run_plays, floor=_THIN_RUN_PLAYS)
    early_w, early_lbl = _split_confidence(
        plays=off.early_down_plays, floor=_THIN_EARLY_PLAYS
    )
    st_w, st_lbl = _split_confidence(plays=pkg.st_plays, floor=_THIN_ST_PLAYS)
    if abs(float(pkg.st_epa_per_play)) < 1e-9 and pkg.st_plays <= 0:
        st_lbl = "neutral_hook"
        st_w = 0.0
    return {
        "version": EFFICIENCY_BACKBONE_VERSION,
        "off_epa": round(float(off.epa_per_play), 6),
        "def_epa_allowed": round(float(pkg.defense.epa_per_play), 6),
        "pass_epa": round(float(off.pass_epa), 6),
        "pass_epa_sample": pass_lbl,
        "pass_plays": int(off.pass_plays),
        "run_epa": round(float(off.run_epa), 6),
        "run_epa_sample": run_lbl,
        "run_plays": int(off.run_plays),
        "early_down_epa": round(float(off.early_down_epa), 6),
        "early_down_sample": early_lbl,
        "early_down_plays": int(off.early_down_plays),
        "success_rate": round(float(off.success_rate), 6),
        "explosive_rate": round(float(off.explosive_rate), 6),
        "red_zone_td_rate": round(float(off.red_zone_td_rate), 6),
        "st_index": round(float(pkg.st_index), 6),
        "st_epa_per_play": round(float(pkg.st_epa_per_play), 6),
        "st_sample": st_lbl,
        "st_plays": int(pkg.st_plays),
        "pace": round(float(pkg.pace), 6),
        "variance": round(float(pkg.variance), 6),
        "split_weights": {
            "pass": round(pass_w, 4),
            "run": round(run_w, 4),
            "early_down": round(early_w, 4),
            "st": round(st_w, 4),
        },
    }


def package_to_strength_indices(pkg: TeamEfficiencyPackage) -> Dict[str, Any]:
    """Map a full efficiency package into the existing O/D index contract.

    Base = EPA + pressure (identical units to Edge Board). Soft additives from
    success / explosiveness / red-zone / pass-run-early splits keep football
    context without inventing a second strength book. ST bleeds modestly.
    """
    base = epa_to_strength_indices(
        off_epa=pkg.offense.epa_per_play,
        def_epa_allowed=pkg.defense.epa_per_play,
        pressure_generated=pkg.defense.pressure_rate,  # generated on defense
        pressure_allowed=pkg.offense.pressure_rate,  # allowed on offense
    )
    pass_w, _ = _split_confidence(
        plays=pkg.offense.pass_plays, floor=_THIN_PASS_PLAYS
    )
    run_w, _ = _split_confidence(plays=pkg.offense.run_plays, floor=_THIN_RUN_PLAYS)
    early_w, _ = _split_confidence(
        plays=pkg.offense.early_down_plays, floor=_THIN_EARLY_PLAYS
    )
    st_w, _ = _split_confidence(plays=pkg.st_plays, floor=_THIN_ST_PLAYS)
    if abs(float(pkg.st_epa_per_play)) < 1e-9 and pkg.st_plays <= 0:
        st_w = 0.0

    # When split samples missing, fall back to overall EPA (no invent).
    pass_epa = (
        pkg.offense.pass_epa
        if pkg.offense.pass_plays > 0
        else pkg.offense.epa_per_play
    )
    run_epa = (
        pkg.offense.run_epa if pkg.offense.run_plays > 0 else pkg.offense.epa_per_play
    )
    early_epa = (
        pkg.offense.early_down_epa
        if pkg.offense.early_down_plays > 0
        else pkg.offense.epa_per_play
    )

    split_add = (
        _W_PASS_EPA * pass_w * _rate_delta(pass_epa, _LEAGUE_PASS_EPA)
        + _W_RUN_EPA * run_w * _rate_delta(run_epa, _LEAGUE_RUN_EPA)
        + _W_EARLY_DOWN * early_w * _rate_delta(early_epa, _LEAGUE_EARLY_DOWN_EPA)
    )
    # Defense-allowed splits when present (invert: allowing more EPA is worse).
    def_pass_w, _ = _split_confidence(
        plays=pkg.defense.pass_plays, floor=_THIN_PASS_PLAYS
    )
    def_run_w, _ = _split_confidence(
        plays=pkg.defense.run_plays, floor=_THIN_RUN_PLAYS
    )
    def_early_w, _ = _split_confidence(
        plays=pkg.defense.early_down_plays, floor=_THIN_EARLY_PLAYS
    )
    def_pass = (
        pkg.defense.pass_epa
        if pkg.defense.pass_plays > 0
        else pkg.defense.epa_per_play
    )
    def_run = (
        pkg.defense.run_epa if pkg.defense.run_plays > 0 else pkg.defense.epa_per_play
    )
    def_early = (
        pkg.defense.early_down_epa
        if pkg.defense.early_down_plays > 0
        else pkg.defense.epa_per_play
    )
    def_split_add = (
        _W_PASS_EPA * def_pass_w * (-_rate_delta(def_pass, _LEAGUE_PASS_EPA))
        + _W_RUN_EPA * def_run_w * (-_rate_delta(def_run, _LEAGUE_RUN_EPA))
        + _W_EARLY_DOWN
        * def_early_w
        * (-_rate_delta(def_early, _LEAGUE_EARLY_DOWN_EPA))
    )

    off_add = (
        _W_SUCCESS * _rate_delta(pkg.offense.success_rate, _LEAGUE_SUCCESS_RATE)
        + _W_EXPLOSIVE * _rate_delta(pkg.offense.explosive_rate, _LEAGUE_EXPLOSIVE_PASS_RATE)
        + _W_RZ * _rate_delta(pkg.offense.red_zone_td_rate, _LEAGUE_RZ_TD_RATE)
        + split_add
    )
    # Defense: lower allowed success / explosive / RZ is better → invert deltas.
    def_add = (
        _W_SUCCESS * (-_rate_delta(pkg.defense.success_rate, _LEAGUE_SUCCESS_RATE))
        + _W_EXPLOSIVE * (-_rate_delta(pkg.defense.explosive_rate, _LEAGUE_EXPLOSIVE_PASS_RATE))
        + _W_RZ * (-_rate_delta(pkg.defense.red_zone_td_rate, _LEAGUE_RZ_TD_RATE))
        + def_split_add
    )
    # Modest ST bleed (symmetric) so ST module is not decorative-only.
    st_bleed = _W_ST * st_w * (float(pkg.st_index) - 1.0)

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
    drivers = visible_drivers(pkg)
    return {
        "offense_index": round(offense_index, 6),
        "defense_index": round(defense_index, 6),
        "pace_factor": round(pace_factor, 6),
        "pass_rate_bias": round(pass_rate_bias, 6),
        "st_index": round(_clamp(pkg.st_index, 0.85, 1.15), 6),
        "explosiveness": round(float(pkg.explosiveness), 6),
        "variance": round(float(pkg.variance), 6),
        "qb_premium": round(float(pkg.qb_premium), 6),
        "drivers": drivers,
    }


def strength_payload_from_package(
    pkg: TeamEfficiencyPackage,
    *,
    source: Optional[str] = None,
    injury_delta_offense: float = 0.0,
    injury_delta_defense: float = 0.0,
    injury_status: str = "structure_ready_zero",
) -> Dict[str, Any]:
    """Payload accepted by ``initialize_strengths`` / loaders.

    Exposes full-strength vs current PR: at load time (no injury scars applied)
    they are equal; injury overlays mutate current indices only and record the
    delta. Never invents QB premium / continuity / time-of-game SOS.
    """
    indices = package_to_strength_indices(pkg)
    # Full-strength = reconstructed intrinsic PR (no availability scars).
    full_off = float(indices["offense_index"])
    full_def = float(indices["defense_index"])
    cur_off = full_off + float(injury_delta_offense)
    cur_def = full_def + float(injury_delta_defense)
    drivers = true_pr_drivers(
        pkg,
        injury_delta_offense=float(injury_delta_offense),
        injury_delta_defense=float(injury_delta_defense),
        injury_status=injury_status,
    )
    # Replace package_to_strength_indices drivers with true-PR enriched set.
    w_cur = float(pkg.notes.get("blend_current_weight", 0.0) or 0.0)
    w_prior = float(pkg.notes.get("blend_prior_weight", 1.0 - w_cur) or (1.0 - w_cur))
    return {
        **indices,
        "offense_index": round(cur_off, 6),
        "defense_index": round(cur_def, 6),
        "full_strength_offense_index": round(full_off, 6),
        "full_strength_defense_index": round(full_def, 6),
        "current_offense_index": round(cur_off, 6),
        "current_defense_index": round(cur_def, 6),
        "injury_delta_offense": round(float(injury_delta_offense), 6),
        "injury_delta_defense": round(float(injury_delta_defense), 6),
        "blend_prior_weight": round(w_prior, 4),
        "blend_current_weight": round(w_cur, 4),
        # Pass through package hook; live loader may overwrite via qb_premium layer.
        "qb_premium": round(float(pkg.qb_premium), 6),
        "drivers": drivers,
        "source": str(source or pkg.source),
        "games_played": int(pkg.games_played),
        "as_of": str(pkg.as_of or ""),
        "version": str(pkg.version or EFFICIENCY_BACKBONE_VERSION),
        "off_epa_per_play": float(pkg.offense.epa_per_play),
        "def_epa_allowed_per_play": float(pkg.defense.epa_per_play),
        "pass_epa": float(pkg.offense.pass_epa),
        "run_epa": float(pkg.offense.run_epa),
        "early_down_epa": float(pkg.offense.early_down_epa),
        "st_epa_per_play": float(pkg.st_epa_per_play),
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
    pass_plays: int = 0,
    run_plays: int = 0,
    early_down_plays: int = 0,
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
        pass_plays=int(pass_plays or 0),
        run_plays=int(run_plays or 0),
        early_down_plays=int(early_down_plays or 0),
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

    pass_plays = int(_safe_float(row.get("pass_plays"), 0.0))
    run_plays = int(_safe_float(row.get("run_plays"), 0.0))
    early_down_plays = int(
        _safe_float(
            row.get("early_down_plays"),
            _safe_float(row.get("early_down_off_plays"), 0.0),
        )
    )
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

    # True splits when present; else default to overall EPA (labeled in drivers).
    off_pass_epa = row.get("pass_epa", row.get("pass_epa_offense"))
    off_run_epa = row.get("run_epa", row.get("run_epa_offense"))
    off_early_epa = row.get("early_down_epa", row.get("early_down_epa_offense"))
    def_pass_epa = row.get("pass_epa_allowed", row.get("pass_epa_defense_allowed"))
    def_run_epa = row.get("run_epa_allowed", row.get("run_epa_defense_allowed"))
    def_early_epa = row.get(
        "early_down_epa_allowed", row.get("early_down_epa_defense_allowed")
    )
    def_pass_plays = int(_safe_float(row.get("pass_plays_allowed"), pass_plays if def_pass_epa is not None else 0))
    def_run_plays = int(_safe_float(row.get("run_plays_allowed"), run_plays if def_run_epa is not None else 0))
    def_early_plays = int(
        _safe_float(
            row.get("early_down_plays_allowed"),
            early_down_plays if def_early_epa is not None else 0,
        )
    )

    offense = build_unit_from_rates(
        epa_per_play=off_epa,
        success_rate=_safe_float(row.get("success_rate_offense"), _LEAGUE_SUCCESS_RATE),
        explosive_rate=off_explosive,
        red_zone_td_rate=_safe_float(row.get("red_zone_td_rate"), _LEAGUE_RZ_TD_RATE),
        pressure_rate=_safe_float(
            row.get("pressure_rate_allowed", row.get("pressure_allowed")), 0.15
        ),
        plays=off_plays,
        pass_epa=_safe_float(off_pass_epa, off_epa) if off_pass_epa is not None else off_epa,
        run_epa=_safe_float(off_run_epa, off_epa) if off_run_epa is not None else off_epa,
        early_down_epa=(
            _safe_float(off_early_epa, off_epa) if off_early_epa is not None else off_epa
        ),
        late_down_conversion_rate=_safe_float(
            row.get("third_down_conversion_rate"), 0.40
        ),
        pass_plays=pass_plays if off_pass_epa is not None else 0,
        run_plays=run_plays if off_run_epa is not None else 0,
        early_down_plays=early_down_plays if off_early_epa is not None else 0,
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
        pass_epa=_safe_float(def_pass_epa, def_epa) if def_pass_epa is not None else def_epa,
        run_epa=_safe_float(def_run_epa, def_epa) if def_run_epa is not None else def_epa,
        early_down_epa=(
            _safe_float(def_early_epa, def_epa) if def_early_epa is not None else def_epa
        ),
        late_down_conversion_rate=_safe_float(
            row.get("third_down_conversion_rate_allowed"), 0.40
        ),
        pass_plays=def_pass_plays if def_pass_epa is not None else 0,
        run_plays=def_run_plays if def_run_epa is not None else 0,
        early_down_plays=def_early_plays if def_early_epa is not None else 0,
    )

    st_epa_val = _safe_float(st_epa if st_epa is not None else row.get("st_epa_per_play"), 0.0)
    st_plays = int(_safe_float(row.get("st_plays"), 0.0))
    # If ST EPA provided explicitly with no play count, treat as season-ok sample.
    if st_epa is not None or ("st_epa_per_play" in row and row.get("st_epa_per_play") is not None):
        if st_plays <= 0 and abs(st_epa_val) > 1e-12:
            st_plays = _THIN_ST_PLAYS  # season avg present → not missing
    st_index = _clamp(1.0 + st_epa_val * 0.55, 0.85, 1.15)

    plays_per_game = (
        (off_plays / games) if games > 0 and off_plays > 0 else _LEAGUE_PLAYS_PER_GAME
    )
    pace = plays_per_game / _LEAGUE_PLAYS_PER_GAME
    explosiveness = _rate_delta(offense.explosive_rate, _LEAGUE_EXPLOSIVE_PASS_RATE)

    drivers_preview = None
    pkg = TeamEfficiencyPackage(
        team=str(team),
        offense=offense,
        defense=defense,
        st_index=round(st_index, 6),
        st_epa_per_play=round(st_epa_val, 6),
        st_plays=int(st_plays),
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
            "has_true_pass_run_splits": bool(
                off_pass_epa is not None and off_run_epa is not None
            ),
            "has_early_down_epa": bool(off_early_epa is not None),
            "has_st_epa": bool(
                st_epa is not None
                or (
                    "st_epa_per_play" in row
                    and row.get("st_epa_per_play") is not None
                    and abs(st_epa_val) > 1e-12
                )
                or st_plays > 0
            ),
        },
    )
    drivers_preview = visible_drivers(pkg)
    pkg.notes["drivers"] = drivers_preview
    return pkg


def league_anchor_package(*, team: str = "LEAGUE") -> TeamEfficiencyPackage:
    """Neutral league-mean package used when continuity discounts prior travel."""
    return TeamEfficiencyPackage(
        team=team,
        offense=UnitEfficiency(),
        defense=UnitEfficiency(),
        st_index=1.0,
        st_epa_per_play=0.0,
        st_plays=0,
        pace=1.0,
        pass_rate=_LEAGUE_PASS_RATE,
        explosiveness=0.0,
        variance=uncertainty_from_games(0),
        qb_premium=0.0,
        games_played=0,
        source="league_anchor",
        notes={"role": "continuity_prior_anchor"},
    )


def blend_packages(
    prior: TeamEfficiencyPackage,
    current: TeamEfficiencyPackage,
    *,
    current_games: Optional[int] = None,
    prior_travel_weight: float = 1.0,
    continuity_score: Optional[float] = None,
    league_anchor: Optional[TeamEfficiencyPackage] = None,
) -> TeamEfficiencyPackage:
    """Blend prior-season → current-season packages with sample-aware weights.

    ``current_games`` overrides ``current.games_played`` for the blend weight
    (prefer schedule-completed REG games when the rolling window is noisy).

    Continuity prior-travel (does **not** replace games/8):
      w_current = games/8
      w_prior   = (1 - w_current) * prior_travel_weight
      w_anchor  = (1 - w_current) * (1 - prior_travel_weight)
      blended   = w_prior * prior + w_current * current + w_anchor * league_anchor

    Default ``prior_travel_weight=1.0`` preserves the #140 blend curve exactly.
    """
    games_for_weight = (
        int(current_games)
        if current_games is not None
        else int(current.games_played)
    )
    w_cur = prior_current_blend_weight(current_games=games_for_weight)
    travel = _clamp(float(prior_travel_weight), 0.0, 1.0)
    w_prior = (1.0 - w_cur) * travel
    w_anchor = (1.0 - w_cur) * (1.0 - travel)
    anchor = league_anchor or league_anchor_package(team=current.team or prior.team)

    def _blend_unit(
        a: UnitEfficiency, b: UnitEfficiency, c: UnitEfficiency
    ) -> UnitEfficiency:
        return UnitEfficiency(
            epa_per_play=(
                w_prior * a.epa_per_play + w_cur * b.epa_per_play + w_anchor * c.epa_per_play
            ),
            success_rate=(
                w_prior * a.success_rate
                + w_cur * b.success_rate
                + w_anchor * c.success_rate
            ),
            explosive_rate=(
                w_prior * a.explosive_rate
                + w_cur * b.explosive_rate
                + w_anchor * c.explosive_rate
            ),
            negative_rate=(
                w_prior * a.negative_rate
                + w_cur * b.negative_rate
                + w_anchor * c.negative_rate
            ),
            pass_epa=w_prior * a.pass_epa + w_cur * b.pass_epa + w_anchor * c.pass_epa,
            run_epa=w_prior * a.run_epa + w_cur * b.run_epa + w_anchor * c.run_epa,
            early_down_epa=(
                w_prior * a.early_down_epa
                + w_cur * b.early_down_epa
                + w_anchor * c.early_down_epa
            ),
            late_down_conversion_rate=(
                w_prior * a.late_down_conversion_rate
                + w_cur * b.late_down_conversion_rate
                + w_anchor * c.late_down_conversion_rate
            ),
            red_zone_td_rate=(
                w_prior * a.red_zone_td_rate
                + w_cur * b.red_zone_td_rate
                + w_anchor * c.red_zone_td_rate
            ),
            pressure_rate=(
                w_prior * a.pressure_rate
                + w_cur * b.pressure_rate
                + w_anchor * c.pressure_rate
            ),
            plays=int(a.plays + b.plays),
            pass_plays=int(a.pass_plays + b.pass_plays),
            run_plays=int(a.run_plays + b.run_plays),
            early_down_plays=int(a.early_down_plays + b.early_down_plays),
        )

    prior_idx = package_to_strength_indices(prior)
    current_idx = package_to_strength_indices(current)
    cont_score = (
        float(continuity_score)
        if continuity_score is not None
        else float((prior.notes or {}).get("continuity_score", travel) or travel)
    )
    try:
        from src.services.nfl_season_engine.continuity_score import (
            continuity_uncertainty_boost,
        )

        var_boost = continuity_uncertainty_boost(cont_score) if travel < 1.0 - 1e-12 else 0.0
    except Exception:
        var_boost = 0.0
    base_var = uncertainty_from_games(games_for_weight)
    variance = round(_clamp(base_var + var_boost, 0.55, 1.60), 4)

    continuity_status = (
        "applied"
        if travel < 1.0 - 1e-12 or continuity_score is not None
        else "stub_not_applied"
    )
    # If caller passed explicit travel=1.0 with a continuity_score, still mark applied.
    if continuity_score is not None:
        continuity_status = "applied"

    return TeamEfficiencyPackage(
        team=current.team or prior.team,
        offense=_blend_unit(prior.offense, current.offense, anchor.offense),
        defense=_blend_unit(prior.defense, current.defense, anchor.defense),
        st_index=(
            w_prior * prior.st_index + w_cur * current.st_index + w_anchor * anchor.st_index
        ),
        st_epa_per_play=(
            w_prior * prior.st_epa_per_play
            + w_cur * current.st_epa_per_play
            + w_anchor * anchor.st_epa_per_play
        ),
        st_plays=int(prior.st_plays + current.st_plays),
        pace=w_prior * prior.pace + w_cur * current.pace + w_anchor * anchor.pace,
        pass_rate=(
            w_prior * prior.pass_rate
            + w_cur * current.pass_rate
            + w_anchor * anchor.pass_rate
        ),
        explosiveness=(
            w_prior * prior.explosiveness
            + w_cur * current.explosiveness
            + w_anchor * anchor.explosiveness
        ),
        # Uncertainty tracks current-season sample + continuity discount.
        # Never tighten because league completed_reg flipped from 0→1.
        variance=variance,
        # QB premium applied post-blend by qb_premium layer (not continuity).
        qb_premium=0.0,
        games_played=int(games_for_weight),
        as_of=current.as_of or prior.as_of,
        version=EFFICIENCY_BACKBONE_VERSION,
        source=BACKBONE_SOURCE_BLEND if w_cur > 0 else str(prior.source or BACKBONE_SOURCE_PACKAGED),
        prior_season=int(prior.prior_season or 0),
        notes={
            "blend_current_weight": round(w_cur, 4),
            "blend_prior_weight": round(w_prior, 4),
            "blend_anchor_weight": round(w_anchor, 4),
            "prior_travel_weight": round(travel, 4),
            "continuity_score": round(cont_score, 4) if continuity_score is not None else None,
            "prior_source": prior.source,
            "current_source": current.source,
            "prior_offense_index": float(prior_idx["offense_index"]),
            "prior_defense_index": float(prior_idx["defense_index"]),
            "current_component_offense_index": float(current_idx["offense_index"]),
            "current_component_defense_index": float(current_idx["defense_index"]),
            "qb_premium_status": "stub_not_applied",
            "continuity_status": continuity_status,
            # Past SOS status lives on prior package notes when applied.
            "true_time_of_game_sos_status": str(
                (prior.notes or {}).get("past_sos", {}).get("status")
                or (current.notes or {}).get("past_sos", {}).get("status")
                or "thin_unavailable"
            ),
            "past_sos_prior": (prior.notes or {}).get("past_sos"),
            "continuity": (prior.notes or {}).get("continuity"),
        },
    )


def true_pr_drivers(
    pkg: TeamEfficiencyPackage,
    *,
    prior_offense_index: Optional[float] = None,
    prior_defense_index: Optional[float] = None,
    current_component_offense_index: Optional[float] = None,
    current_component_defense_index: Optional[float] = None,
    injury_delta_offense: float = 0.0,
    injury_delta_defense: float = 0.0,
    injury_status: str = "structure_ready_zero",
) -> Dict[str, Any]:
    """Minimum-viable inspectable drivers for true PR / Edge Board / ops."""
    base = visible_drivers(pkg)
    w_cur = float(pkg.notes.get("blend_current_weight", 0.0) or 0.0)
    w_prior = float(pkg.notes.get("blend_prior_weight", 1.0 - w_cur) or (1.0 - w_cur))
    if prior_offense_index is None:
        prior_offense_index = pkg.notes.get("prior_offense_index")
    if prior_defense_index is None:
        prior_defense_index = pkg.notes.get("prior_defense_index")
    if current_component_offense_index is None:
        current_component_offense_index = pkg.notes.get("current_component_offense_index")
    if current_component_defense_index is None:
        current_component_defense_index = pkg.notes.get("current_component_defense_index")
    games = int(pkg.games_played)
    cont_notes = pkg.notes.get("continuity") if isinstance(pkg.notes.get("continuity"), dict) else {}
    cont_status = str(pkg.notes.get("continuity_status") or "stub_not_applied")
    travel = pkg.notes.get("prior_travel_weight")
    if travel is None and cont_notes:
        travel = cont_notes.get("prior_travel_weight")
    w_anchor = float(pkg.notes.get("blend_anchor_weight", 0.0) or 0.0)
    return {
        **base,
        "blend": {
            "w_prior": round(w_prior, 4),
            "w_current": round(w_cur, 4),
            "w_anchor": round(w_anchor, 4),
            "prior_travel_weight": (
                round(float(travel), 4) if travel is not None else None
            ),
            "prior_offense_index": (
                round(float(prior_offense_index), 6)
                if prior_offense_index is not None
                else None
            ),
            "prior_defense_index": (
                round(float(prior_defense_index), 6)
                if prior_defense_index is not None
                else None
            ),
            "current_component_offense_index": (
                round(float(current_component_offense_index), 6)
                if current_component_offense_index is not None
                else None
            ),
            "current_component_defense_index": (
                round(float(current_component_defense_index), 6)
                if current_component_defense_index is not None
                else None
            ),
        },
        "injury_availability_delta": {
            "offense": round(float(injury_delta_offense), 6),
            "defense": round(float(injury_delta_defense), 6),
            "status": str(injury_status),
        },
        "uncertainty": {
            "variance": round(float(pkg.variance), 4),
            "games_played": games,
            "sample_note": "wide_early" if games <= 4 else "tightening",
            "continuity_boost": round(
                float(pkg.variance) - uncertainty_from_games(games), 4
            )
            if float(pkg.variance) > uncertainty_from_games(games) + 1e-9
            else 0.0,
        },
        "stubs": {
            "qb_premium": "stub_not_applied",
            "continuity": cont_status,
            "injury_at_time_depth": "stub_not_applied",
            "full_venue_model": str(
                (pkg.notes.get("past_sos") or {}).get("full_venue_model")
                or "stub_not_applied"
            ),
            "true_time_of_game_sos": str(
                (pkg.notes.get("past_sos") or {}).get("status") or "thin_unavailable"
            ),
        },
        "past_sos": dict(pkg.notes.get("past_sos") or {"status": "thin_unavailable"}),
        "continuity": dict(cont_notes)
        if cont_notes
        else {"status": cont_status},
    }


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
        st_key_present = "st_epa_per_play" in r
        out[team] = build_package_from_season_row(
            team,
            r,
            as_of=as_of,
            source=source,
            prior_season=prior_season,
            league_off_epa=league_off,
            league_def_epa=league_def,
            st_epa=_safe_float(r.get("st_epa_per_play"), 0.0) if st_key_present else None,
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
