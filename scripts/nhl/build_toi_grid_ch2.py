#!/usr/bin/env python3
"""Rebuild NHL Ch2 TOI grid + goalie tandem from raw skater/goalie boxes.

Skater TOI shares (weighted 0.20/0.30/0.50) sum to 1.0 per team.
Goalie GS shares sum to 1.0 (starter / backup / residual).

Does not emit KEI. Does not retune NHL_TEAM_CARRY_SHRINK.
Does not rewrite nhl_team_prior_2026.json.

Usage:
  python3 scripts/nhl/build_toi_grid_ch2.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "services/model-service/src/services/nhl_season_engine/data"
SKATER_BOX = DATA / "nhl_skater_box_2023_2025.json"
GOALIE_BOX = DATA / "nhl_goalie_box_2023_2025.json"
OUT_TOI = DATA / "nhl_toi_grid_2026.json"
OUT_TANDEM = DATA / "nhl_goalie_tandem_2026.json"

# Keep import path working when run as a script.
import sys

sys.path.insert(0, str(ROOT / "services" / "model-service"))
from src.services.nhl_data import NHL_TEAM_ABBREVS  # noqa: E402
from src.services.nhl_season_engine import priors as P  # noqa: E402

EXPECTED_TEAMS = 32
SHARE_EPS = 1e-6
# Opening-night dressing: 12 F + 6 D. Depth beyond 18 is folded out before normalize.
SKATERS_PER_TEAM = 18


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _primary_team(team_field: Any) -> Optional[str]:
    """Multi-team rows like 'MIN,VAN' → last abbrev (most recent club)."""
    if team_field is None:
        return None
    parts = [p.strip().upper() for p in str(team_field).split(",") if p.strip()]
    return parts[-1] if parts else None


def _weighted_mean(
    season_values: Dict[int, float],
    weights: Dict[int, float],
) -> Optional[float]:
    num = 0.0
    den = 0.0
    for sid, val in season_values.items():
        w = float(weights.get(sid) or 0.0)
        if w <= 0 or val is None:
            continue
        num += w * float(val)
        den += w
    if den <= 0:
        return None
    return num / den


def build_toi_grid(skater_pack: Dict[str, Any]) -> Dict[str, Any]:
    weights = dict(P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID)
    # player_id → {season_id: toi_per_game}, plus meta from latest season.
    by_player: Dict[str, Dict[str, Any]] = {}
    for season_key, rows in (skater_pack.get("by_season") or {}).items():
        season_id = int(season_key)
        for row in rows or []:
            pid = str(row.get("player_id") or "")
            if not pid:
                continue
            toi = row.get("toi_per_game")
            if toi is None:
                continue
            gp = float(row.get("gp") or 0)
            if gp <= 0:
                continue
            slot = by_player.setdefault(
                pid,
                {
                    "player_id": pid,
                    "player_name": row.get("player_name"),
                    "position": row.get("position"),
                    "toi_by_season": {},
                    "team_by_season": {},
                    "gp_by_season": {},
                },
            )
            slot["toi_by_season"][season_id] = float(toi)
            slot["team_by_season"][season_id] = _primary_team(row.get("team"))
            slot["gp_by_season"][season_id] = gp
            prev = slot.get("_max_season") or 0
            if season_id >= prev:
                slot["_max_season"] = season_id
                slot["player_name"] = row.get("player_name") or slot.get("player_name")
                slot["position"] = row.get("position") or slot.get("position")

    # Assign each player to a team (latest season with a team).
    team_bags: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for pid, slot in by_player.items():
        seasons = sorted(slot["toi_by_season"])
        team = None
        for sid in reversed(seasons):
            team = slot["team_by_season"].get(sid)
            if team:
                break
        if not team or team not in NHL_TEAM_ABBREVS:
            continue
        toi_w = _weighted_mean(slot["toi_by_season"], weights)
        if toi_w is None or toi_w <= 0:
            continue
        team_bags[team].append(
            {
                "player_id": pid,
                "player_name": slot.get("player_name"),
                "position": slot.get("position"),
                "toi_sec_w": toi_w,
                "seasons_used": sorted(slot["toi_by_season"]),
            }
        )

    teams_out: Dict[str, List[Dict[str, Any]]] = {}
    for team in NHL_TEAM_ABBREVS:
        rows = sorted(team_bags.get(team) or [], key=lambda x: -x["toi_sec_w"])
        rows = rows[:SKATERS_PER_TEAM]
        total = sum(r["toi_sec_w"] for r in rows)
        if total <= 0:
            teams_out[team] = []
            continue
        normalized: List[Dict[str, Any]] = []
        for r in rows:
            share = r["toi_sec_w"] / total
            normalized.append(
                {
                    "player_id": r["player_id"],
                    "player_name": r["player_name"],
                    "position": r["position"],
                    "toi_share": round(share, 8),
                    "toi_min": round(share * float(P.NHL_TOI_GRID_SKATER_MINUTES), 4),
                    "toi_sec_w": round(r["toi_sec_w"], 4),
                    "seasons_used": r["seasons_used"],
                }
            )
        # Fix residual on largest share so Σ share == 1 exactly.
        ssum = sum(r["toi_share"] for r in normalized)
        if normalized and abs(ssum - 1.0) > 0:
            normalized[0]["toi_share"] = round(
                normalized[0]["toi_share"] + (1.0 - ssum), 8
            )
            normalized[0]["toi_min"] = round(
                normalized[0]["toi_share"] * float(P.NHL_TOI_GRID_SKATER_MINUTES), 4
            )
        teams_out[team] = normalized

    return {
        "engine_version": P.ENGINE_VERSION,
        "as_of": _utc_today(),
        "object": "toi_grid",
        "season_target": "2026-27",
        "source": "nhl_skater_box_2023_2025.json",
        "PLAYER_YEAR_WEIGHTS": P.PLAYER_YEAR_WEIGHTS,
        "PLAYER_YEAR_WEIGHTS_BY_SEASON_ID": {
            str(k): v for k, v in P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID.items()
        },
        "NHL_TOI_GRID_SKATER_MINUTES": P.NHL_TOI_GRID_SKATER_MINUTES,
        "skaters_per_team": SKATERS_PER_TEAM,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "formula": (
            "toi_sec_w = Σ w_y · toi_per_game_y (renormalized); "
            "keep top 18 by toi_sec_w; toi_share = toi_sec_w / Σ_18; "
            "toi_min = share × 300"
        ),
        "team_count": EXPECTED_TEAMS,
        "teams": teams_out,
        "does_not": [
            "emit KEI / fill KEINHL",
            "retune NHL_TEAM_CARRY_SHRINK",
            "rebase nhl_team_prior_2026.json",
            "xG",
            "situation",
            "NBA/WNBA minute copy",
        ],
    }


def build_goalie_tandem(goalie_pack: Dict[str, Any]) -> Dict[str, Any]:
    weights = dict(P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID)
    by_player: Dict[str, Dict[str, Any]] = {}
    for season_key, rows in (goalie_pack.get("by_season") or {}).items():
        season_id = int(season_key)
        for row in rows or []:
            pid = str(row.get("player_id") or "")
            if not pid:
                continue
            gs = row.get("gs")
            if gs is None:
                continue
            gp = float(row.get("gp") or 0)
            if gp <= 0 and float(gs or 0) <= 0:
                continue
            slot = by_player.setdefault(
                pid,
                {
                    "player_id": pid,
                    "player_name": row.get("player_name"),
                    "gs_by_season": {},
                    "gp_by_season": {},
                    "toi_by_season": {},
                    "team_by_season": {},
                },
            )
            slot["gs_by_season"][season_id] = float(gs)
            slot["gp_by_season"][season_id] = gp
            if row.get("toi") is not None:
                slot["toi_by_season"][season_id] = float(row["toi"])
            slot["team_by_season"][season_id] = _primary_team(row.get("team"))
            prev = slot.get("_max_season") or 0
            if season_id >= prev:
                slot["_max_season"] = season_id
                slot["player_name"] = row.get("player_name") or slot.get("player_name")

    team_bags: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for pid, slot in by_player.items():
        seasons = sorted(slot["gs_by_season"])
        team = None
        for sid in reversed(seasons):
            team = slot["team_by_season"].get(sid)
            if team:
                break
        if not team or team not in NHL_TEAM_ABBREVS:
            continue
        gs_w = _weighted_mean(slot["gs_by_season"], weights)
        if gs_w is None or gs_w < 0:
            continue
        if gs_w == 0:
            continue
        team_bags[team].append(
            {
                "player_id": pid,
                "player_name": slot.get("player_name"),
                "gs_w": gs_w,
                "gp_w": _weighted_mean(slot["gp_by_season"], weights) or 0.0,
                "toi_w": _weighted_mean(slot["toi_by_season"], weights),
                "seasons_used": sorted(slot["gs_by_season"]),
            }
        )

    teams_out: Dict[str, Dict[str, Any]] = {}
    for team in NHL_TEAM_ABBREVS:
        rows = sorted(team_bags.get(team) or [], key=lambda x: -x["gs_w"])
        total = sum(r["gs_w"] for r in rows)
        if total <= 0 or not rows:
            teams_out[team] = {
                "team": team,
                "starter": None,
                "backup": None,
                "residual": [],
                "gs_share_sum": 0.0,
                "goalies": [],
            }
            continue

        goalies: List[Dict[str, Any]] = []
        for i, r in enumerate(rows):
            share = r["gs_w"] / total
            role = "starter" if i == 0 else "backup" if i == 1 else "residual"
            goalies.append(
                {
                    "player_id": r["player_id"],
                    "player_name": r["player_name"],
                    "role": role,
                    "gs_share": round(share, 8),
                    "gs_w": round(r["gs_w"], 4),
                    "gp_w": round(r["gp_w"], 4),
                    "toi_w": None if r["toi_w"] is None else round(r["toi_w"], 2),
                    "seasons_used": r["seasons_used"],
                }
            )
        ssum = sum(g["gs_share"] for g in goalies)
        if goalies and abs(ssum - 1.0) > 0:
            goalies[0]["gs_share"] = round(goalies[0]["gs_share"] + (1.0 - ssum), 8)

        teams_out[team] = {
            "team": team,
            "starter": goalies[0] if goalies else None,
            "backup": goalies[1] if len(goalies) > 1 else None,
            "residual": goalies[2:],
            "gs_share_sum": round(sum(g["gs_share"] for g in goalies), 8),
            "goalies": goalies,
        }

    return {
        "engine_version": P.ENGINE_VERSION,
        "as_of": _utc_today(),
        "object": "goalie_tandem",
        "season_target": "2026-27",
        "source": "nhl_goalie_box_2023_2025.json",
        "PLAYER_YEAR_WEIGHTS": P.PLAYER_YEAR_WEIGHTS,
        "PLAYER_YEAR_WEIGHTS_BY_SEASON_ID": {
            str(k): v for k, v in P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID.items()
        },
        "NHL_GOALIE_TANDEM_SHARE_SUM": P.NHL_GOALIE_TANDEM_SHARE_SUM,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "STARTER_GATE": P.STARTER_GATE,
        "formula": (
            "gs_w = Σ w_y · gs_y (renormalized); "
            "gs_share = gs_w / Σ_team; roles starter/backup/residual"
        ),
        "team_count": EXPECTED_TEAMS,
        "teams": teams_out,
        "does_not": [
            "emit KEI / fill KEINHL",
            "goalie PLAY tags (STARTER_GATE=unknown)",
            "retune NHL_TEAM_CARRY_SHRINK",
            "xG",
            "situation",
        ],
    }


def main() -> None:
    skaters = json.loads(SKATER_BOX.read_text(encoding="utf-8"))
    goalies = json.loads(GOALIE_BOX.read_text(encoding="utf-8"))
    toi = build_toi_grid(skaters)
    tandem = build_goalie_tandem(goalies)

    # Identity gates before write.
    for team, rows in toi["teams"].items():
        if not rows:
            raise SystemExit(f"empty TOI grid for {team}")
        s = sum(r["toi_share"] for r in rows)
        if abs(s - 1.0) > 1e-6:
            raise SystemExit(f"TOI share sum {team}={s}")
        mins = sum(r["toi_min"] for r in rows)
        if abs(mins - float(P.NHL_TOI_GRID_SKATER_MINUTES)) > 0.05:
            raise SystemExit(f"TOI minutes sum {team}={mins}")

    for team, row in tandem["teams"].items():
        s = float(row.get("gs_share_sum") or 0.0)
        if s <= 0:
            raise SystemExit(f"empty goalie tandem for {team}")
        if abs(s - 1.0) > 1e-6:
            raise SystemExit(f"goalie share sum {team}={s}")

    if len(toi["teams"]) != EXPECTED_TEAMS or len(tandem["teams"]) != EXPECTED_TEAMS:
        raise SystemExit("expected 32 teams in both packs")

    OUT_TOI.write_text(json.dumps(toi, indent=2) + "\n", encoding="utf-8")
    OUT_TANDEM.write_text(json.dumps(tandem, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_TOI}")
    print(f"wrote {OUT_TANDEM}")
    # Sample anchors
    col = toi["teams"]["COL"][:3]
    print("COL top TOI", [(r["player_name"], r["toi_share"], r["toi_min"]) for r in col])
    car = tandem["teams"]["CAR"]
    print(
        "CAR tandem",
        car["starter"]["player_name"] if car["starter"] else None,
        car["starter"]["gs_share"] if car["starter"] else None,
        car["backup"]["player_name"] if car["backup"] else None,
        car["backup"]["gs_share"] if car["backup"] else None,
    )


if __name__ == "__main__":
    main()
