"""Phase 3 — historical replay protocol + scorecard (no look-ahead).

Cutoff rule (documented + enforced):
  * Seasons ≤2024: nflverse depth_charts ``week=1`` + ``game_type=REG``
    (earliest regular-season published depth; standard preseason→W1 artifact).
  * Season ≥2025: latest nflverse ``dt`` on or before Labor Day Monday of
    that season year (pre-W1 kickoff window).

Strength priors: **prior season Y−1 only** (play-weighted EPA from
``nfl_dp_team_situational_weekly``). Current-season rolling features are
forbidden — week-1 rolling already embeds Y's week-1 games.

This module never calibrates knobs on season Y and scores Y in the same pass.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.depth_chart import apply_depth_chart_roster_book
from src.services.nfl_season_engine.loaders import (
    NFL_TEAMS,
    SCHEDULE_SOURCE_DB,
    STRENGTH_SOURCE_PACKAGED_EPA,
    _rosters_from_depth_rows,
    normalize_team_abbr,
)
from src.services.nfl_season_engine.player_regression import (
    apply_process_priors_to_roster_book,
)
from src.services.nfl_season_engine.player_usage import (
    anchor_roster_book_to_prior_usage_shares,
)
from src.services.nfl_season_engine.season_sim import simulate_full_season
from src.services.nfl_season_engine.team_strength import initialize_strengths
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    ScheduledGame,
    SeasonSimResult,
)
from src.services.nfl_season_engine.usage_roles import annotate_roster_book

REPLAY_PROTOCOL_VERSION = "nfl-historical-replay-v1-20260809"
NFLVERSE_DEPTH_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "depth_charts/depth_charts_{season}.parquet"
)
SKILL_POSITIONS = ("QB", "RB", "WR", "TE")
DEFAULT_HIST_DEPTH_DIR = (
    Path(__file__).resolve().parent / "data" / "historical"
)

# Labor Day Monday approximations used as 2025+ preseason cutoff (inclusive).
# Documented: latest depth snapshot with dt.date() <= this day.
PRESEASON_CUTOFF_BY_SEASON: Dict[int, str] = {
    2025: "2025-09-01",
    2026: "2026-09-07",
}

TEAM_MAP = {
    "LAR": "LA",
    "AZ": "ARI",
    "WSH": "WAS",
    "JAC": "JAX",
    "OAK": "LV",  # Raiders relocation — historical schedules
    "SD": "LAC",  # Chargers relocation
    "STL": "LA",  # Rams historical (pre-2016; rare in 2019+ packs)
}


# ---------------------------------------------------------------------------
# Scorecard math
# ---------------------------------------------------------------------------


def mae(errors: Sequence[float]) -> float:
    vals = [float(x) for x in errors if math.isfinite(float(x))]
    if not vals:
        return float("nan")
    return sum(abs(v) for v in vals) / len(vals)


def bias(errors: Sequence[float]) -> float:
    """Mean signed error = mean(pred − actual)."""
    vals = [float(x) for x in errors if math.isfinite(float(x))]
    if not vals:
        return float("nan")
    return sum(vals) / len(vals)


def spearman_rank_corr(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman ρ without scipy. Returns NaN if undefined."""
    n = min(len(x), len(y))
    if n < 2:
        return float("nan")
    xs = [float(x[i]) for i in range(n)]
    ys = [float(y[i]) for i in range(n)]
    if any(not math.isfinite(v) for v in xs + ys):
        return float("nan")

    def _ranks(vals: Sequence[float]) -> List[float]:
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        ranks = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        return ranks

    rx, ry = _ranks(xs), _ranks(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    deny = math.sqrt(sum((b - my) ** 2 for b in ry))
    if denx <= 1e-12 or deny <= 1e-12:
        return float("nan")
    return num / (denx * deny)


def score_vector(
    pred: Mapping[str, float],
    actual: Mapping[str, float],
) -> Dict[str, float]:
    keys = []
    for k in sorted(set(pred) & set(actual)):
        try:
            pv = float(pred[k])
            av = float(actual[k])
        except (TypeError, ValueError):
            continue
        if math.isfinite(pv) and math.isfinite(av):
            keys.append(k)
    errs = [float(pred[k]) - float(actual[k]) for k in keys]
    p = [float(pred[k]) for k in keys]
    a = [float(actual[k]) for k in keys]
    return {
        "n": float(len(keys)),
        "mae": mae(errs),
        "bias": bias(errs),
        "rank_corr": spearman_rank_corr(p, a),
    }


# ---------------------------------------------------------------------------
# Depth packaging (nflverse → engine rows)
# ---------------------------------------------------------------------------


def _normalize_team(raw: str) -> str:
    token = str(raw or "").strip().upper()
    return TEAM_MAP.get(token, normalize_team_abbr(token))


def labor_day_cutoff(season: int) -> date:
    """Return documented preseason cutoff date for season ≥2025."""
    if season in PRESEASON_CUTOFF_BY_SEASON:
        return date.fromisoformat(PRESEASON_CUTOFF_BY_SEASON[season])
    # First Monday of September
    d = date(int(season), 9, 1)
    # Monday=0 in weekday()
    while d.weekday() != 0:
        d = date.fromordinal(d.toordinal() + 1)
    return d


def download_nflverse_depth(season: int, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"depth_charts_{int(season)}.parquet"
    if out.is_file() and out.stat().st_size > 1000:
        return out
    url = NFLVERSE_DEPTH_URL.format(season=int(season))
    urllib.request.urlretrieve(url, out)
    return out


def package_historical_depth_rows(
    season: int,
    *,
    parquet_path: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Extract no-look-ahead skill depth rows for season Y."""
    import polars as pl

    df = pl.read_parquet(str(parquet_path))
    cutoff_rule = ""
    as_of = ""
    week = 1

    if "dt" in df.columns:
        cutoff = labor_day_cutoff(season)
        cutoff_rule = (
            f"latest nflverse dt on or before {cutoff.isoformat()} "
            "(Labor Day / pre-W1 window)"
        )
        # Parse dt to date
        dts = df.select(pl.col("dt").cast(pl.Utf8)).to_series().to_list()
        eligible = []
        for raw in dts:
            try:
                token = str(raw).replace("Z", "+00:00")
                dd = datetime.fromisoformat(token).date()
            except ValueError:
                continue
            if dd <= cutoff:
                eligible.append(str(raw))
        if not eligible:
            # Fall back to earliest August snapshot — still preseason-ish; flag gap.
            cutoff_rule += "; FALLBACK earliest August dt (no pre-Labor-Day rows)"
            august = [
                str(r)
                for r in dts
                if str(r).startswith(f"{season}-08")
            ]
            if not august:
                raise ValueError(
                    f"No preseason depth snapshots for season={season} before "
                    f"{cutoff.isoformat()}"
                )
            latest_dt = min(august)
        else:
            latest_dt = max(eligible)
        as_of = str(latest_dt)[:10]
        skill = df.filter(
            (pl.col("dt").cast(pl.Utf8) == latest_dt)
            & (pl.col("pos_abb").is_in(list(SKILL_POSITIONS)))
        )
        team_col, pos_col, rank_col, name_col, id_col = (
            "team",
            "pos_abb",
            "pos_rank",
            "player_name",
            "gsis_id",
        )
    else:
        cutoff_rule = "nflverse week=1 game_type=REG (preseason→W1 published depth)"
        as_of = f"{season}-W1-REG"
        skill = df.filter(
            (pl.col("week") == 1)
            & (pl.col("game_type") == "REG")
            & (pl.col("depth_position").is_in(list(SKILL_POSITIONS)))
        )
        team_col, pos_col, rank_col, name_col, id_col = (
            "club_code",
            "depth_position",
            "depth_team",
            "full_name",
            "gsis_id",
        )

    rows_out: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, int]] = set()
    sort_cols = [team_col, pos_col, rank_col]
    for row in skill.sort(sort_cols).iter_rows(named=True):
        team = _normalize_team(str(row.get(team_col) or ""))
        pos = str(row.get(pos_col) or "").strip().upper()
        try:
            rank = int(row.get(rank_col) or 0)
        except (TypeError, ValueError):
            continue
        name = str(row.get(name_col) or "").strip()
        if team not in NFL_TEAMS or pos not in SKILL_POSITIONS or rank < 1 or rank > 3:
            continue
        if not name:
            continue
        key = (team, pos, rank)
        if key in seen:
            continue
        seen.add(key)
        pid = str(row.get(id_col) or "").strip()
        rows_out.append(
            {
                "team": team,
                "position": pos,
                "depth_order": rank,
                "player_id": pid or f"{team}-{pos}-{rank}",
                "player_name": name,
                "depth_slot": {1: "starter", 2: "backup", 3: "rotation"}.get(
                    rank, "depth"
                ),
                "role_confidence": 0.85 if rank == 1 else (0.65 if rank == 2 else 0.5),
            }
        )

    teams = {r["team"] for r in rows_out}
    full = 0
    for team in teams:
        has = {(r["position"], r["depth_order"]) for r in rows_out if r["team"] == team}
        if all((p, 1) in has for p in SKILL_POSITIONS):
            full += 1

    blob = json.dumps(rows_out, sort_keys=True).encode("utf-8")
    sha = hashlib.sha256(blob).hexdigest()
    snapshot_id = f"nfl-depth-{season}-w{week}-{as_of.replace('-', '')}-{sha[:12]}"
    meta = {
        "season": int(season),
        "week": week,
        "as_of": as_of,
        "cutoff_rule": cutoff_rule,
        "source": "nflverse_depth_charts_historical",
        "upstream": "nflverse/nflverse-data depth_charts release",
        "snapshot_id": snapshot_id,
        "pack_sha256": sha,
        "team_count": len(teams),
        "row_count": len(rows_out),
        "full_skill_starter_teams": full,
        "look_ahead": False,
        "protocol_version": REPLAY_PROTOCOL_VERSION,
    }
    if full < 28:
        meta["coverage_warning"] = (
            f"Only {full}/32 teams have QB1+RB1+WR1+TE1 at cutoff"
        )
    return rows_out, meta


def write_historical_depth_pack(
    season: int,
    *,
    cache_dir: Path,
    out_dir: Path = DEFAULT_HIST_DEPTH_DIR,
) -> Path:
    parquet = download_nflverse_depth(season, cache_dir)
    rows, meta = package_historical_depth_rows(season, parquet_path=parquet)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"nfl_depth_chart_{int(season)}_w1.json"
    payload = {**meta, "rows": rows}
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def load_historical_depth_pack(
    season: int,
    *,
    pack_dir: Path = DEFAULT_HIST_DEPTH_DIR,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    path = pack_dir / f"nfl_depth_chart_{int(season)}_w1.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = list(payload.get("rows") or [])
    meta = {k: v for k, v in payload.items() if k != "rows"}
    if meta.get("look_ahead") is True:
        raise ValueError(f"Depth pack marked look_ahead=true: {path}")
    return rows, meta


# ---------------------------------------------------------------------------
# Prior-season strength (no current-season rolling)
# ---------------------------------------------------------------------------


def _epa_to_strength_indices(
    *,
    off_epa: float,
    def_epa_allowed: float,
    pressure_generated: float = 0.0,
    pressure_allowed: float = 0.0,
) -> Dict[str, float]:
    pressure_delta = float(pressure_generated) - float(pressure_allowed)
    offense_index = max(
        0.82, min(1.22, 1.0 + (float(off_epa) * 0.75) + (pressure_delta * 0.18))
    )
    defense_index = max(
        0.82,
        min(1.24, 1.0 + ((-float(def_epa_allowed)) * 0.90) + (pressure_delta * 0.14)),
    )
    return {
        "offense_index": round(offense_index, 6),
        "defense_index": round(defense_index, 6),
    }


def load_prior_season_epa_strengths(
    session: Any,
    *,
    season: int,
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Any]]:
    """Y−1 play-weighted EPA → strength indices. Never reads season Y rolling."""
    from sqlalchemy import text

    prior = int(season) - 1
    rows = session.execute(
        text(
            """
            SELECT
              team,
              COUNT(*)::int AS n_weeks,
              COALESCE(SUM(offensive_plays), 0)::int AS offensive_plays,
              COALESCE(SUM(defensive_plays), 0)::int AS defensive_plays,
              CASE WHEN COALESCE(SUM(offensive_plays),0) > 0
                THEN SUM(epa_per_play_offense * offensive_plays)
                     / NULLIF(SUM(offensive_plays), 0)
                ELSE AVG(epa_per_play_offense) END AS off_epa,
              CASE WHEN COALESCE(SUM(defensive_plays),0) > 0
                THEN SUM(epa_per_play_defense_allowed * defensive_plays)
                     / NULLIF(SUM(defensive_plays), 0)
                ELSE AVG(epa_per_play_defense_allowed) END AS def_epa_allowed,
              AVG(pressure_rate_generated) AS pressure_generated,
              AVG(pressure_rate_allowed) AS pressure_allowed
            FROM nfl_dp_team_situational_weekly
            WHERE season = :prior_season AND source = 'nflverse'
            GROUP BY team
            ORDER BY team
            """
        ),
        {"prior_season": prior},
    ).fetchall()

    teams: Dict[str, Dict[str, float]] = {}
    for r in rows:
        team = _normalize_team(str(r.team))
        if team not in NFL_TEAMS:
            continue
        idx = _epa_to_strength_indices(
            off_epa=float(r.off_epa or 0.0),
            def_epa_allowed=float(r.def_epa_allowed or 0.0),
            pressure_generated=float(r.pressure_generated or 0.0),
            pressure_allowed=float(r.pressure_allowed or 0.0),
        )
        teams[team] = {
            "off_epa_per_play": float(r.off_epa or 0.0),
            "def_epa_allowed_per_play": float(r.def_epa_allowed or 0.0),
            "offense_index": float(idx["offense_index"]),
            "defense_index": float(idx["defense_index"]),
            "n_weeks": float(r.n_weeks),
        }

    meta = {
        "prior_season": prior,
        "strength_source": STRENGTH_SOURCE_PACKAGED_EPA,
        "method": "play_weighted_season_avg_epa_y_minus_1",
        "forbidden": "season_Y_rolling_features",
        "team_count": len(teams),
    }
    if len(teams) < 30:
        raise ValueError(
            f"Insufficient prior-season EPA for season={season} "
            f"(prior={prior}, teams={len(teams)})"
        )
    return teams, meta


def assert_no_lookahead_inputs(
    *,
    season: int,
    strength_meta: Mapping[str, Any],
    depth_meta: Mapping[str, Any],
) -> None:
    """Hard guards used by tests + runner."""
    prior = int(strength_meta.get("prior_season") or -1)
    if prior != int(season) - 1:
        raise AssertionError(
            f"Strength prior_season must be Y-1 ({season - 1}); got {prior}"
        )
    if strength_meta.get("forbidden") != "season_Y_rolling_features":
        raise AssertionError("Strength meta missing forbidden rolling-features flag")
    if depth_meta.get("look_ahead") is True:
        raise AssertionError("Depth pack look_ahead=true")
    if int(depth_meta.get("season") or 0) != int(season):
        raise AssertionError(
            f"Depth pack season mismatch: {depth_meta.get('season')} vs {season}"
        )
    week = int(depth_meta.get("week") or 0)
    if week not in (0, 1):
        raise AssertionError(f"Depth week must be 0 or 1 for preseason; got {week}")


# ---------------------------------------------------------------------------
# Universe builder
# ---------------------------------------------------------------------------


def load_schedule_from_db(session: Any, *, season: int) -> List[ScheduledGame]:
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT season, week, home_team, away_team, game_id
            FROM nfl_dp_schedules
            WHERE season = :season
              AND week BETWEEN 1 AND 18
            ORDER BY week, home_team, away_team
            """
        ),
        {"season": int(season)},
    ).fetchall()
    schedule: List[ScheduledGame] = []
    for r in rows:
        home = _normalize_team(str(r.home_team))
        away = _normalize_team(str(r.away_team))
        if home not in NFL_TEAMS or away not in NFL_TEAMS:
            continue
        gid = str(
            getattr(r, "game_id", None)
            or f"{season}-W{int(r.week):02d}-{away}@{home}"
        )
        schedule.append(
            ScheduledGame(
                season=int(r.season),
                week=int(r.week),
                game_id=gid,
                home_team=home,
                away_team=away,
            )
        )
    # 16-game era ≈256 REG games; 17-game era ≈272. Allow thin byes/filters.
    min_games = 240 if int(season) <= 2020 else 250
    if len(schedule) < min_games:
        raise ValueError(
            f"Schedule too thin for season={season}: {len(schedule)} games "
            f"(min={min_games})"
        )
    return schedule


def build_historical_replay_universe(
    session: Any,
    *,
    season: int,
    depth_pack_dir: Path = DEFAULT_HIST_DEPTH_DIR,
) -> EngineUniverse:
    """Build a no-look-ahead universe for season Y (same sim code path)."""
    depth_rows, depth_meta = load_historical_depth_pack(
        season, pack_dir=depth_pack_dir
    )
    epa_teams, strength_meta = load_prior_season_epa_strengths(
        session, season=season
    )
    assert_no_lookahead_inputs(
        season=season,
        strength_meta=strength_meta,
        depth_meta=depth_meta,
    )
    schedule = load_schedule_from_db(session, season=season)

    strength_inputs: Dict[str, Dict[str, float | str]] = {}
    for team in NFL_TEAMS:
        prior = epa_teams.get(team) or {}
        off = float(prior.get("offense_index", 1.0) or 1.0)
        deff = float(prior.get("defense_index", 1.0) or 1.0)
        strength_inputs[team] = {
            "offense_index": off,
            "defense_index": deff,
            "full_strength_offense_index": off,
            "full_strength_defense_index": deff,
            "injury_delta_offense": 0.0,
            "injury_delta_defense": 0.0,
            "blend_prior_weight": 1.0,
            "blend_current_weight": 0.0,
            "pace_factor": 1.0,
            "pass_rate_bias": 0.0,
            "st_index": 1.0,
            "explosiveness": 0.0,
            "variance": 1.35,
            "qb_premium": 0.0,
            "games_played": 0,
            "source": STRENGTH_SOURCE_PACKAGED_EPA,
            "as_of": f"prior_season={strength_meta['prior_season']}",
            "version": REPLAY_PROTOCOL_VERSION,
            "drivers": {
                "blend": {"w_prior": 1.0, "w_current": 0.0},
                "historical_replay": True,
                "prior_season": strength_meta["prior_season"],
                "stubs": {
                    "qb_premium": "stub_not_applied",
                    "continuity": "stub_not_applied",
                    "injury_at_time_depth": "stub_not_applied",
                },
            },
        }

    # League efficiency priors only — never Y baselines (would leak Y usage).
    # Path A2: Y−1 *usage shares* (targets/carries ÷ team) are allowed as a
    # volume role prior; Y counting-stat baselines remain scorecard-only.
    rosters, _hits, coverage = _rosters_from_depth_rows(
        depth_rows,
        source="historical_nflverse_depth_w1",
        baseline_eff=None,
    )
    roster_book = apply_depth_chart_roster_book(rosters)
    if isinstance(roster_book, tuple):
        rosters = roster_book[0]
    else:
        rosters = roster_book
    prior_usage = load_prior_year_usage_shares(
        session, season=int(strength_meta["prior_season"])
    )
    rosters, usage_anchor_diag = anchor_roster_book_to_prior_usage_shares(
        rosters, prior_usage
    )
    rosters = annotate_roster_book(rosters)
    rosters = apply_process_priors_to_roster_book(rosters)

    return EngineUniverse(
        season=int(season),
        schedule=schedule,
        strengths=initialize_strengths(strength_inputs),
        rosters=rosters,
        notes={
            "mode": "historical_replay",
            "protocol_version": REPLAY_PROTOCOL_VERSION,
            "engine_version": ENGINE_VERSION,
            "schedule_source": SCHEDULE_SOURCE_DB,
            "roster_source": "historical_nflverse_depth_w1",
            "roster_as_of": str(depth_meta.get("as_of") or ""),
            "depth_as_of": str(depth_meta.get("as_of") or ""),
            "depth_cutoff_rule": str(depth_meta.get("cutoff_rule") or ""),
            "snapshot_id": str(depth_meta.get("snapshot_id") or ""),
            "pack_sha256": str(depth_meta.get("pack_sha256") or ""),
            "strength_source": STRENGTH_SOURCE_PACKAGED_EPA,
            "prior_season": int(strength_meta["prior_season"]),
            "look_ahead": False,
            "prior_usage_anchor": usage_anchor_diag,
            **{f"depth_{k}": v for k, v in coverage.items()},
        },
        packaged_injury_paths=[],
    )


# ---------------------------------------------------------------------------
# Actuals + baselines
# ---------------------------------------------------------------------------


def load_team_actuals(session: Any, *, season: int) -> Dict[str, Dict[str, float]]:
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            WITH g AS (
              SELECT home_team AS team, home_score AS pf, away_score AS pa,
                     CASE WHEN home_score > away_score THEN 1.0
                          WHEN home_score < away_score THEN 0.0 ELSE 0.5 END AS w
              FROM nfl_dp_schedules
              WHERE season = :season AND week BETWEEN 1 AND 18
                AND home_score IS NOT NULL AND away_score IS NOT NULL
              UNION ALL
              SELECT away_team, away_score, home_score,
                     CASE WHEN away_score > home_score THEN 1.0
                          WHEN away_score < home_score THEN 0.0 ELSE 0.5 END
              FROM nfl_dp_schedules
              WHERE season = :season AND week BETWEEN 1 AND 18
                AND home_score IS NOT NULL AND away_score IS NOT NULL
            )
            SELECT team, SUM(w) AS wins, SUM(pf) AS pf, SUM(pa) AS pa,
                   COUNT(*)::int AS games
            FROM g
            GROUP BY team
            """
        ),
        {"season": int(season)},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for r in rows:
        team = _normalize_team(str(r.team))
        if team not in NFL_TEAMS:
            continue
        out[team] = {
            "wins": float(r.wins),
            "pf": float(r.pf),
            "pa": float(r.pa),
            "games": float(r.games),
        }
    return out


def load_team_offense_yards(
    session: Any, *, season: int
) -> Dict[str, Dict[str, float]]:
    """Team pass/rush yards from usage weekly (REG weeks)."""
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT team,
                   SUM(pass_yards)::float AS pass_yards,
                   SUM(rush_yards)::float AS rush_yards
            FROM nfl_dp_player_usage_weekly
            WHERE season = :season
              AND week BETWEEN 1 AND 18
              AND source = 'pbp_aggregation'
            GROUP BY team
            """
        ),
        {"season": int(season)},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for r in rows:
        team = _normalize_team(str(r.team))
        if team not in NFL_TEAMS:
            continue
        out[team] = {
            "pass_yards": float(r.pass_yards or 0.0),
            "rush_yards": float(r.rush_yards or 0.0),
        }
    return out


def load_prior_year_usage_shares(
    session: Any, *, season: int
) -> Dict[str, Dict[str, float]]:
    """Y−1 player share of team targets / rush attempts (by player_id).

    Used as a *usage input* prior for returning players — not a path-end
    season-yards blend. ``season`` is the prior season (Y−1).
    """
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT
              u.player_id,
              u.team,
              SUM(u.targets)::float AS targets,
              SUM(u.rush_attempts)::float AS rush_attempts,
              SUM(u.pass_attempts)::float AS pass_attempts
            FROM nfl_dp_player_usage_weekly u
            WHERE u.season = :season
              AND u.week BETWEEN 1 AND 18
              AND u.source = 'pbp_aggregation'
              AND u.player_id IS NOT NULL
              AND u.player_id <> ''
            GROUP BY u.player_id, u.team
            """
        ),
        {"season": int(season)},
    ).fetchall()
    team_tgt: Dict[str, float] = {}
    team_rush: Dict[str, float] = {}
    raw: List[Any] = []
    for r in rows:
        team = _normalize_team(str(r.team or ""))
        if team not in NFL_TEAMS:
            continue
        tgt = float(r.targets or 0.0)
        rush = float(r.rush_attempts or 0.0)
        team_tgt[team] = team_tgt.get(team, 0.0) + tgt
        team_rush[team] = team_rush.get(team, 0.0) + rush
        raw.append(r)
    out: Dict[str, Dict[str, float]] = {}
    for r in raw:
        pid = str(r.player_id or "").strip()
        team = _normalize_team(str(r.team or ""))
        if not pid or team not in NFL_TEAMS:
            continue
        tgt = float(r.targets or 0.0)
        rush = float(r.rush_attempts or 0.0)
        # If a player appears on multiple teams in Y−1, keep the higher-volume
        # row (absolute attempts) so free-agent role priors travel.
        candidate = {
            "targets": tgt,
            "rush_attempts": rush,
            "pass_attempts": float(r.pass_attempts or 0.0),
            "target_share": tgt / max(1.0, team_tgt.get(team, 0.0)),
            "rush_share": rush / max(1.0, team_rush.get(team, 0.0)),
        }
        prev = out.get(pid)
        if prev is None or (
            candidate["targets"] + candidate["rush_attempts"]
            > float(prev.get("targets") or 0.0) + float(prev.get("rush_attempts") or 0.0)
        ):
            out[pid] = candidate
    return out


def load_player_actuals(
    session: Any, *, season: int
) -> Dict[str, Dict[str, Any]]:
    from sqlalchemy import text

    # Prefer roster position when weekly usage position is null.
    rows = session.execute(
        text(
            """
            SELECT
              u.player_id,
              u.player_name,
              u.team,
              COALESCE(
                NULLIF(UPPER(TRIM(u.position)), ''),
                NULLIF(UPPER(TRIM(r.position)), '')
              ) AS position,
              SUM(u.pass_yards)::float AS pass_yards,
              SUM(u.pass_touchdowns)::float AS pass_tds,
              SUM(u.rush_yards)::float AS rush_yards,
              SUM(u.receiving_yards)::float AS rec_yards,
              SUM(u.receptions)::float AS receptions,
              SUM(u.touchdowns_scored)::float AS touchdowns_scored
            FROM nfl_dp_player_usage_weekly u
            LEFT JOIN nfl_dp_rosters r
              ON r.season = u.season AND r.player_id = u.player_id
            WHERE u.season = :season
              AND u.week BETWEEN 1 AND 18
              AND u.source = 'pbp_aggregation'
            GROUP BY u.player_id, u.player_name, u.team,
                     COALESCE(
                       NULLIF(UPPER(TRIM(u.position)), ''),
                       NULLIF(UPPER(TRIM(r.position)), '')
                     )
            """
        ),
        {"season": int(season)},
    ).fetchall()

    # rush/rec TDs are not split cleanly in usage — approximate:
    # pass_tds from pass_touchdowns; RB/WR/TE TDs from touchdowns_scored.
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        pid = str(r.player_id or "")
        if not pid:
            continue
        team = _normalize_team(str(r.team or ""))
        pos = str(r.position or "").strip().upper()
        tds = float(r.touchdowns_scored or 0.0)
        pass_tds = float(r.pass_tds or 0.0)
        rush_tds = tds if pos in ("RB", "QB") else 0.0
        rec_tds = tds if pos in ("WR", "TE") else 0.0
        if pos == "RB":
            rush_tds = tds
            rec_tds = 0.0
        out[pid] = {
            "player_id": pid,
            "player_name": str(r.player_name or ""),
            "team": team,
            "position": pos,
            "pass_yards": float(r.pass_yards or 0.0),
            "pass_tds": pass_tds,
            "rush_yards": float(r.rush_yards or 0.0),
            "rush_tds": rush_tds,
            "rec_yards": float(r.rec_yards or 0.0),
            "rec_tds": rec_tds,
            "receptions": float(r.receptions or 0.0),
        }
    return out


def prior_year_regression_team_baseline(
    session: Any, *, season: int
) -> Dict[str, Dict[str, float]]:
    """wins/PF/PA = 0.5 * prior + 0.5 * league mean (no Y leakage)."""
    prior = load_team_actuals(session, season=int(season) - 1)
    if len(prior) < 30:
        raise ValueError(f"Prior-year team actuals thin for {season - 1}")
    mean_w = sum(v["wins"] for v in prior.values()) / len(prior)
    mean_pf = sum(v["pf"] for v in prior.values()) / len(prior)
    mean_pa = sum(v["pa"] for v in prior.values()) / len(prior)
    out: Dict[str, Dict[str, float]] = {}
    for team in NFL_TEAMS:
        p = prior.get(team) or {"wins": mean_w, "pf": mean_pf, "pa": mean_pa}
        out[team] = {
            "wins": 0.5 * float(p["wins"]) + 0.5 * mean_w,
            "pf": 0.5 * float(p["pf"]) + 0.5 * mean_pf,
            "pa": 0.5 * float(p["pa"]) + 0.5 * mean_pa,
        }
    return out


def epa_power_team_baseline(
    epa_teams: Mapping[str, Mapping[str, float]],
    *,
    games_per_team: float = 17.0,
) -> Dict[str, Dict[str, float]]:
    """Simple power: wins from (off−def) index gap; PF/PA from indices.

    Formula (documented):
      net = offense_index − defense_index_allowed_proxy
          = offense_index − (2.0 − defense_index)   # higher def index = better
          = offense_index + defense_index − 2.0
      wins = clip(8.5 + 28.0 * net, 1, 15)
      pf   = games * (21.8 + 18.0 * (offense_index − 1.0))
      pa   = games * (21.8 − 16.0 * (defense_index − 1.0))
    """
    out: Dict[str, Dict[str, float]] = {}
    for team in NFL_TEAMS:
        row = epa_teams.get(team) or {}
        off = float(row.get("offense_index", 1.0) or 1.0)
        deff = float(row.get("defense_index", 1.0) or 1.0)
        net = off + deff - 2.0
        wins = max(1.0, min(15.0, 8.5 + 28.0 * net))
        pf = games_per_team * (21.8 + 18.0 * (off - 1.0))
        pa = games_per_team * (21.8 - 16.0 * (deff - 1.0))
        out[team] = {"wins": wins, "pf": pf, "pa": pa}
    return out


def prior_year_regression_player_baseline(
    session: Any, *, season: int
) -> Dict[str, Dict[str, float]]:
    """Player volume → 0.5 * prior + 0.5 * position mean (by player_id)."""
    prior = load_player_actuals(session, season=int(season) - 1)
    pos_sums: Dict[str, Dict[str, float]] = {}
    pos_n: Dict[str, int] = {}
    metrics = (
        "pass_yards",
        "pass_tds",
        "rush_yards",
        "rush_tds",
        "rec_yards",
        "rec_tds",
    )
    for row in prior.values():
        pos = str(row.get("position") or "")
        if pos not in SKILL_POSITIONS:
            continue
        bucket = pos_sums.setdefault(pos, {m: 0.0 for m in metrics})
        for m in metrics:
            bucket[m] += float(row.get(m) or 0.0)
        pos_n[pos] = pos_n.get(pos, 0) + 1
    pos_mean = {
        pos: {m: (pos_sums[pos][m] / max(1, pos_n[pos])) for m in metrics}
        for pos in pos_sums
    }
    out: Dict[str, Dict[str, float]] = {}
    for pid, row in prior.items():
        pos = str(row.get("position") or "")
        means = pos_mean.get(pos) or {m: 0.0 for m in metrics}
        out[pid] = {
            m: 0.5 * float(row.get(m) or 0.0) + 0.5 * float(means.get(m) or 0.0)
            for m in metrics
        }
        out[pid]["player_name"] = float("nan")  # type marker unused
    # Store names separately via prior map when scoring
    return {pid: {k: v for k, v in vals.items() if k != "player_name"} for pid, vals in out.items()}


def fixed_watchlist(
    session: Any, *, season: int, per_pos: int = 5
) -> Dict[str, List[str]]:
    """Top prior-year volume by position — pre-registered, not post-hoc."""
    prior = load_player_actuals(session, season=int(season) - 1)
    by_pos: Dict[str, List[Tuple[float, str]]] = {p: [] for p in SKILL_POSITIONS}
    for pid, row in prior.items():
        pos = str(row.get("position") or "")
        if pos not in by_pos:
            continue
        if pos == "QB":
            vol = float(row.get("pass_yards") or 0.0)
        elif pos == "RB":
            vol = float(row.get("rush_yards") or 0.0) + float(row.get("rec_yards") or 0.0)
        else:
            vol = float(row.get("rec_yards") or 0.0)
        by_pos[pos].append((vol, pid))
    out: Dict[str, List[str]] = {}
    for pos, items in by_pos.items():
        items.sort(reverse=True)
        out[pos] = [pid for _v, pid in items[:per_pos]]
    return out


def load_vegas_win_totals(path: Optional[Path]) -> Tuple[Dict[int, Dict[str, float]], str]:
    """Optional JSON ``{season: {TEAM: win_total}}``. Missing → empty + note."""
    if path is None or not path.is_file():
        return {}, (
            "Vegas preseason win totals: NOT AVAILABLE in-repo "
            "(no historical futures file). Baseline skipped."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[int, Dict[str, float]] = {}
    for season_s, teams in (payload.get("seasons") or payload).items():
        try:
            season_i = int(season_s)
        except (TypeError, ValueError):
            continue
        if not isinstance(teams, dict):
            continue
        out[season_i] = {
            _normalize_team(t): float(v)
            for t, v in teams.items()
            if _normalize_team(t) in NFL_TEAMS
        }
    src = str(payload.get("source") or path)
    return out, f"Vegas win totals loaded from {src}"


# ---------------------------------------------------------------------------
# Scoring a season
# ---------------------------------------------------------------------------


@dataclass
class SeasonScorecard:
    season: int
    engine_version: str
    snapshot_id: str
    n_sims: int
    config: Dict[str, Any] = field(default_factory=dict)
    model_team: Dict[str, Dict[str, float]] = field(default_factory=dict)
    baselines: Dict[str, Dict[str, Dict[str, float]]] = field(default_factory=dict)
    player_pool: Dict[str, Dict[str, float]] = field(default_factory=dict)
    watchlist: Dict[str, Dict[str, float]] = field(default_factory=dict)
    offense: Dict[str, Dict[str, float]] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)
    conservation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "season": self.season,
            "engine_version": self.engine_version,
            "snapshot_id": self.snapshot_id,
            "n_sims": self.n_sims,
            "config": self.config,
            "model_team": self.model_team,
            "baselines": self.baselines,
            "player_pool": self.player_pool,
            "watchlist": self.watchlist,
            "offense": self.offense,
            "gaps": self.gaps,
            "conservation": self.conservation,
        }


def _player_match_key(name: str) -> str:
    """Normalize ``Josh Allen`` / ``J.Allen`` / ``J Allen`` → ``j|allen``.

    Also collapses multi-initial first tokens (``A.J.`` / ``AJ``) to first char.
    """
    raw = str(name or "").strip().lower()
    raw = raw.replace(".", " ").replace("'", "").replace("-", " ")
    parts = [p for p in re.split(r"\s+", raw) if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    # Drop single-letter middle initials (A J Brown → first=A, last=Brown).
    first = parts[0]
    last = parts[-1]
    return f"{first[0]}|{last}"


def _match_players(
    model_rows: Sequence[Mapping[str, Any]],
    actuals: Mapping[str, Mapping[str, Any]],
) -> List[Tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """Match model ↔ actuals by team + initial|lastname (nflverse vs pbp names)."""
    by_key: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for row in actuals.values():
        key = (
            _player_match_key(str(row.get("player_name") or "")),
            _normalize_team(str(row.get("team") or "")),
        )
        if key[0] and key not in by_key:
            by_key[key] = row
    pairs = []
    seen_actual: set[str] = set()
    for m in model_rows:
        key = (
            _player_match_key(str(m.get("player_name") or "")),
            _normalize_team(str(m.get("team") or "")),
        )
        a = by_key.get(key)
        if not a:
            continue
        pid = str(a.get("player_id") or "")
        if pid and pid in seen_actual:
            continue
        if pid:
            seen_actual.add(pid)
        pairs.append((m, a))
    return pairs


def score_season_predictions(
    *,
    season: int,
    sim: SeasonSimResult,
    universe: EngineUniverse,
    team_actuals: Mapping[str, Mapping[str, float]],
    offense_actuals: Mapping[str, Mapping[str, float]],
    player_actuals: Mapping[str, Mapping[str, Any]],
    baseline_team: Mapping[str, Mapping[str, Mapping[str, float]]],
    baseline_players: Mapping[str, Mapping[str, Mapping[str, float]]],
    watchlist_ids: Mapping[str, Sequence[str]],
    gaps: Optional[List[str]] = None,
) -> SeasonScorecard:
    model_wins = {
        t: float((sim.team_wins.get(t) or {}).get("mean") or 0.0) for t in NFL_TEAMS
    }
    model_pf = {
        t: float((sim.team_wins.get(t) or {}).get("pf_mean") or 0.0) for t in NFL_TEAMS
    }
    model_pa = {
        t: float((sim.team_wins.get(t) or {}).get("pa_mean") or 0.0) for t in NFL_TEAMS
    }
    act_wins = {t: float((team_actuals.get(t) or {}).get("wins") or 0.0) for t in NFL_TEAMS if t in team_actuals}
    act_pf = {t: float(team_actuals[t]["pf"]) for t in act_wins}
    act_pa = {t: float(team_actuals[t]["pa"]) for t in act_wins}

    model_team = {
        "wins": score_vector(model_wins, act_wins),
        "pf": score_vector(model_pf, act_pf),
        "pa": score_vector(model_pa, act_pa),
    }

    baselines_out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for name, preds in baseline_team.items():
        baselines_out[name] = {
            "wins": score_vector(
                {t: float(preds[t]["wins"]) for t in preds if t in act_wins},
                act_wins,
            ),
            "pf": score_vector(
                {t: float(preds[t]["pf"]) for t in preds if t in act_pf},
                act_pf,
            ),
            "pa": score_vector(
                {t: float(preds[t]["pa"]) for t in preds if t in act_pa},
                act_pa,
            ),
        }

    # Offense yards from model player means
    model_off: Dict[str, Dict[str, float]] = {t: {"pass_yards": 0.0, "rush_yards": 0.0} for t in NFL_TEAMS}
    for row in sim.player_season_totals:
        team = _normalize_team(str(row.get("team") or ""))
        if team not in model_off:
            continue
        model_off[team]["pass_yards"] += float(row.get("pass_yards_mean") or 0.0)
        model_off[team]["rush_yards"] += float(row.get("rush_yards_mean") or 0.0)
    offense = {
        "pass_yards": score_vector(
            {t: model_off[t]["pass_yards"] for t in offense_actuals},
            {t: float(offense_actuals[t]["pass_yards"]) for t in offense_actuals},
        ),
        "rush_yards": score_vector(
            {t: model_off[t]["rush_yards"] for t in offense_actuals},
            {t: float(offense_actuals[t]["rush_yards"]) for t in offense_actuals},
        ),
    }

    pairs = _match_players(sim.player_season_totals, player_actuals)
    player_pool: Dict[str, Dict[str, float]] = {}
    for metric, model_key in (
        ("pass_yards", "pass_yards_mean"),
        ("pass_tds", "pass_tds_mean"),
        ("rush_yards", "rush_yards_mean"),
        ("rush_tds", "rush_tds_mean"),
        ("rec_yards", "rec_yards_mean"),
        ("rec_tds", "rec_tds_mean"),
    ):
        pred = {}
        act = {}
        for i, (m, a) in enumerate(pairs):
            pos = str(m.get("position") or a.get("position") or "")
            if metric.startswith("pass") and pos != "QB":
                continue
            if metric.startswith("rush") and pos not in ("QB", "RB"):
                continue
            if metric.startswith("rec") and pos not in ("WR", "TE", "RB"):
                continue
            key = f"{i}:{m.get('player_key')}"
            pred[key] = float(m.get(model_key) or 0.0)
            act[key] = float(a.get(metric) or 0.0)
        player_pool[metric] = score_vector(pred, act)

    # Baseline player pool (prior-year regression) on the **same position
    # universe** as the model pool (Path A2 scorecard hygiene — #164 diluted
    # prior pass MAE with near-zero non-QB pass_yards).
    if "prior_year_regression" in baseline_players:
        bpred_map = baseline_players["prior_year_regression"]
        for metric in ("pass_yards", "rush_yards", "rec_yards"):
            pred = {}
            act = {}
            for i, (m, a) in enumerate(pairs):
                pos = str(m.get("position") or a.get("position") or "")
                if metric.startswith("pass") and pos != "QB":
                    continue
                if metric.startswith("rush") and pos not in ("QB", "RB"):
                    continue
                if metric.startswith("rec") and pos not in ("WR", "TE", "RB"):
                    continue
                pid = str(a.get("player_id") or "")
                if pid not in bpred_map:
                    continue
                key = f"{i}:{pid}"
                pred[key] = float(bpred_map[pid].get(metric) or 0.0)
                act[key] = float(a.get(metric) or 0.0)
            baselines_out.setdefault("prior_year_regression", {})
            baselines_out["prior_year_regression"][f"player_{metric}"] = score_vector(
                pred, act
            )

    # Watchlist
    watch: Dict[str, Dict[str, float]] = {}
    id_to_actual = dict(player_actuals)
    for pos, ids in watchlist_ids.items():
        metric = {
            "QB": ("pass_yards", "pass_yards_mean"),
            "RB": ("rush_yards", "rush_yards_mean"),
            "WR": ("rec_yards", "rec_yards_mean"),
            "TE": ("rec_yards", "rec_yards_mean"),
        }[pos]
        pred = {}
        act = {}
        for pid in ids:
            a = id_to_actual.get(pid)
            if not a:
                continue
            akey = (
                _player_match_key(str(a.get("player_name") or "")),
                _normalize_team(str(a.get("team") or "")),
            )
            mrow = next(
                (
                    r
                    for r in sim.player_season_totals
                    if (
                        _player_match_key(str(r.get("player_name") or "")),
                        _normalize_team(str(r.get("team") or "")),
                    )
                    == akey
                ),
                None,
            )
            if not mrow:
                continue
            pred[pid] = float(mrow.get(metric[1]) or 0.0)
            act[pid] = float(a.get(metric[0]) or 0.0)
        watch[pos] = score_vector(pred, act)

    mean_wins_sum = sum(model_wins.values())
    n_games = float(len(universe.schedule))
    conservation = {
        "mean_wins_sum": round(mean_wins_sum, 3),
        # Path W/L is zero-sum: each REG game awards exactly one win.
        "wins_zero_sum_ok": abs(mean_wins_sum - n_games) < 1.5,
        "n_schedule_games": int(n_games),
        "expected_wins_sum": n_games,
    }

    return SeasonScorecard(
        season=int(season),
        engine_version=str(sim.engine_version),
        snapshot_id=str(universe.notes.get("snapshot_id") or ""),
        n_sims=int(sim.n_sims),
        config={
            "protocol_version": REPLAY_PROTOCOL_VERSION,
            "prior_season": universe.notes.get("prior_season"),
            "depth_cutoff_rule": universe.notes.get("depth_cutoff_rule"),
            "seed": None,
        },
        model_team=model_team,
        baselines=baselines_out,
        player_pool=player_pool,
        watchlist=watch,
        offense=offense,
        gaps=list(gaps or []),
        conservation=conservation,
    )


def pool_scorecards(cards: Sequence[SeasonScorecard]) -> Dict[str, Any]:
    """Micro-average MAE/bias across seasons (equal team weight via n)."""

    def _pool(metric_path: Tuple[str, ...]) -> Dict[str, float]:
        total_n = 0.0
        mae_acc = 0.0
        bias_acc = 0.0
        rhos = []
        for card in cards:
            node: Any = card.to_dict()
            for key in metric_path:
                node = (node or {}).get(key)
            if not isinstance(node, dict) or not node:
                continue
            n = float(node.get("n") or 0.0)
            if n <= 0 or not math.isfinite(float(node.get("mae", float("nan")))):
                continue
            total_n += n
            mae_acc += float(node["mae"]) * n
            bias_acc += float(node["bias"]) * n
            if math.isfinite(float(node.get("rank_corr", float("nan")))):
                rhos.append(float(node["rank_corr"]))
        if total_n <= 0:
            return {"n": 0.0, "mae": float("nan"), "bias": float("nan"), "rank_corr": float("nan")}
        return {
            "n": total_n,
            "mae": mae_acc / total_n,
            "bias": bias_acc / total_n,
            "rank_corr": sum(rhos) / len(rhos) if rhos else float("nan"),
        }

    return {
        "seasons": [c.season for c in cards],
        "model_team_wins": _pool(("model_team", "wins")),
        "model_team_pf": _pool(("model_team", "pf")),
        "model_team_pa": _pool(("model_team", "pa")),
        "prior_year_wins": _pool(("baselines", "prior_year_regression", "wins")),
        "epa_power_wins": _pool(("baselines", "epa_power", "wins")),
        "vegas_wins": _pool(("baselines", "vegas", "wins")),
        "model_pass_yards": _pool(("offense", "pass_yards")),
        "model_rush_yards": _pool(("offense", "rush_yards")),
        "model_player_pass_yards": _pool(("player_pool", "pass_yards")),
        "model_player_rush_yards": _pool(("player_pool", "rush_yards")),
        "model_player_rec_yards": _pool(("player_pool", "rec_yards")),
    }


def verdict_from_pooled(pooled: Mapping[str, Any]) -> Dict[str, Any]:
    """Pre-registered win rule: lower MAE wins; ties within 1% → explain."""
    m = pooled.get("model_team_wins") or {}
    p = pooled.get("prior_year_wins") or {}
    e = pooled.get("epa_power_wins") or {}
    v = pooled.get("vegas_wins") or {}

    def _beats(a: Mapping[str, Any], b: Mapping[str, Any]) -> Optional[bool]:
        """True if a.mae < b.mae; None if either MAE missing/non-finite."""
        am, bm = a.get("mae"), b.get("mae")
        if am is None or bm is None:
            return None
        if not math.isfinite(float(am)) or not math.isfinite(float(bm)):
            return None
        if abs(float(am) - float(bm)) / max(float(bm), 1e-6) < 0.005:
            return None  # statistical tie band (0.5%)
        return float(am) < float(bm)

    vs_prior = _beats(m, p)
    vs_epa = _beats(m, e)
    vegas_mae = (v or {}).get("mae")
    vs_vegas = (
        _beats(m, v)
        if vegas_mae is not None and math.isfinite(float(vegas_mae))
        else None
    )

    earned = []
    not_earned = []
    if vs_prior is True:
        earned.append("team_wins vs prior_year_regression")
    elif vs_prior is False:
        not_earned.append("team_wins vs prior_year_regression (higher MAE)")
    else:
        not_earned.append(
            "team_wins vs prior_year_regression (tie within 0.5% or unavailable)"
        )

    if vs_epa is True:
        earned.append("team_wins vs epa_power")
    elif vs_epa is False:
        not_earned.append("team_wins vs epa_power (higher MAE)")
    else:
        not_earned.append("team_wins vs epa_power (tie/unavailable)")

    if vs_vegas is True:
        earned.append("team_wins vs vegas")
    elif vs_vegas is False:
        not_earned.append("team_wins vs vegas (higher MAE)")
    else:
        not_earned.append("team_wins vs vegas (missing historical files)")

    # Player yards as secondary signal
    for key, label in (
        ("model_player_pass_yards", "player_pass_yards"),
        ("model_player_rush_yards", "player_rush_yards"),
        ("model_player_rec_yards", "player_rec_yards"),
    ):
        node = pooled.get(key) or {}
        if math.isfinite(float(node.get("mae") or float("nan"))):
            earned.append(f"{label} scorecard produced (n={int(node.get('n') or 0)})")

    seasons_scored = list(pooled.get("seasons") or [])
    # Infrastructure: repeatable runner + packs + scorecard.
    # Model-value claim: must beat prior-year+regression on team wins MAE.
    return {
        "earned": earned,
        "not_earned": not_earned,
        "model_wins_mae": m.get("mae"),
        "prior_year_wins_mae": p.get("mae"),
        "epa_power_wins_mae": e.get("mae"),
        "vegas_wins_mae": v.get("mae"),
        "phase4_infrastructure_unblocked": len(seasons_scored) >= 1,
        "phase4_model_claim_unblocked": bool(vs_prior is True),
        "note": (
            "Phase 4 infrastructure unblocked (repeatable no-look-ahead replay). "
            "Model-value claim stays blocked until team-wins MAE beats "
            "prior-year+regression."
        ),
        "seasons_scored": seasons_scored,
    }


def run_season_replay(
    session: Any,
    *,
    season: int,
    n_sims: int = 40,
    seed: int = 20260809,
    depth_pack_dir: Path = DEFAULT_HIST_DEPTH_DIR,
    vegas_totals: Optional[Mapping[str, float]] = None,
) -> SeasonScorecard:
    universe = build_historical_replay_universe(
        session, season=season, depth_pack_dir=depth_pack_dir
    )
    sim = simulate_full_season(
        universe,
        n_sims=n_sims,
        seed=int(seed) + int(season),
        include_diagnostics=True,
    )
    team_actuals = load_team_actuals(session, season=season)
    offense_actuals = load_team_offense_yards(session, season=season)
    player_actuals = load_player_actuals(session, season=season)
    epa_teams, _ = load_prior_season_epa_strengths(session, season=season)

    gaps: List[str] = []
    if len(team_actuals) < 32:
        gaps.append(f"team_actuals only {len(team_actuals)}/32")
    if len(offense_actuals) < 32:
        gaps.append(f"offense_yards only {len(offense_actuals)}/32")
    if not player_actuals:
        gaps.append("player_actuals empty")
    if universe.notes.get("depth_full_skill_starter_teams", 32) < 28:
        gaps.append(
            f"depth full-skill starters "
            f"{universe.notes.get('depth_full_skill_starter_teams')}/32"
        )

    games = 17.0 if season >= 2021 else 16.0
    baseline_team = {
        "prior_year_regression": prior_year_regression_team_baseline(
            session, season=season
        ),
        "epa_power": epa_power_team_baseline(epa_teams, games_per_team=games),
    }
    if vegas_totals:
        baseline_team["vegas"] = {
            t: {
                "wins": float(vegas_totals[t]),
                "pf": float("nan"),
                "pa": float("nan"),
            }
            for t in vegas_totals
        }
    else:
        gaps.append("vegas_win_totals_missing")

    baseline_players = {
        "prior_year_regression": prior_year_regression_player_baseline(
            session, season=season
        )
    }
    watch = fixed_watchlist(session, season=season)
    card = score_season_predictions(
        season=season,
        sim=sim,
        universe=universe,
        team_actuals=team_actuals,
        offense_actuals=offense_actuals,
        player_actuals=player_actuals,
        baseline_team=baseline_team,
        baseline_players=baseline_players,
        watchlist_ids=watch,
        gaps=gaps,
    )
    card.config["seed"] = int(seed) + int(season)
    card.config["n_sims"] = n_sims
    return card
