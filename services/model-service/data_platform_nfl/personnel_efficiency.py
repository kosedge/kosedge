"""Personnel efficiency + substitution elasticity materializers.

Leakage: weekly row for week W is as-of end of W. Pre-game joins use W-1.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import text

from .kav import assert_no_future_leakage

PERSONNEL_VERSION = "personnel-eff-v1"
MIN_PLAYS_WEEK = 12


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def parse_offense_personnel(raw: Optional[str]) -> Optional[str]:
    """Normalize nflverse offense_personnel like '1 RB, 1 TE, 3 WR' → '11'."""
    if not raw:
        return None
    text_v = str(raw).upper().strip()
    # Already coded like "11", "12", "21"
    if re.fullmatch(r"[0-9]{2}", text_v):
        return text_v
    rb = te = None
    m_rb = re.search(r"(\d+)\s*RB", text_v)
    m_te = re.search(r"(\d+)\s*TE", text_v)
    if m_rb:
        rb = int(m_rb.group(1))
    if m_te:
        te = int(m_te.group(1))
    if rb is None or te is None:
        return None
    return f"{rb}{te}"


def bucket_personnel(code: Optional[str]) -> str:
    if code in {"11", "12", "21", "13", "22", "10"}:
        if code == "10":
            return "11"
        if code == "22":
            return "21"
        return code
    return "other"


def compute_personnel_edge(
    *,
    rates: Dict[str, float],
    epas: Dict[str, Optional[float]],
    league_epa: Dict[str, float],
) -> float:
    """Play-weighted EPA vs league at same package; bounded latent."""
    edge = 0.0
    weight = 0.0
    for pkg, rate in rates.items():
        if rate <= 0:
            continue
        team_epa = epas.get(pkg)
        if team_epa is None:
            continue
        base = league_epa.get(pkg, 0.0)
        edge += rate * (float(team_epa) - float(base))
        weight += rate
    if weight <= 0:
        return 0.0
    # Scale EPA/play gap (~0.05) into small edge units.
    return _clamp(edge / max(0.05, weight) / 0.05, -3.0, 3.0)


def light_usage_elasticity_tilt(
    *,
    base_usage: float,
    elasticity_5g: Optional[float],
    max_tilt: float = 0.04,
) -> float:
    """Light player-usage tilt from team sub elasticity (bounded; optional hook)."""
    if elasticity_5g is None:
        return float(base_usage)
    tilt = _clamp(float(elasticity_5g) * 0.02, -max_tilt, max_tilt)
    return _clamp(float(base_usage) * (1.0 + tilt), 0.0, 1.0)


def compute_substitution_elasticity(
    *,
    snap_pcts: Sequence[float],
    epa_values: Sequence[float],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Crude elasticity: cov(snap_pct, epa) / var(snap_pct)."""
    n = min(len(snap_pcts), len(epa_values))
    if n < 4:
        return None, None, None
    xs = [float(snap_pcts[i]) for i in range(n)]
    ys = [float(epa_values[i]) for i in range(n)]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs) / n
    if var_x < 1e-6:
        return mean_x, 0.0, 0.0
    cov = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / n
    elasticity = _clamp(cov / var_x, -2.0, 2.0)
    vol = var_x ** 0.5
    return mean_x, vol, elasticity


def _rolling_mean(values: Sequence[float], window: int = 5) -> Optional[float]:
    if not values:
        return None
    slice_vals = list(values)[-window:]
    return sum(slice_vals) / len(slice_vals) if slice_vals else None


def materialize_personnel_efficiency(
    *,
    seasons: Sequence[int],
    replace_existing: bool = False,
) -> Dict[str, Any]:
    from .db import SessionLocal

    session = SessionLocal()
    started = _now()
    try:
        season_list = [int(s) for s in seasons]
        if replace_existing:
            session.execute(
                text("DELETE FROM nfl_dp_personnel_efficiency_weekly WHERE season = ANY(:seasons)"),
                {"seasons": season_list},
            )
            session.commit()

        rows = session.execute(
            text(
                """
                SELECT
                  season, week, posteam AS team,
                  offense_personnel,
                  epa,
                  CASE WHEN success THEN 1.0 ELSE 0.0 END AS success_n
                FROM nfl_dp_play_by_play
                WHERE season = ANY(:seasons)
                  AND play_type IN ('pass', 'run')
                  AND posteam IS NOT NULL
                  AND epa IS NOT NULL
                  AND week IS NOT NULL
                  AND week BETWEEN 1 AND 22
                  AND offense_personnel IS NOT NULL
                """
            ),
            {"seasons": season_list},
        ).fetchall()

        # Aggregate per (season, week, team, package)
        from collections import defaultdict

        cell: Dict[Tuple[int, int, str, str], Dict[str, float]] = defaultdict(
            lambda: {"n": 0.0, "epa": 0.0, "success": 0.0}
        )
        for row in rows:
            m = dict(row._mapping)
            code = bucket_personnel(parse_offense_personnel(m.get("offense_personnel")))
            key = (int(m["season"]), int(m["week"]), str(m["team"]), code)
            cell[key]["n"] += 1.0
            cell[key]["epa"] += float(m["epa"])
            cell[key]["success"] += float(m["success_n"] or 0.0)

        # League package EPA by season (for edge baseline)
        league: Dict[Tuple[int, str], Dict[str, float]] = defaultdict(lambda: {"n": 0.0, "epa": 0.0})
        for (season, _week, _team, pkg), agg in cell.items():
            league[(season, pkg)]["n"] += agg["n"]
            league[(season, pkg)]["epa"] += agg["epa"]
        league_epa: Dict[Tuple[int, str], float] = {}
        for k, agg in league.items():
            league_epa[k] = agg["epa"] / agg["n"] if agg["n"] else 0.0

        # Build weekly team totals then cumulative as-of
        week_team: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
        for (season, week, team, pkg), agg in cell.items():
            wt = week_team.setdefault(
                (season, week, team),
                {"plays": 0.0, "pkg_n": defaultdict(float), "pkg_epa": defaultdict(float), "pkg_success": defaultdict(float)},
            )
            wt["plays"] += agg["n"]
            wt["pkg_n"][pkg] += agg["n"]
            wt["pkg_epa"][pkg] += agg["epa"]
            wt["pkg_success"][pkg] += agg["success"]

        written = 0
        history: Dict[Tuple[int, str], List[float]] = defaultdict(list)

        keys_sorted = sorted(week_team.keys(), key=lambda x: (x[0], x[2], x[1]))
        # Process in season/team/week order for rolling
        by_team: Dict[Tuple[int, str], List[Tuple[int, Dict[str, Any]]]] = defaultdict(list)
        for season, week, team in keys_sorted:
            by_team[(season, team)].append((week, week_team[(season, week, team)]))

        for (season, team), week_rows in by_team.items():
            cum_pkg_n: Dict[str, float] = defaultdict(float)
            cum_pkg_epa: Dict[str, float] = defaultdict(float)
            cum_pkg_success: Dict[str, float] = defaultdict(float)
            cum_plays = 0.0
            edges: List[float] = []
            for week, wt in week_rows:
                for pkg in wt["pkg_n"]:
                    cum_pkg_n[pkg] += wt["pkg_n"][pkg]
                    cum_pkg_epa[pkg] += wt["pkg_epa"][pkg]
                    cum_pkg_success[pkg] += wt["pkg_success"][pkg]
                cum_plays += wt["plays"]
                if cum_plays < MIN_PLAYS_WEEK:
                    continue

                rates = {pkg: cum_pkg_n[pkg] / cum_plays for pkg in cum_pkg_n}
                epas = {
                    pkg: (cum_pkg_epa[pkg] / cum_pkg_n[pkg] if cum_pkg_n[pkg] else None)
                    for pkg in cum_pkg_n
                }
                league_map = {pkg: league_epa.get((season, pkg), 0.0) for pkg in cum_pkg_n}
                edge = compute_personnel_edge(rates=rates, epas=epas, league_epa=league_map)
                edges.append(edge)
                edge_5g = _rolling_mean(edges, 5)

                def _rate(pkg: str) -> Optional[float]:
                    return round(rates.get(pkg, 0.0), 6) if cum_plays else None

                def _epa(pkg: str) -> Optional[float]:
                    v = epas.get(pkg)
                    return round(v, 6) if v is not None else None

                epa_weighted = sum(
                    (cum_pkg_epa[p] / cum_pkg_n[p]) * rates[p] for p in rates if cum_pkg_n[p]
                )
                success_weighted = sum(
                    (cum_pkg_success[p] / cum_pkg_n[p]) * rates[p] for p in rates if cum_pkg_n[p]
                )

                session.execute(
                    text(
                        """
                        INSERT INTO nfl_dp_personnel_efficiency_weekly (
                          season, week, team, plays,
                          personnel_11_rate, personnel_12_rate, personnel_21_rate,
                          personnel_13_rate, personnel_other_rate,
                          epa_11, epa_12, epa_21, epa_weighted, success_weighted,
                          personnel_edge, personnel_edge_5g, as_of_week, source, updated_at
                        ) VALUES (
                          :season, :week, :team, :plays,
                          :r11, :r12, :r21, :r13, :rother,
                          :e11, :e12, :e21, :epa_w, :succ_w,
                          :edge, :edge_5g, :as_of_week, :source, :updated_at
                        )
                        ON CONFLICT (season, week, team) DO UPDATE SET
                          plays = EXCLUDED.plays,
                          personnel_11_rate = EXCLUDED.personnel_11_rate,
                          personnel_12_rate = EXCLUDED.personnel_12_rate,
                          personnel_21_rate = EXCLUDED.personnel_21_rate,
                          personnel_13_rate = EXCLUDED.personnel_13_rate,
                          personnel_other_rate = EXCLUDED.personnel_other_rate,
                          epa_11 = EXCLUDED.epa_11,
                          epa_12 = EXCLUDED.epa_12,
                          epa_21 = EXCLUDED.epa_21,
                          epa_weighted = EXCLUDED.epa_weighted,
                          success_weighted = EXCLUDED.success_weighted,
                          personnel_edge = EXCLUDED.personnel_edge,
                          personnel_edge_5g = EXCLUDED.personnel_edge_5g,
                          as_of_week = EXCLUDED.as_of_week,
                          source = EXCLUDED.source,
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": season,
                        "week": week,
                        "team": team,
                        "plays": int(cum_plays),
                        "r11": _rate("11"),
                        "r12": _rate("12"),
                        "r21": _rate("21"),
                        "r13": _rate("13"),
                        "rother": _rate("other"),
                        "e11": _epa("11"),
                        "e12": _epa("12"),
                        "e21": _epa("21"),
                        "epa_w": round(epa_weighted, 6),
                        "succ_w": round(success_weighted, 6),
                        "edge": round(edge, 6),
                        "edge_5g": round(edge_5g, 6) if edge_5g is not None else None,
                        "as_of_week": week,
                        "source": "nflverse_pbp",
                        "updated_at": _now(),
                    },
                )
                written += 1

            session.commit()

        # Substitution elasticity from snap counts if table present.
        sub_written = _materialize_substitution_elasticity(session, seasons=season_list, replace_existing=replace_existing)

        return {
            "ok": True,
            "version": PERSONNEL_VERSION,
            "seasons": season_list,
            "personnel_rows": written,
            "substitution_rows": sub_written,
            "elapsed_sec": round((_now() - started).total_seconds(), 3),
            "notes": "Strict lag: join as_of_week = game.week - 1",
        }
    except Exception as exc:
        try:
            session.rollback()
        except Exception:
            pass
        return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
    finally:
        session.close()


def _materialize_substitution_elasticity(
    session: Any,
    *,
    seasons: Sequence[int],
    replace_existing: bool,
) -> int:
    if replace_existing:
        try:
            session.execute(
                text("DELETE FROM nfl_dp_substitution_elasticity_weekly WHERE season = ANY(:seasons)"),
                {"seasons": list(seasons)},
            )
            session.commit()
        except Exception:
            session.rollback()

    # Prefer snap counts table when present.
    try:
        snap_rows = session.execute(
            text(
                """
                SELECT season, week, team, position, player_id,
                       COALESCE(offense_pct, 0) AS snap_pct
                FROM nfl_dp_snap_counts_weekly
                WHERE season = ANY(:seasons)
                  AND week BETWEEN 1 AND 22
                """
            ),
            {"seasons": list(seasons)},
        ).fetchall()
    except Exception:
        return 0

    if not snap_rows:
        return 0

    # Pair with team-week EPA from PBP
    try:
        epa_rows = session.execute(
            text(
                """
                SELECT season, week, posteam AS team, AVG(epa) AS epa
                FROM nfl_dp_play_by_play
                WHERE season = ANY(:seasons)
                  AND play_type IN ('pass', 'run')
                  AND epa IS NOT NULL
                  AND week BETWEEN 1 AND 22
                GROUP BY season, week, posteam
                """
            ),
            {"seasons": list(seasons)},
        ).fetchall()
    except Exception:
        return 0

    epa_map = {
        (int(r._mapping["season"]), int(r._mapping["week"]), str(r._mapping["team"])): float(r._mapping["epa"])
        for r in epa_rows
    }

    from collections import defaultdict

    # position_group -> list of (season, week, team, snap, epa)
    grouped: Dict[Tuple[int, str, str], List[Tuple[float, float]]] = defaultdict(list)
    for row in snap_rows:
        m = dict(row._mapping)
        season, week, team = int(m["season"]), int(m["week"]), str(m["team"])
        pos = str(m.get("position") or "UNK").upper()
        if pos in {"WR", "RB", "TE", "QB", "FB"}:
            group = pos
        elif pos in {"CB", "S", "FS", "SS", "DB"}:
            group = "DB"
        elif pos in {"LB", "ILB", "OLB", "MLB"}:
            group = "LB"
        elif pos in {"DE", "DT", "NT", "DL", "EDGE"}:
            group = "DL"
        else:
            group = "OTHER"
        epa = epa_map.get((season, week, team))
        if epa is None:
            continue
        # Accumulate player-week into team-group later via mean snap
        grouped[(season, week, team, group)].append((float(m["snap_pct"]), epa))

    # Collapse to team-week-group mean snap vs team epa
    team_week_group: Dict[Tuple[int, int, str, str], Tuple[float, float]] = {}
    for (season, week, team, group), pairs in grouped.items():
        if not pairs:
            continue
        mean_snap = sum(p[0] for p in pairs) / len(pairs)
        team_week_group[(season, week, team, group)] = (mean_snap, pairs[0][1])

    # Cumulative elasticity as-of each week
    by_key: Dict[Tuple[int, str, str], List[Tuple[int, float, float]]] = defaultdict(list)
    for (season, week, team, group), (snap, epa) in team_week_group.items():
        by_key[(season, team, group)].append((week, snap, epa))

    written = 0
    for (season, team, group), series in by_key.items():
        series.sort(key=lambda x: x[0])
        snaps: List[float] = []
        epas: List[float] = []
        elast_hist: List[float] = []
        for week, snap, epa in series:
            snaps.append(snap)
            epas.append(epa)
            mean_snap, vol, elast = compute_substitution_elasticity(snap_pcts=snaps, epa_values=epas)
            if elast is None:
                continue
            elast_hist.append(elast)
            elast_5g = _rolling_mean(elast_hist, 5)
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_substitution_elasticity_weekly (
                      season, week, team, position_group, sample_players,
                      mean_snap_pct, snap_pct_volatility, epa_per_snap_pct,
                      elasticity, elasticity_5g, as_of_week, source, updated_at
                    ) VALUES (
                      :season, :week, :team, :position_group, :sample_players,
                      :mean_snap_pct, :vol, :epa_per,
                      :elasticity, :elasticity_5g, :as_of_week, :source, :updated_at
                    )
                    ON CONFLICT (season, week, team, position_group) DO UPDATE SET
                      sample_players = EXCLUDED.sample_players,
                      mean_snap_pct = EXCLUDED.mean_snap_pct,
                      snap_pct_volatility = EXCLUDED.snap_pct_volatility,
                      epa_per_snap_pct = EXCLUDED.epa_per_snap_pct,
                      elasticity = EXCLUDED.elasticity,
                      elasticity_5g = EXCLUDED.elasticity_5g,
                      as_of_week = EXCLUDED.as_of_week,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": season,
                    "week": week,
                    "team": team,
                    "position_group": group,
                    "sample_players": len(snaps),
                    "mean_snap_pct": round(mean_snap or 0.0, 6),
                    "vol": round(vol or 0.0, 6),
                    "epa_per": round(elast, 6),
                    "elasticity": round(elast, 6),
                    "elasticity_5g": round(elast_5g, 6) if elast_5g is not None else None,
                    "as_of_week": week,
                    "source": "nflverse_snaps_pbp",
                    "updated_at": _now(),
                },
            )
            written += 1
        session.commit()
    return written


def fetch_lagged_personnel_for_matchup(
    session: Any,
    *,
    season: int,
    week: int,
    home_team: str,
    away_team: str,
) -> Dict[str, Any]:
    """Strict week-1 lag fetch for sim inputs."""
    as_of = int(week) - 1
    assert_no_future_leakage(as_of if as_of >= 1 else None, int(week))
    if as_of < 1:
        return {"available": False, "as_of_week": None}

    def _one(team: str) -> Dict[str, Any]:
        row = session.execute(
            text(
                """
                SELECT personnel_edge_5g, personnel_edge, as_of_week
                FROM nfl_dp_personnel_efficiency_weekly
                WHERE season = :season AND team = :team AND week = :week
                """
            ),
            {"season": season, "team": team, "week": as_of},
        ).fetchone()
        if not row:
            return {}
        return dict(row._mapping)

    home = _one(home_team)
    away = _one(away_team)
    home_edge = home.get("personnel_edge_5g") if home else None
    away_edge = away.get("personnel_edge_5g") if away else None

    # Team-level mean sub elasticity (offense-ish groups)
    def _sub(team: str) -> Optional[float]:
        row = session.execute(
            text(
                """
                SELECT AVG(elasticity_5g) AS e
                FROM nfl_dp_substitution_elasticity_weekly
                WHERE season = :season AND team = :team AND week = :week
                  AND position_group IN ('WR', 'RB', 'TE', 'QB')
                """
            ),
            {"season": season, "team": team, "week": as_of},
        ).fetchone()
        if not row or row._mapping.get("e") is None:
            return None
        return float(row._mapping["e"])

    return {
        "available": home_edge is not None and away_edge is not None,
        "as_of_week": as_of,
        "home_personnel_edge_5g": float(home_edge) if home_edge is not None else None,
        "away_personnel_edge_5g": float(away_edge) if away_edge is not None else None,
        "home_sub_elasticity_5g": _sub(home_team),
        "away_sub_elasticity_5g": _sub(away_team),
    }


def attach_personnel_to_matchup_features(
    session: Any,
    *,
    seasons: Sequence[int],
) -> Dict[str, Any]:
    """Fill matchup pack second-order personnel columns (lagged)."""
    updated = 0
    packs = session.execute(
        text(
            """
            SELECT season, week, game_id, home_team, away_team
            FROM nfl_dp_matchup_features_weekly
            WHERE season = ANY(:seasons)
            """
        ),
        {"seasons": list(seasons)},
    ).fetchall()
    for row in packs:
        m = dict(row._mapping)
        season, week = int(m["season"]), int(m["week"])
        feat = fetch_lagged_personnel_for_matchup(
            session,
            season=season,
            week=week,
            home_team=str(m["home_team"]),
            away_team=str(m["away_team"]),
        )
        home_e = feat.get("home_personnel_edge_5g")
        away_e = feat.get("away_personnel_edge_5g")
        diff = None
        if home_e is not None and away_e is not None:
            diff = home_e - away_e
        session.execute(
            text(
                """
                UPDATE nfl_dp_matchup_features_weekly SET
                  home_personnel_edge_5g = :home_e,
                  away_personnel_edge_5g = :away_e,
                  diff_personnel_edge_5g = :diff,
                  home_sub_elasticity_5g = :home_sub,
                  away_sub_elasticity_5g = :away_sub,
                  second_order_as_of_week = COALESCE(:as_of, second_order_as_of_week),
                  updated_at = NOW()
                WHERE season = :season AND week = :week AND game_id = :game_id
                """
            ),
            {
                "home_e": home_e,
                "away_e": away_e,
                "diff": diff,
                "home_sub": feat.get("home_sub_elasticity_5g"),
                "away_sub": feat.get("away_sub_elasticity_5g"),
                "as_of": feat.get("as_of_week"),
                "season": season,
                "week": week,
                "game_id": m["game_id"],
            },
        )
        updated += 1
    session.commit()
    return {"ok": True, "updated": updated}
