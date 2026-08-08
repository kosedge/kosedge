#!/usr/bin/env python3
"""Rebuild packaged NFL efficiency-backbone artifact (Sprint 2).

Source: local / env Postgres ``nfl_dp_team_situational_weekly`` (source=nflverse).

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


def build(season: int, prior_season: int, dsn: Optional[str]) -> Tuple[Path, Path]:
    from src.services.nfl_season_engine.efficiency_backbone import (
        EFFICIENCY_BACKBONE_VERSION,
        packages_from_team_rows,
        package_to_strength_indices,
        rank_packages,
    )

    rows: List[Dict[str, Any]] = []
    used_dsn = ""
    last_err: Optional[Exception] = None
    for candidate in _candidate_dsns(dsn):
        try:
            with _connect(candidate) as conn:
                rows = _fetch_season_avgs(conn, prior_season)
            if rows:
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
        norm_rows.append(
            {
                "team": team,
                "n_weeks": int(r.get("n_weeks") or 0),
                "games_played": int(r.get("n_weeks") or 0),
                "offensive_plays": int(r.get("offensive_plays") or 0),
                "defensive_plays": int(r.get("defensive_plays") or 0),
                "pass_plays": int(r.get("pass_plays") or 0),
                "run_plays": int(r.get("run_plays") or 0),
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
        )

    packages = packages_from_team_rows(
        norm_rows,
        as_of=date.today().isoformat(),
        source="packaged_efficiency_backbone",
        prior_season=int(prior_season),
    )
    if len(packages) != 32:
        raise SystemExit(f"Expected 32 teams, got {len(packages)}: {sorted(packages)}")

    teams_payload: Dict[str, Dict[str, Any]] = {}
    legacy_teams: Dict[str, Dict[str, Any]] = {}
    for team, pkg in packages.items():
        idx = package_to_strength_indices(pkg)
        teams_payload[team] = {
            **pkg.to_dict(),
            **idx,
            "n_weeks": pkg.games_played,
            "offensive_plays": pkg.offense.plays,
            "defensive_plays": pkg.defense.plays,
            "off_epa_per_play": round(pkg.offense.epa_per_play, 6),
            "def_epa_allowed_per_play": round(pkg.defense.epa_per_play, 6),
            "pressure_rate_generated": round(pkg.defense.pressure_rate, 6),
            "pressure_rate_allowed": round(pkg.offense.pressure_rate, 6),
            "success_rate_offense": round(pkg.offense.success_rate, 6),
            "success_rate_defense_allowed": round(pkg.defense.success_rate, 6),
            "explosive_rate_offense": round(pkg.offense.explosive_rate, 6),
            "explosive_rate_defense_allowed": round(pkg.defense.explosive_rate, 6),
            "red_zone_td_rate": round(pkg.offense.red_zone_td_rate, 6),
            "pass_rate": round(pkg.pass_rate, 6),
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
        "source_table": "nfl_dp_team_situational_weekly",
        "source_filter": "source=nflverse",
        "source_host": used_dsn,
        "as_of": date.today().isoformat(),
        "method": "efficiency_backbone_v1_play_weighted_situational",
        "conversion": (
            "efficiency_backbone.package_to_strength_indices "
            "(EPA+pressure base + soft success/explosive/RZ; ST module)"
        ),
        "notes": (
            f"{season} launch priors = {prior_season} season play-weighted efficiency "
            "package from nfl_dp_team_situational_weekly. Feeds existing TeamStrength "
            "slot (offense_index/defense_index/pace). See data/ops/nfl-model-vision.md."
        ),
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
        "method": "efficiency_backbone_v1_compat_epa_priors",
        "conversion": "efficiency_backbone.package_to_strength_indices",
        "notes": (
            f"Legacy compat mirror of nfl_team_efficiency_backbone_{season}.json "
            "(Sprint 2). Prefer the efficiency backbone artifact."
        ),
        "team_count": len(legacy_teams),
        "teams": legacy_teams,
    }
    legacy_path = OUT_DIR / f"nfl_team_epa_priors_{season}.json"
    legacy_path.write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")
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
