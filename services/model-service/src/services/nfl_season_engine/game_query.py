"""Query API: future game → player box-score distributions.

Runs Layers 2–4 for ``n_replicates`` Monte Carlo draws at the current
(universe) strength book — no in-path evolution, since the query is for a
single future game's marginal distribution. Season-long coherence lives in
``season_sim.simulate_full_season``; this endpoint answers "what does the
box look like for this matchup right now?"
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.nfl_season_engine.calibration import ENGINE_VERSION, LEAGUE_BASE_PASS_RATE
from src.services.nfl_season_engine.coaching_tendencies import (
    explain_tendency_effects,
    profile_for_team,
)
from src.services.nfl_season_engine.depth_chart import (
    apply_depth_chart_roster_book,
    apply_weekly_role_volatility,
    classify_team_depth,
    depth_structure_diagnostics,
)
from src.services.nfl_season_engine.game_script import (
    build_game_script,
    play_mix_for_side,
    summarize_script_distribution,
)
from src.services.nfl_season_engine.injury_paths import (
    InjuryPath,
    apply_injury_paths_for_week,
    injury_paths_to_dicts,
    summarize_adjustments,
)
from src.services.nfl_season_engine.player_usage import (
    allocate_game_usage,
    share_integrity_summary,
    usage_share_diagnostics,
)
from src.services.nfl_season_engine.production import (
    box_score_to_stat_dict,
    produce_box_scores,
)
from src.services.nfl_season_engine.red_zone import (
    rz_pass_rate_from_script,
    scoring_usage_diagnostics,
)
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    GameBoxProjection,
    ScheduledGame,
    dist_block,
)
from src.services.nfl_season_engine.usage_roles import annotate_usage_roles

DEFAULT_SEASON_ENGINE_VERSION = ENGINE_VERSION

_POSITION_STATS = {
    "QB": ("pass_yards", "pass_tds", "ints", "rush_yards"),
    "RB": ("rush_yards", "rush_tds", "rec_yards", "receptions"),
    "WR": ("rec_yards", "receptions", "rec_tds"),
    "TE": ("rec_yards", "receptions", "rec_tds"),
}


def _find_game(
    universe: EngineUniverse,
    *,
    home_team: str,
    away_team: str,
    week: Optional[int] = None,
    game_id: Optional[str] = None,
) -> ScheduledGame:
    home = "LA" if home_team == "LAR" else home_team
    away = "LA" if away_team == "LAR" else away_team
    candidates = [
        g
        for g in universe.schedule
        if g.home_team == home and g.away_team == away
        and (week is None or g.week == week)
        and (game_id is None or g.game_id == game_id)
    ]
    if candidates:
        return candidates[0]
    # Synthetic future game when not on the loaded schedule.
    return ScheduledGame(
        season=universe.season,
        week=int(week or 1),
        game_id=game_id or f"{universe.season}-W{int(week or 1):02d}-{away}@{home}",
        home_team=home,
        away_team=away,
    )


def _summarize(values: Sequence[float]) -> Dict[str, float]:
    if not values:
        return dist_block(0.0, 0.0, 0.0, 0.0, 0.0)
    ordered = sorted(values)
    n = len(ordered)
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) if n > 1 else 0.0
    return dist_block(
        mean,
        std,
        ordered[max(0, int(round((n - 1) * 0.10)))],
        ordered[max(0, int(round((n - 1) * 0.50)))],
        ordered[max(0, int(round((n - 1) * 0.90)))],
    )


def _coaching_tendency_diagnostics(
    *,
    game: ScheduledGame,
    scripts: Sequence[Any],
    week_strengths: Mapping[str, Any],
    rz_pass_home: Sequence[float],
    rz_pass_away: Sequence[float],
) -> Dict[str, Any]:
    """Mean tendency deltas + sample explain blocks for include_diagnostics."""
    home_str = week_strengths.get(game.home_team)
    away_str = week_strengths.get(game.away_team)
    home_strength_bias = float(getattr(home_str, "pass_rate_bias", 0.0) or 0.0)
    away_strength_bias = float(getattr(away_str, "pass_rate_bias", 0.0) or 0.0)
    home_before = LEAGUE_BASE_PASS_RATE + home_strength_bias
    away_before = LEAGUE_BASE_PASS_RATE + away_strength_bias
    n = max(1, len(scripts))
    home_pass = sum(s.home_pass_rate for s in scripts) / n
    away_pass = sum(s.away_pass_rate for s in scripts) / n
    home_early = sum(s.home_early_down_pass_rate for s in scripts) / n
    away_early = sum(s.away_early_down_pass_rate for s in scripts) / n
    home_hurry = sum(s.home_hurry_up for s in scripts) / n
    away_hurry = sum(s.away_hurry_up for s in scripts) / n
    home_rz = sum(rz_pass_home) / max(1, len(rz_pass_home))
    away_rz = sum(rz_pass_away) / max(1, len(rz_pass_away))
    sample = scripts[0] if scripts else None
    out: Dict[str, Any] = {
        "home": {
            "pass_rate_mean": round(home_pass, 4),
            "early_down_pass_rate_mean": round(home_early, 4),
            "hurry_up_mean": round(home_hurry, 4),
            "rz_pass_rate_mean": round(home_rz, 4),
            "pass_rate_bias_applied": profile_for_team(game.home_team).pass_rate_bias,
            "script_aggression": profile_for_team(game.home_team).script_aggression,
            "rz_pass_bias_applied": profile_for_team(game.home_team).rz_pass_bias,
            "base_pass_rate_before_coaching_bias": round(home_before, 4),
        },
        "away": {
            "pass_rate_mean": round(away_pass, 4),
            "early_down_pass_rate_mean": round(away_early, 4),
            "hurry_up_mean": round(away_hurry, 4),
            "rz_pass_rate_mean": round(away_rz, 4),
            "pass_rate_bias_applied": profile_for_team(game.away_team).pass_rate_bias,
            "script_aggression": profile_for_team(game.away_team).script_aggression,
            "rz_pass_bias_applied": profile_for_team(game.away_team).rz_pass_bias,
            "base_pass_rate_before_coaching_bias": round(away_before, 4),
        },
    }
    if sample is not None:
        out["sample"] = {
            "home": explain_tendency_effects(
                game.home_team,
                base_pass_rate_before_coaching=home_before,
                detail=sample.home_script_detail,
                intensity=sample.home_script_intensity,
                time_bucket=sample.time_bucket,
                pass_rate=sample.home_pass_rate,
                early_down_pass_rate=sample.home_early_down_pass_rate,
                hurry_up=sample.home_hurry_up,
                rz_pass_rate=rz_pass_home[0] if rz_pass_home else None,
            ),
            "away": explain_tendency_effects(
                game.away_team,
                base_pass_rate_before_coaching=away_before,
                detail=sample.away_script_detail,
                intensity=sample.away_script_intensity,
                time_bucket=sample.time_bucket,
                pass_rate=sample.away_pass_rate,
                early_down_pass_rate=sample.away_early_down_pass_rate,
                hurry_up=sample.away_hurry_up,
                rz_pass_rate=rz_pass_away[0] if rz_pass_away else None,
            ),
        }
    return out


def _aggregate_play_mix(scripts: Sequence[Any], side: str) -> Dict[str, Any]:
    """Mean play-mix + modal script detail / time bucket across MC scripts."""
    if not scripts:
        return {}
    n = len(scripts)
    if side == "home":
        pass_rates = [s.home_pass_rate for s in scripts]
        early = [s.home_early_down_pass_rate for s in scripts]
        hurry = [s.home_hurry_up for s in scripts]
        inten = [s.home_script_intensity for s in scripts]
        details = [s.home_script_detail for s in scripts]
        states = [s.home_script for s in scripts]
    else:
        pass_rates = [s.away_pass_rate for s in scripts]
        early = [s.away_early_down_pass_rate for s in scripts]
        hurry = [s.away_hurry_up for s in scripts]
        inten = [s.away_script_intensity for s in scripts]
        details = [s.away_script_detail for s in scripts]
        states = [s.away_script for s in scripts]
    buckets = [s.time_bucket for s in scripts]

    def _mode(vals: Sequence[str]) -> str:
        counts: Dict[str, int] = defaultdict(int)
        for v in vals:
            counts[str(v)] += 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    return {
        "pass_rate_mean": round(sum(pass_rates) / n, 4),
        "run_rate_mean": round(1.0 - (sum(pass_rates) / n), 4),
        "early_down_pass_rate_mean": round(sum(early) / n, 4),
        "hurry_up_mean": round(sum(hurry) / n, 4),
        "script_intensity_mean": round(sum(inten) / n, 4),
        "script_state_mode": _mode(states),
        "script_detail_mode": _mode(details),
        "time_bucket_mode": _mode(buckets),
        "minutes_remaining_mean": round(sum(s.minutes_remaining for s in scripts) / n, 2),
    }


def project_game_player_boxes(
    universe: EngineUniverse,
    *,
    home_team: str,
    away_team: str,
    week: Optional[int] = None,
    game_id: Optional[str] = None,
    n_replicates: int = 500,
    seed: int = 7,
    engine_version: str = DEFAULT_SEASON_ENGINE_VERSION,
    injury_paths: Optional[Sequence[InjuryPath]] = None,
    include_diagnostics: bool = False,
) -> GameBoxProjection:
    """Monte Carlo player box projections for one future game.

    When ``include_diagnostics`` is True, attach structured usage shares,
    script/personnel state, share-integrity checks, and injury availability
    applied for the query week (kept off by default to avoid bloating
    responses).
    """
    n_replicates = max(50, int(n_replicates))
    game = _find_game(
        universe,
        home_team=home_team,
        away_team=away_team,
        week=week,
        game_id=game_id,
    )
    rng = random.Random(seed)
    paths = list(injury_paths or [])
    # Depth-chart base splits for the two clubs, one week-volatility draw
    # (seeded), then injury shocks — mirrors season-path Layer-3 ordering.
    focus_book = {
        game.home_team: list(universe.rosters.get(game.home_team, [])),
        game.away_team: list(universe.rosters.get(game.away_team, [])),
    }
    base_rosters, base_structures = apply_depth_chart_roster_book(focus_book)
    vol_rng = random.Random(seed ^ (game.week * 1_000_003))
    vol_rosters, vol_transitions = apply_weekly_role_volatility(
        base_rosters,
        week=game.week,
        rng=vol_rng,
        structures=base_structures,
    )
    # Keep full book for injury lookup; overlay the two adjusted teams.
    query_rosters = {t: list(r) for t, r in universe.rosters.items()}
    query_rosters.update(vol_rosters)
    week_rosters, week_strengths, adjustments = apply_injury_paths_for_week(
        query_rosters,
        universe.strengths,
        paths,
        week=game.week,
    )

    scripts = []
    accum: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    meta: Dict[str, Dict[str, str]] = {}
    usage_role_by_key: Dict[str, str] = {}
    personnel_by_key: Dict[str, str] = {}
    script_state_by_key: Dict[str, str] = {}
    script_detail_by_key: Dict[str, str] = {}
    scoring_role_by_key: Dict[str, str] = {}
    rz_accum: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    rz_pass_home: List[float] = []
    rz_pass_away: List[float] = []
    # Neutral-script share dump for inspectability (pre-MC).
    home_roles = annotate_usage_roles(week_rosters.get(game.home_team, []))
    away_roles = annotate_usage_roles(week_rosters.get(game.away_team, []))
    for role in list(home_roles) + list(away_roles):
        usage_role_by_key[role.player_key] = role.usage_role

    for _ in range(n_replicates):
        script, _outcome = build_game_script(game, week_strengths, rng=rng, realized=True)
        scripts.append(script)
        usage = allocate_game_usage(script, week_rosters, rng=rng)
        boxes = produce_box_scores(
            usage_rows=usage,
            roles=week_rosters,
            script=script,
            strengths=week_strengths,
            rng=rng,
        )
        rz_pass_home.append(
            rz_pass_rate_from_script(
                base_team_pass_rate=script.home_pass_rate,
                detail=script.home_script_detail,  # type: ignore[arg-type]
                intensity=script.home_script_intensity,
                time_bucket=script.time_bucket,  # type: ignore[arg-type]
                team=script.home_team,
            )
        )
        rz_pass_away.append(
            rz_pass_rate_from_script(
                base_team_pass_rate=script.away_pass_rate,
                detail=script.away_script_detail,  # type: ignore[arg-type]
                intensity=script.away_script_intensity,
                time_bucket=script.time_bucket,  # type: ignore[arg-type]
                team=script.away_team,
            )
        )
        for u in usage:
            if u.usage_role:
                usage_role_by_key[u.player_key] = u.usage_role
            if u.personnel:
                personnel_by_key[u.player_key] = u.personnel
            script_state_by_key[u.player_key] = u.script
            if u.script_detail:
                script_detail_by_key[u.player_key] = u.script_detail
            if u.scoring_role:
                scoring_role_by_key[u.player_key] = u.scoring_role
            rz_accum[u.player_key]["rz_carries_i20"].append(float(u.rz_carries_i20))
            rz_accum[u.player_key]["rz_carries_i10"].append(float(u.rz_carries_i10))
            rz_accum[u.player_key]["rz_targets_i20"].append(float(u.rz_targets_i20))
            rz_accum[u.player_key]["rz_targets_i10"].append(float(u.rz_targets_i10))
            rz_accum[u.player_key]["td_opportunity_share"].append(
                float(u.td_opportunity_share)
            )
        for box in boxes:
            meta[box.player_key] = {
                "player_key": box.player_key,
                "player_name": box.player_name,
                "team": box.team,
                "position": box.position,
            }
            stats = box_score_to_stat_dict(box)
            for k, v in stats.items():
                accum[box.player_key][k].append(float(v))
            # Always keep full raw counters for transparency.
            accum[box.player_key]["pass_attempts"].append(float(box.pass_attempts))
            accum[box.player_key]["carries"].append(float(box.carries))
            accum[box.player_key]["targets"].append(float(box.targets))

    players: List[Dict[str, Any]] = []
    for key, info in meta.items():
        pos = info["position"]
        wanted = _POSITION_STATS.get(pos, ("rec_yards", "receptions", "rec_tds"))
        distributions = {stat: _summarize(accum[key].get(stat, [])) for stat in wanted}
        # Attach volume context.
        distributions["pass_attempts"] = _summarize(accum[key].get("pass_attempts", []))
        distributions["carries"] = _summarize(accum[key].get("carries", []))
        distributions["targets"] = _summarize(accum[key].get("targets", []))
        point = {stat: distributions[stat]["mean"] for stat in wanted}
        players.append(
            {
                **info,
                "usage_role": usage_role_by_key.get(key, ""),
                "personnel": personnel_by_key.get(key, ""),
                "script": script_state_by_key.get(key, ""),
                "script_detail": script_detail_by_key.get(key, ""),
                "scoring_role": scoring_role_by_key.get(key, ""),
                "point_estimate": point,
                "distributions": distributions,
            }
        )

    def _sort_key(row: Dict[str, Any]) -> float:
        pe = row.get("point_estimate") or {}
        pos = row.get("position")
        if pos == "QB":
            return float(pe.get("pass_yards") or 0.0)
        if pos == "RB":
            return float(pe.get("rush_yards") or 0.0)
        return float(pe.get("rec_yards") or 0.0)

    players.sort(key=_sort_key, reverse=True)

    on_schedule = any(
        g.home_team == game.home_team
        and g.away_team == game.away_team
        and g.week == game.week
        for g in universe.schedule
    )
    notes = {
        **dict(universe.notes),
        "query_mode": "single_game_marginal_mc",
        "layers": (
            "1=injury-adjusted strength → 2=game_script → 3=player_usage → 4=production "
            "(strengths frozen at query-time book + week injury shocks)"
        ),
        "schedule_match": "on_loaded_schedule" if on_schedule else "synthetic_matchup",
    }
    if paths:
        notes["injury_path_count"] = str(len(paths))
        notes["injury_active_adjustments"] = str(len(adjustments))

    diagnostics: Dict[str, Any] = {}
    if include_diagnostics:
        focus = {
            game.home_team: week_rosters.get(game.home_team, []),
            game.away_team: week_rosters.get(game.away_team, []),
        }
        diagnostics = {
            "usage_shares_home": usage_share_diagnostics(
                home_roles, script="neutral", pass_rate=0.58
            ),
            "usage_shares_away": usage_share_diagnostics(
                away_roles, script="neutral", pass_rate=0.58
            ),
            "share_integrity_home": share_integrity_summary(
                home_roles, script="neutral", pass_rate=0.58
            ),
            "share_integrity_away": share_integrity_summary(
                away_roles, script="neutral", pass_rate=0.58
            ),
            "injury_paths": injury_paths_to_dicts(paths) if paths else [],
            "injury_adjustments": summarize_adjustments(adjustments),
            "game_script_summary": summarize_script_distribution(scripts),
            "schedule_match": notes["schedule_match"],
            "seed": seed,
            # Additive v1.5 depth-chart / committee / volatility fields.
            "depth_structure": {
                game.home_team: classify_team_depth(
                    game.home_team, week_rosters.get(game.home_team, [])
                ).to_dict(),
                game.away_team: classify_team_depth(
                    game.away_team, week_rosters.get(game.away_team, [])
                ).to_dict(),
            },
            "depth_structure_detail": depth_structure_diagnostics(focus),
            "role_transitions": [t.to_dict() for t in vol_transitions if t.team in focus][
                :40
            ],
            # Additive v1.6 play-calling / script detail fields.
            "play_mix_home": _aggregate_play_mix(scripts, "home"),
            "play_mix_away": _aggregate_play_mix(scripts, "away"),
            "play_mix_sample": {
                "home": play_mix_for_side(scripts[0], "home") if scripts else {},
                "away": play_mix_for_side(scripts[0], "away") if scripts else {},
            },
            # Additive v1.7 red-zone / scoring-usage fields.
            "red_zone": {
                "home": {
                    "rz_pass_rate_mean": round(sum(rz_pass_home) / max(1, len(rz_pass_home)), 4),
                    "rz_run_rate_mean": round(
                        1.0 - (sum(rz_pass_home) / max(1, len(rz_pass_home))), 4
                    ),
                },
                "away": {
                    "rz_pass_rate_mean": round(sum(rz_pass_away) / max(1, len(rz_pass_away)), 4),
                    "rz_run_rate_mean": round(
                        1.0 - (sum(rz_pass_away) / max(1, len(rz_pass_away))), 4
                    ),
                },
                "players": [
                    {
                        "player_key": key,
                        "player_name": meta[key]["player_name"],
                        "team": meta[key]["team"],
                        "position": meta[key]["position"],
                        "usage_role": usage_role_by_key.get(key, ""),
                        "scoring_role": scoring_role_by_key.get(key, ""),
                        "rz_carries_i20": _summarize(rz_accum[key].get("rz_carries_i20", [])),
                        "rz_carries_i10": _summarize(rz_accum[key].get("rz_carries_i10", [])),
                        "rz_targets_i20": _summarize(rz_accum[key].get("rz_targets_i20", [])),
                        "rz_targets_i10": _summarize(rz_accum[key].get("rz_targets_i10", [])),
                        "td_opportunity_share": _summarize(
                            rz_accum[key].get("td_opportunity_share", [])
                        ),
                    }
                    for key in meta
                ],
            },
            "scoring_usage": {
                "home": scoring_usage_diagnostics(
                    home_roles, team=game.home_team
                ),
                "away": scoring_usage_diagnostics(
                    away_roles, team=game.away_team
                ),
            },
            # Additive v1.8 coaching / tendency fields.
            "coaching_profile": {
                "home": profile_for_team(game.home_team).to_dict(),
                "away": profile_for_team(game.away_team).to_dict(),
            },
            "tendency_effects": _coaching_tendency_diagnostics(
                game=game,
                scripts=scripts,
                week_strengths=week_strengths,
                rz_pass_home=rz_pass_home,
                rz_pass_away=rz_pass_away,
            ),
        }

    return GameBoxProjection(
        season=universe.season,
        week=game.week,
        game_id=game.game_id,
        home_team=game.home_team,
        away_team=game.away_team,
        n_replicates=n_replicates,
        engine_version=engine_version,
        game_script_summary=summarize_script_distribution(scripts),
        players=players,
        notes=notes,
        diagnostics=diagnostics,
    )
