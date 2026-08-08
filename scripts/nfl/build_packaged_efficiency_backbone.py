#!/usr/bin/env python3
"""Rebuild packaged NFL efficiency-backbone artifact (Sprint 2 → v1.1).

Source: local / env Postgres
  - ``nfl_dp_team_situational_weekly`` (source=nflverse)
  - ``nfl_dp_play_by_play`` → true pass / run / early-down EPA
  - ``nfl_dp_team_st_kav_weekly`` → real ST EPA (when present)

Writes:
  services/model-service/.../data/nfl_team_efficiency_backbone_<season>.json
  (also refreshes legacy ``nfl_team_epa_priors_<season>.json`` for compat)

Conversion uses ``efficiency_backbone`` → same O/D index contract as Edge Board.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

OUT_DIR = MS / "src" / "services" / "nfl_season_engine" / "data"


def _connect(dsn: str):
    try:
        import psycopg

        return psycopg.connect(dsn)
    except Exception:
        import psycopg2

        return psycopg2.connect(dsn)


def _candidate_dsns(explicit: Optional[str]) -> List[str]:
    out: List[str] = []
    if explicit:
        out.append(explicit)
    out.append("postgresql://ryankos:postgres@127.0.0.1:5432/kosedge")
    for key in ("LAUNCH_RESEARCH_DATABASE_URL", "DATABASE_URL"):
        raw = (os.getenv(key) or "").strip()
        if not raw:
            continue
        raw = raw.replace("postgresql+psycopg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://"
        )
        if raw not in out:
            out.append(raw)
    return out


def _fetch_season_avgs(conn: Any, prior_season: int) -> List[Dict[str, Any]]:
    sql = """
        SELECT
          team,
          COUNT(*)::int AS n_weeks,
          COALESCE(SUM(offensive_plays), 0)::int AS offensive_plays,
          COALESCE(SUM(defensive_plays), 0)::int AS defensive_plays,
          COALESCE(SUM(pass_plays), 0)::int AS pass_plays,
          COALESCE(SUM(run_plays), 0)::int AS run_plays,
          COALESCE(SUM(early_down_plays), 0)::int AS early_down_plays,
          COALESCE(SUM(explosive_pass_plays), 0)::int AS explosive_pass_plays,
          COALESCE(SUM(explosive_pass_allowed), 0)::int AS explosive_pass_allowed,
          CASE WHEN COALESCE(SUM(offensive_plays),0) > 0
            THEN SUM(epa_per_play_offense * offensive_plays) / NULLIF(SUM(offensive_plays), 0)
            ELSE AVG(epa_per_play_offense) END AS off_epa,
          CASE WHEN COALESCE(SUM(defensive_plays),0) > 0
            THEN SUM(epa_per_play_defense_allowed * defensive_plays)
                 / NULLIF(SUM(defensive_plays), 0)
            ELSE AVG(epa_per_play_defense_allowed) END AS def_epa_allowed,
          CASE WHEN COALESCE(SUM(offensive_plays),0) > 0
            THEN SUM(success_rate_offense * offensive_plays) / NULLIF(SUM(offensive_plays), 0)
            ELSE AVG(success_rate_offense) END AS success_rate_offense,
          CASE WHEN COALESCE(SUM(defensive_plays),0) > 0
            THEN SUM(success_rate_defense_allowed * defensive_plays)
                 / NULLIF(SUM(defensive_plays), 0)
            ELSE AVG(success_rate_defense_allowed) END AS success_rate_defense_allowed,
          AVG(pass_rate) AS pass_rate,
          AVG(early_down_pass_rate) AS early_down_pass_rate,
          AVG(third_down_conversion_rate) AS third_down_conversion_rate,
          AVG(red_zone_td_rate) AS red_zone_td_rate,
          AVG(pressure_rate_generated) AS pressure_generated,
          AVG(pressure_rate_allowed) AS pressure_allowed
        FROM nfl_dp_team_situational_weekly
        WHERE season = %s AND source = 'nflverse'
        GROUP BY team
        ORDER BY team
    """
    cur = conn.cursor()
    cur.execute(sql, (int(prior_season),))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    return rows


def _fetch_offensive_splits(conn: Any, prior_season: int) -> Dict[str, Dict[str, Any]]:
    """True pass / run / early-down EPA from owned PBP (REG weeks 1–18)."""
    sql = """
        WITH plays AS (
          SELECT
            posteam AS team,
            defteam AS opp,
            play_type,
            down,
            epa
          FROM nfl_dp_play_by_play
          WHERE season = %s
            AND week BETWEEN 1 AND 18
            AND play_type IN ('pass', 'run')
            AND epa IS NOT NULL
            AND posteam IS NOT NULL
            AND defteam IS NOT NULL
        ),
        off AS (
          SELECT
            team,
            AVG(epa) FILTER (WHERE play_type = 'pass') AS pass_epa,
            COUNT(*) FILTER (WHERE play_type = 'pass')::int AS pass_plays,
            AVG(epa) FILTER (WHERE play_type = 'run') AS run_epa,
            COUNT(*) FILTER (WHERE play_type = 'run')::int AS run_plays,
            AVG(epa) FILTER (WHERE down IN (1, 2)) AS early_down_epa,
            COUNT(*) FILTER (WHERE down IN (1, 2))::int AS early_down_plays
          FROM plays
          GROUP BY team
        ),
        deff AS (
          SELECT
            opp AS team,
            AVG(epa) FILTER (WHERE play_type = 'pass') AS pass_epa_allowed,
            COUNT(*) FILTER (WHERE play_type = 'pass')::int AS pass_plays_allowed,
            AVG(epa) FILTER (WHERE play_type = 'run') AS run_epa_allowed,
            COUNT(*) FILTER (WHERE play_type = 'run')::int AS run_plays_allowed,
            AVG(epa) FILTER (WHERE down IN (1, 2)) AS early_down_epa_allowed,
            COUNT(*) FILTER (WHERE down IN (1, 2))::int AS early_down_plays_allowed
          FROM plays
          GROUP BY opp
        )
        SELECT
          COALESCE(o.team, d.team) AS team,
          o.pass_epa, o.pass_plays, o.run_epa, o.run_plays,
          o.early_down_epa, o.early_down_plays,
          d.pass_epa_allowed, d.pass_plays_allowed,
          d.run_epa_allowed, d.run_plays_allowed,
          d.early_down_epa_allowed, d.early_down_plays_allowed
        FROM off o
        FULL OUTER JOIN deff d ON o.team = d.team
    """
    cur = conn.cursor()
    try:
        cur.execute(sql, (int(prior_season),))
    except Exception:
        cur.close()
        return {}
    cols = [d[0] for d in cur.description]
    out: Dict[str, Dict[str, Any]] = {}
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        team = str(r.get("team") or "").strip().upper()
        if team == "LAR":
            team = "LA"
        if not team:
            continue
        out[team] = r
    cur.close()
    return out


def _fetch_st_season(conn: Any, prior_season: int) -> Dict[str, Dict[str, Any]]:
    """Season-average ST EPA from ST KAV weekly (honest ST module)."""
    sql = """
        SELECT
          team,
          COUNT(*)::int AS st_games,
          COALESCE(SUM(
            CASE WHEN raw_st_epa_per_play IS NULL THEN 0 ELSE 1 END
          ), 0)::int AS st_plays_proxy,
          AVG(raw_st_epa_per_play) AS st_epa_per_play
        FROM nfl_dp_team_st_kav_weekly
        WHERE season = %s
        GROUP BY team
    """
    cur = conn.cursor()
    try:
        cur.execute(sql, (int(prior_season),))
    except Exception:
        cur.close()
        return {}
    cols = [d[0] for d in cur.description]
    out: Dict[str, Dict[str, Any]] = {}
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        team = str(r.get("team") or "").strip().upper()
        if team == "LAR":
            team = "LA"
        if not team:
            continue
        # Approximate ST play volume: ~8 ST plays/game × games with ST rows.
        games = int(r.get("st_games") or 0)
        out[team] = {
            "st_epa_per_play": r.get("st_epa_per_play"),
            "st_plays": max(0, games * 8),
            "st_games": games,
        }
    cur.close()
    return out


def _fetch_schedule_rows(conn: Any, prior_season: int) -> List[Dict[str, Any]]:
    sql = """
        SELECT
          game_id,
          week,
          UPPER(TRIM(home_team)) AS home_team,
          UPPER(TRIM(away_team)) AS away_team,
          game_date
        FROM nfl_dp_schedules
        WHERE season = %s
          AND week BETWEEN 1 AND 18
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
        ORDER BY week ASC, game_date ASC NULLS LAST, game_id ASC
    """
    cur = conn.cursor()
    try:
        cur.execute(sql, (int(prior_season),))
    except Exception:
        cur.close()
        return []
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    return rows


def _fetch_rolling_weekly_book(conn: Any, prior_season: int) -> Dict[Tuple[str, int], Any]:
    from src.services.nfl_season_engine.adjusted_sos import OpponentRating

    sql = """
        SELECT week, team, off_epa_per_play_5g, def_epa_allowed_per_play_5g
        FROM nfl_dp_team_rolling_features_weekly
        WHERE season = %s AND week BETWEEN 1 AND 18
    """
    cur = conn.cursor()
    try:
        cur.execute(sql, (int(prior_season),))
    except Exception:
        cur.close()
        return {}
    out: Dict[Tuple[str, int], Any] = {}
    for week, team, off_epa, def_epa in cur.fetchall():
        t = str(team or "").strip().upper()
        if t == "LAR":
            t = "LA"
        w = int(week or 0)
        if not t or w < 1:
            continue
        out[(t, w)] = OpponentRating(
            off_epa=float(off_epa or 0.0),
            def_epa=float(def_epa or 0.0),
            source="time_of_game",
        )
    cur.close()
    return out


def _apply_past_sos_packages(
    packages: Dict[str, Any],
    *,
    schedule_rows: List[Dict[str, Any]],
    weekly_book: Dict[Tuple[str, int], Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Schedule-adjust prior packages; return (packages, sos_meta)."""
    from src.services.nfl_season_engine.adjusted_sos import (
        apply_past_sos_to_package,
        compute_league_past_sos,
        expand_schedule_games,
        rest_days_from_dates,
        season_book_from_packages,
    )

    if not schedule_rows or not packages:
        return packages, {"status": "thin_unavailable", "teams_adjusted": 0}

    team_dates: Dict[str, List[Any]] = {}
    for row in schedule_rows:
        gdate = row.get("game_date")
        if gdate is None:
            continue
        for key in ("home_team", "away_team"):
            t = str(row.get(key) or "").strip().upper()
            if t == "LAR":
                t = "LA"
            if t:
                team_dates.setdefault(t, []).append(gdate)
    games = expand_schedule_games(
        schedule_rows, rest_lookup=rest_days_from_dates(team_dates)
    )
    season_book = season_book_from_packages(packages)
    raw_by_team = {
        team: {
            "off_epa_per_play": float(
                pkg.notes.get("off_epa_raw", pkg.offense.epa_per_play)
            ),
            "def_epa_allowed_per_play": float(
                pkg.notes.get("def_epa_raw", pkg.defense.epa_per_play)
            ),
        }
        for team, pkg in packages.items()
    }
    sos_map = compute_league_past_sos(
        games,
        raw_by_team=raw_by_team,
        weekly_book=weekly_book,
        season_book=season_book,
    )
    out: Dict[str, Any] = {}
    adjusted = 0
    soft: List[str] = []
    hard: List[str] = []
    for team, pkg in packages.items():
        sos = sos_map.get(team)
        if sos is None:
            out[team] = pkg
            continue
        out[team] = apply_past_sos_to_package(pkg, sos)
        if sos.games > 0 and sos.status != "thin_unavailable":
            adjusted += 1
            if sos.schedule_adj_off_epa < sos.raw_off_epa - 1e-9:
                soft.append(team)
            elif sos.schedule_adj_off_epa > sos.raw_off_epa + 1e-9:
                hard.append(team)
    soft_sorted = sorted(
        soft,
        key=lambda t: float(sos_map[t].schedule_adj_off_epa - sos_map[t].raw_off_epa),
    )
    hard_sorted = sorted(
        hard,
        key=lambda t: float(sos_map[t].raw_off_epa - sos_map[t].schedule_adj_off_epa),
    )
    meta = {
        "status": "applied",
        "teams_adjusted": adjusted,
        "time_of_game_share_mean": round(
            sum(s.time_of_game_share for s in sos_map.values()) / max(1, len(sos_map)),
            4,
        ),
        "soft_slate_examples": soft_sorted[:5],
        "hard_slate_examples": hard_sorted[:5],
        "future_schedule_excluded": True,
    }
    return out, meta


def build(season: int, prior_season: int, dsn: Optional[str]) -> Tuple[Path, Path]:
    from src.services.nfl_season_engine.efficiency_backbone import (
        EFFICIENCY_BACKBONE_VERSION,
        packages_from_team_rows,
        package_to_strength_indices,
        rank_packages,
    )

    rows: List[Dict[str, Any]] = []
    splits: Dict[str, Dict[str, Any]] = {}
    st_map: Dict[str, Dict[str, Any]] = {}
    schedule_rows: List[Dict[str, Any]] = []
    weekly_book: Dict[Tuple[str, int], Any] = {}
    used_dsn = ""
    last_err: Optional[Exception] = None
    for candidate in _candidate_dsns(dsn):
        try:
            with _connect(candidate) as conn:
                rows = _fetch_season_avgs(conn, prior_season)
                if rows:
                    splits = _fetch_offensive_splits(conn, prior_season)
                    st_map = _fetch_st_season(conn, prior_season)
                    schedule_rows = _fetch_schedule_rows(conn, prior_season)
                    weekly_book = _fetch_rolling_weekly_book(conn, prior_season)
                    used_dsn = candidate.split("@")[-1] if "@" in candidate else candidate
                    break
        except Exception as exc:  # pragma: no cover - ops path
            last_err = exc
            continue
    if not rows:
        raise SystemExit(
            f"No situational weekly rows for season={prior_season}. last_err={last_err}"
        )

    # Normalize column names for backbone builder.
    norm_rows: List[Dict[str, Any]] = []
    for r in rows:
        team = str(r.get("team") or "").strip().upper()
        if team == "LAR":
            team = "LA"
        sp = splits.get(team) or {}
        st = st_map.get(team) or {}
        row: Dict[str, Any] = {
            "team": team,
            "n_weeks": int(r.get("n_weeks") or 0),
            "games_played": int(r.get("n_weeks") or 0),
            "offensive_plays": int(r.get("offensive_plays") or 0),
            "defensive_plays": int(r.get("defensive_plays") or 0),
            "pass_plays": int(sp.get("pass_plays") or r.get("pass_plays") or 0),
            "run_plays": int(sp.get("run_plays") or r.get("run_plays") or 0),
            "early_down_plays": int(
                sp.get("early_down_plays") or r.get("early_down_plays") or 0
            ),
            "explosive_pass_plays": int(r.get("explosive_pass_plays") or 0),
            "explosive_pass_allowed": int(r.get("explosive_pass_allowed") or 0),
            "off_epa_per_play": float(r.get("off_epa") or 0.0),
            "def_epa_allowed_per_play": float(r.get("def_epa_allowed") or 0.0),
            "success_rate_offense": float(r.get("success_rate_offense") or 0.44),
            "success_rate_defense_allowed": float(
                r.get("success_rate_defense_allowed") or 0.44
            ),
            "pass_rate": float(r.get("pass_rate") or 0.58),
            "early_down_pass_rate": float(r.get("early_down_pass_rate") or 0.55),
            "third_down_conversion_rate": float(
                r.get("third_down_conversion_rate") or 0.40
            ),
            "red_zone_td_rate": float(r.get("red_zone_td_rate") or 0.55),
            "pressure_rate_generated": float(r.get("pressure_generated") or 0.0),
            "pressure_rate_allowed": float(r.get("pressure_allowed") or 0.0),
        }
        if sp.get("pass_epa") is not None:
            row["pass_epa"] = float(sp["pass_epa"])
        if sp.get("run_epa") is not None:
            row["run_epa"] = float(sp["run_epa"])
        if sp.get("early_down_epa") is not None:
            row["early_down_epa"] = float(sp["early_down_epa"])
        if sp.get("pass_epa_allowed") is not None:
            row["pass_epa_allowed"] = float(sp["pass_epa_allowed"])
            row["pass_plays_allowed"] = int(sp.get("pass_plays_allowed") or 0)
        if sp.get("run_epa_allowed") is not None:
            row["run_epa_allowed"] = float(sp["run_epa_allowed"])
            row["run_plays_allowed"] = int(sp.get("run_plays_allowed") or 0)
        if sp.get("early_down_epa_allowed") is not None:
            row["early_down_epa_allowed"] = float(sp["early_down_epa_allowed"])
            row["early_down_plays_allowed"] = int(
                sp.get("early_down_plays_allowed") or 0
            )
        if st.get("st_epa_per_play") is not None:
            row["st_epa_per_play"] = float(st["st_epa_per_play"])
            row["st_plays"] = int(st.get("st_plays") or 0)
        norm_rows.append(row)

    packages = packages_from_team_rows(
        norm_rows,
        as_of=date.today().isoformat(),
        source="packaged_efficiency_backbone",
        prior_season=int(prior_season),
    )
    if len(packages) != 32:
        raise SystemExit(f"Expected 32 teams, got {len(packages)}: {sorted(packages)}")

    packages, sos_meta = _apply_past_sos_packages(
        packages, schedule_rows=schedule_rows, weekly_book=weekly_book
    )

    teams_payload: Dict[str, Dict[str, Any]] = {}
    legacy_teams: Dict[str, Dict[str, Any]] = {}
    st_nonzero = 0
    splits_ok = 0
    for team, pkg in packages.items():
        idx = package_to_strength_indices(pkg)
        if abs(float(pkg.st_epa_per_play)) > 1e-9 or pkg.st_plays > 0:
            st_nonzero += 1
        if pkg.notes.get("has_true_pass_run_splits"):
            splits_ok += 1
        past_sos = dict(pkg.notes.get("past_sos") or {})
        teams_payload[team] = {
            **pkg.to_dict(),
            **{k: v for k, v in idx.items() if k != "drivers"},
            "drivers": idx.get("drivers"),
            "n_weeks": pkg.games_played,
            "offensive_plays": pkg.offense.plays,
            "defensive_plays": pkg.defense.plays,
            "off_epa_per_play": round(pkg.offense.epa_per_play, 6),
            "def_epa_allowed_per_play": round(pkg.defense.epa_per_play, 6),
            "pass_epa": round(pkg.offense.pass_epa, 6),
            "run_epa": round(pkg.offense.run_epa, 6),
            "early_down_epa": round(pkg.offense.early_down_epa, 6),
            "pressure_rate_generated": round(pkg.defense.pressure_rate, 6),
            "pressure_rate_allowed": round(pkg.offense.pressure_rate, 6),
            "success_rate_offense": round(pkg.offense.success_rate, 6),
            "success_rate_defense_allowed": round(pkg.defense.success_rate, 6),
            "explosive_rate_offense": round(pkg.offense.explosive_rate, 6),
            "explosive_rate_defense_allowed": round(pkg.defense.explosive_rate, 6),
            "red_zone_td_rate": round(pkg.offense.red_zone_td_rate, 6),
            "pass_rate": round(pkg.pass_rate, 6),
            "past_sos": past_sos,
        }
        legacy_teams[team] = {
            "off_epa_per_play": round(pkg.offense.epa_per_play, 6),
            "def_epa_allowed_per_play": round(pkg.defense.epa_per_play, 6),
            "pressure_rate_generated": round(pkg.defense.pressure_rate, 6),
            "pressure_rate_allowed": round(pkg.offense.pressure_rate, 6),
            "offense_index": float(idx["offense_index"]),
            "defense_index": float(idx["defense_index"]),
            "pace_factor": float(idx["pace_factor"]),
            "pass_rate_bias": float(idx["pass_rate_bias"]),
            "st_index": float(idx["st_index"]),
            "explosiveness": float(idx["explosiveness"]),
            "variance": float(idx["variance"]),
            "pass_epa": round(pkg.offense.pass_epa, 6),
            "run_epa": round(pkg.offense.run_epa, 6),
            "early_down_epa": round(pkg.offense.early_down_epa, 6),
            "n_weeks": pkg.games_played,
            "offensive_plays": pkg.offense.plays,
            "defensive_plays": pkg.defense.plays,
        }

    ranked = rank_packages(packages)
    payload = {
        "season": int(season),
        "prior_season": int(prior_season),
        "source": "packaged_efficiency_backbone",
        "version": EFFICIENCY_BACKBONE_VERSION,
        "source_table": (
            "nfl_dp_team_situational_weekly+pbp_splits+st_kav+"
            "schedules+rolling_for_past_sos"
        ),
        "source_filter": (
            "source=nflverse; pbp weeks 1-18; st_kav season avg; "
            "past SOS = opponent rolling W-1 (else season approximate)"
        ),
        "source_host": used_dsn,
        "as_of": date.today().isoformat(),
        "method": (
            "efficiency_backbone_v1.1_play_weighted_situational_splits_st"
            "+past_sos_schedule_adjusted_prior"
        ),
        "conversion": (
            "efficiency_backbone.package_to_strength_indices "
            "(EPA+pressure base + soft success/explosive/RZ + pass/run/early "
            "EPA + modest ST); prior EPA schedule-adjusted via Past SOS"
        ),
        "notes": (
            f"{season} launch priors = {prior_season} season play-weighted efficiency "
            "package (situational + true pass/run/early-down EPA from PBP + ST KAV) "
            "with Past SOS schedule-adjusted performance on the prior side only. "
            "Future 2026 SOS excluded from intrinsic PR. "
            "See data/ops/nfl-model-vision.md."
        ),
        "coverage": {
            "teams_with_st": st_nonzero,
            "teams_with_pass_run_splits": splits_ok,
            "st_source": "nfl_dp_team_st_kav_weekly" if st_map else "missing",
            "splits_source": "nfl_dp_play_by_play" if splits else "missing",
            "past_sos": sos_meta,
            "schedule_games": len(schedule_rows),
            "rolling_week_keys": len(weekly_book),
        },
        "team_count": len(teams_payload),
        "hierarchy_top8": [t for t, _ in ranked[:8]],
        "hierarchy_bottom5": [t for t, _ in ranked[-5:]],
        "teams": teams_payload,
    }
    backbone_path = OUT_DIR / f"nfl_team_efficiency_backbone_{season}.json"
    backbone_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    legacy = {
        "season": int(season),
        "prior_season": int(prior_season),
        "source": "packaged_epa_prior",
        "source_table": "nfl_dp_team_situational_weekly",
        "source_filter": "source=nflverse",
        "source_host": used_dsn,
        "as_of": date.today().isoformat(),
        "method": "efficiency_backbone_v1.1_compat_epa_priors",
        "conversion": "efficiency_backbone.package_to_strength_indices",
        "notes": (
            f"Legacy compat mirror of nfl_team_efficiency_backbone_{season}.json "
            "(v1.1). Prefer the efficiency backbone artifact."
        ),
        "team_count": len(legacy_teams),
        "teams": legacy_teams,
    }
    legacy_path = OUT_DIR / f"nfl_team_epa_priors_{season}.json"
    legacy_path.write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "teams": len(packages),
                "st_teams": st_nonzero,
                "split_teams": splits_ok,
                "past_sos": sos_meta,
                "top8": payload["hierarchy_top8"],
                "bottom5": payload["hierarchy_bottom5"],
            },
            indent=2,
        )
    )
    return backbone_path, legacy_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--prior-season", type=int, default=None)
    parser.add_argument("--dsn", default="")
    args = parser.parse_args()
    prior = int(args.prior_season) if args.prior_season else int(args.season) - 1
    backbone, legacy = build(args.season, prior, args.dsn or None)
    print(f"Wrote {backbone}")
    print(f"Wrote {legacy}")


if __name__ == "__main__":
    main()
