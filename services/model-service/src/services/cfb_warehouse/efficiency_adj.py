"""Opponent-adjusted team-week efficiency from owned PBP (leakage-safe).

Week-W snapshot uses only same-season plays with ``week < W``.
``feature_week`` = last included week (0 if none) so warehouse fallback
``feature_week < game_week`` holds. Shrink thin samples to league mean.
FCS plays are kept and flagged — not deleted.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.garbage import DEFAULTS as GARBAGE_DEFAULTS
from src.services.cfb_warehouse.garbage import weight_play
from src.services.cfb_warehouse.identity import known_engine_codes, resolve_team_code
from src.services.cfb_warehouse.leakage import era_tag
from src.services.cfb_warehouse.paths import clean_dir, pbp_raw_dir

SHRINK_PLAYS = 80.0
ADJ_ITERS = 4
EXPLOSIVE_EPA = 1.0
EXPLOSIVE_YARDS = 15
GAME_COMPLETE_BUFFER = timedelta(hours=4)
PBP_SEASONS = tuple(range(2014, 2026))

PBP_READ_COLS = (
    "season",
    "week",
    "game_id",
    "pos_team",
    "def_pos_team",
    "EPA",
    "EPA_success",
    "statYardage",
    "pass",
    "rush",
    "scrimmage_play",
    "stuffed_run",
    "rz_play",
    "pos_score_diff",
    "start.TimeSecsRem",
    "under_2",
    "half",
    "period",
)


def _f(raw: Any, default: float = 0.0) -> float:
    if raw is None or raw == "":
        return default
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(val):
        return default
    return val


def _truthy(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw in (None, "", 0, "0"):
        return False
    return str(raw).lower() in {"1", "true", "t", "yes"}


def _team_id(name: Any, known: Mapping[str, Any]) -> Tuple[str, bool]:
    label = str(name or "").strip()
    if not label or label.lower() in {"nan", "none", "nat", "<na>"}:
        return "", True
    code = resolve_team_code(name=label, abbr="", known_codes=known)
    if code:
        return code, False
    return f"fcs:{label}", True


def filter_plays_before_week(
    plays: Iterable[Mapping[str, Any]],
    *,
    season: int,
    week: int,
) -> list[dict[str, Any]]:
    """Same-season plays with week < W. Never include week ≥ W."""
    out: list[dict[str, Any]] = []
    for play in plays:
        if int(_f(play.get("season"), 0)) != int(season):
            continue
        if int(_f(play.get("week"), 0)) >= int(week):
            continue
        out.append(dict(play))
    return out


def assert_no_future_weeks(
    rows: Sequence[Mapping[str, Any]],
    *,
    season: int,
    week: int,
    week_key: str = "max_week_included",
) -> None:
    for row in rows:
        included = int(_f(row.get(week_key, row.get("feature_week")), -1))
        if included >= int(week):
            raise ValueError(
                f"CFB leakage: week {week} snapshot includes week {included} "
                f"(season={season} row={row.get('team_id')})"
            )


def aggregate_team_games(
    plays: Sequence[Mapping[str, Any]],
    *,
    known: Optional[Mapping[str, Any]] = None,
    kickoff_by_game: Optional[Mapping[str, Any]] = None,
) -> list[dict[str, Any]]:
    """One offense row per (game, team) from scrimmage plays."""
    known = known if known is not None else known_engine_codes()
    kickoff_by_game = kickoff_by_game or {}
    buckets: Dict[Tuple[Any, ...], Dict[str, float]] = {}
    meta: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

    for play in plays:
        if play.get("scrimmage_play") is not None and not _truthy(play.get("scrimmage_play")):
            continue
        epa = play.get("EPA")
        if epa is None or epa == "":
            continue
        epa_f = _f(epa, default=float("nan"))
        if not math.isfinite(epa_f):
            continue
        off_id, fcs_off = _team_id(play.get("pos_team"), known)
        def_id, fcs_def = _team_id(play.get("def_pos_team"), known)
        if not off_id or not def_id:
            continue
        w = weight_play(play)
        if w <= 0:
            continue
        gid = str(play.get("game_id") or "")
        season = int(_f(play.get("season"), 0))
        week = int(_f(play.get("week"), 0))
        key = (season, week, gid, off_id, def_id)
        acc = buckets.setdefault(
            key,
            {
                "w": 0.0,
                "n": 0.0,
                "epa": 0.0,
                "success": 0.0,
                "pass_w": 0.0,
                "pass_epa": 0.0,
                "rush_w": 0.0,
                "rush_epa": 0.0,
                "explosive": 0.0,
                "stuff_w": 0.0,
                "stuff": 0.0,
                "rz_w": 0.0,
                "rz_epa": 0.0,
            },
        )
        acc["w"] += w
        acc["n"] += 1.0
        acc["epa"] += w * epa_f
        acc["success"] += w * (1.0 if _truthy(play.get("EPA_success")) else 0.0)
        yards = _f(play.get("statYardage"))
        if epa_f >= EXPLOSIVE_EPA or yards >= EXPLOSIVE_YARDS:
            acc["explosive"] += w
        if _truthy(play.get("pass")):
            acc["pass_w"] += w
            acc["pass_epa"] += w * epa_f
        if _truthy(play.get("rush")):
            acc["rush_w"] += w
            acc["rush_epa"] += w * epa_f
            acc["stuff_w"] += w
            if _truthy(play.get("stuffed_run")):
                acc["stuff"] += w
        if _truthy(play.get("rz_play")):
            acc["rz_w"] += w
            acc["rz_epa"] += w * epa_f
        meta[key] = {
            "season": season,
            "week": week,
            "game_id": gid,
            "team_id": off_id,
            "opponent_id": def_id,
            "fcs_offense": fcs_off,
            "fcs_defense": fcs_def,
            "fcs_opponent": fcs_off or fcs_def,
        }

    rows: list[dict[str, Any]] = []
    for key, acc in buckets.items():
        w = acc["w"] or 1.0
        info = meta[key]
        kick = kickoff_by_game.get(str(info["game_id"]))
        available_at = None
        if kick:
            try:
                dt = datetime.fromisoformat(str(kick).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                available_at = (dt + GAME_COMPLETE_BUFFER).isoformat()
            except ValueError:
                available_at = None
        rows.append(
            {
                **info,
                "n_plays": int(acc["n"]),
                "n_plays_weighted": round(w, 3),
                "off_epa_raw": acc["epa"] / w,
                "off_success_raw": acc["success"] / w,
                "off_pass_epa_raw": (acc["pass_epa"] / acc["pass_w"]) if acc["pass_w"] else None,
                "off_rush_epa_raw": (acc["rush_epa"] / acc["rush_w"]) if acc["rush_w"] else None,
                "off_explosive_rate": acc["explosive"] / w,
                "stuff_rate": (acc["stuff"] / acc["stuff_w"]) if acc["stuff_w"] else None,
                "rz_epa_raw": (acc["rz_epa"] / acc["rz_w"]) if acc["rz_w"] else None,
                "available_at": available_at,
                "era_tag": era_tag(info["season"]),
            }
        )
    return rows


def iterative_adjust(
    team_games: Sequence[Mapping[str, Any]],
    *,
    iters: int = ADJ_ITERS,
) -> Dict[str, Dict[str, float]]:
    """adjusted = observed − opponent expected. Centered at league mean 0."""
    off_sums: Dict[str, float] = defaultdict(float)
    off_w: Dict[str, float] = defaultdict(float)
    def_sums: Dict[str, float] = defaultdict(float)
    def_w: Dict[str, float] = defaultdict(float)
    games_by_team: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)

    for row in team_games:
        if not math.isfinite(_f(row.get("off_epa_raw"), default=float("nan"))):
            continue
        team = str(row["team_id"])
        w = _f(row.get("n_plays_weighted"), 1.0)
        off_sums[team] += w * _f(row.get("off_epa_raw"))
        off_w[team] += w
        opp = str(row["opponent_id"])
        def_sums[opp] += w * _f(row.get("off_epa_raw"))
        def_w[opp] += w
        games_by_team[team].append(row)

    teams = sorted(set(off_w) | set(def_w))
    off_adj = {t: (off_sums[t] / off_w[t] if off_w[t] else 0.0) for t in teams}
    def_adj = {t: (def_sums[t] / def_w[t] if def_w[t] else 0.0) for t in teams}

    def _center(d: Dict[str, float]) -> None:
        if not d:
            return
        mu = sum(d.values()) / len(d)
        for k in d:
            d[k] -= mu

    _center(off_adj)
    _center(def_adj)

    for _ in range(int(iters)):
        new_off: Dict[str, float] = {}
        allowed: Dict[str, List[Tuple[float, float, str]]] = defaultdict(list)
        for team in teams:
            num = den = 0.0
            for row in games_by_team.get(team, []):
                w = _f(row.get("n_plays_weighted"), 1.0)
                opp = str(row["opponent_id"])
                num += w * (_f(row.get("off_epa_raw")) - def_adj.get(opp, 0.0))
                den += w
            new_off[team] = num / den if den else 0.0
        for team, rows in games_by_team.items():
            for row in rows:
                opp = str(row["opponent_id"])
                w = _f(row.get("n_plays_weighted"), 1.0)
                allowed[opp].append((w, _f(row.get("off_epa_raw")), team))
        new_def: Dict[str, float] = {}
        for team in teams:
            num = den = 0.0
            for w, epa, offense in allowed.get(team, []):
                num += w * (epa - off_adj.get(offense, 0.0))
                den += w
            new_def[team] = num / den if den else 0.0
        off_adj, def_adj = new_off, new_def
        _center(off_adj)
        _center(def_adj)

    out: Dict[str, Dict[str, float]] = {}
    for team in teams:
        n = off_w.get(team, 0.0)
        shrink = n / (n + SHRINK_PLAYS)
        out[team] = {
            "off_epa_adj": shrink * off_adj.get(team, 0.0),
            "def_epa_adj": shrink * def_adj.get(team, 0.0),
            "off_epa_raw": (off_sums[team] / off_w[team]) if off_w[team] else 0.0,
            "def_epa_raw": (def_sums[team] / def_w[team]) if def_w[team] else 0.0,
            "n_plays_weighted": n,
            "shrinkage": 1.0 - shrink,
            "uncertainty": 1.0 / ((n + SHRINK_PLAYS) ** 0.5),
        }
    return out


def week_snapshots(
    team_games: Sequence[Mapping[str, Any]],
    *,
    season: int,
    weeks: Sequence[int],
) -> list[dict[str, Any]]:
    """Entering-week snapshots. Week W uses only games with week < W."""
    by_week: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    all_teams: set[str] = set()
    for row in team_games:
        if int(row["season"]) != int(season):
            continue
        by_week[int(row["week"])].append(row)
        tid = str(row["team_id"])
        if not tid.startswith("fcs:"):
            all_teams.add(tid)

    out: list[dict[str, Any]] = []
    for week in weeks:
        prior = [r for w, rows in by_week.items() if w < int(week) for r in rows]
        max_included = max((int(r["week"]) for r in prior), default=0)
        adj = iterative_adjust(prior) if prior else {}
        avail = None
        for row in prior:
            a = row.get("available_at")
            if a and (avail is None or str(a) > str(avail)):
                avail = str(a)
        for team in sorted(all_teams):
            stats = adj.get(team) or {
                "off_epa_adj": 0.0,
                "def_epa_adj": 0.0,
                "off_epa_raw": 0.0,
                "def_epa_raw": 0.0,
                "n_plays_weighted": 0.0,
                "shrinkage": 1.0,
                "uncertainty": 1.0 / (SHRINK_PLAYS ** 0.5),
            }
            n_games = sum(1 for r in prior if str(r["team_id"]) == team)
            fcs_games = sum(
                1 for r in prior if str(r["team_id"]) == team and r.get("fcs_opponent")
            )
            row = {
                "season": int(season),
                "as_of_week": int(week),
                "feature_week": int(max_included),
                "max_week_included": int(max_included),
                "team_id": team,
                "n_games": n_games,
                "fcs_games": fcs_games,
                "available_at": avail,
                "era_tag": era_tag(season),
                "cold_start": n_games == 0,
                **{
                    k: round(float(v), 6) if isinstance(v, (int, float)) else v
                    for k, v in stats.items()
                },
            }
            assert_no_future_weeks([row], season=season, week=week)
            out.append(row)
    return out


def season_final_from_snapshots(
    snapshots: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Last as_of_week per team (full season, for next year's prior only)."""
    best: Dict[Tuple[int, str], Mapping[str, Any]] = {}
    for row in snapshots:
        key = (int(row["season"]), str(row["team_id"]))
        prev = best.get(key)
        if prev is None or int(row["as_of_week"]) >= int(prev["as_of_week"]):
            best[key] = row
    return [dict(v) for v in best.values()]


def load_pbp_season(season: int, *, prefer_hd: bool = True):
    import pandas as pd

    raw = pbp_raw_dir(prefer_hd=prefer_hd) / f"play_by_play_{int(season)}.parquet"
    core = clean_dir(prefer_hd=prefer_hd) / "pbp" / f"pbp_{int(season)}_core.parquet"
    src = raw if raw.exists() else core
    if not src.exists():
        raise FileNotFoundError(f"Missing PBP for {season}: {src}")
    cols = list(PBP_READ_COLS)
    try:
        import pyarrow.parquet as pq

        available = set(pq.ParquetFile(src).schema.names)
        cols = [c for c in cols if c in available]
    except Exception:  # noqa: BLE001
        pass
    return pd.read_parquet(src, columns=cols)


def load_games_kickoffs(*, prefer_hd: bool = True) -> Dict[str, str]:
    import pandas as pd

    path = clean_dir(prefer_hd=prefer_hd) / "games.parquet"
    if not path.exists():
        return {}
    g = pd.read_parquet(path, columns=["game_id", "kickoff"])
    return {
        str(r["game_id"]): str(r["kickoff"])
        for r in g.to_dict(orient="records")
        if r.get("kickoff")
    }


def build_efficiency(
    *,
    seasons: Sequence[int] = PBP_SEASONS,
    prefer_hd: bool = True,
) -> Dict[str, Any]:
    import pandas as pd

    known = known_engine_codes()
    kickoffs = load_games_kickoffs(prefer_hd=prefer_hd)
    clean = clean_dir(prefer_hd=prefer_hd) / "efficiency"
    clean.mkdir(parents=True, exist_ok=True)

    all_games: List[Dict[str, Any]] = []
    all_weeks: List[Dict[str, Any]] = []
    by_season: Dict[str, Any] = {}

    for season in seasons:
        try:
            df = load_pbp_season(int(season), prefer_hd=prefer_hd)
        except Exception as exc:  # noqa: BLE001
            by_season[str(season)] = {"status": "failed", "error": str(exc)[:200]}
            continue
        plays = df.to_dict(orient="records")
        games = aggregate_team_games(plays, known=known, kickoff_by_game=kickoffs)
        weeks = sorted({int(r["week"]) for r in games} | {1})
        as_of = sorted(set(weeks) | {max(weeks) + 1})
        snaps = week_snapshots(games, season=int(season), weeks=as_of)
        all_games.extend(games)
        all_weeks.extend(snaps)
        by_season[str(season)] = {
            "status": "ok",
            "plays": int(len(plays)),
            "team_games": len(games),
            "week_rows": len(snaps),
            "fbs_team_games": sum(
                1 for r in games if not str(r["team_id"]).startswith("fcs:")
            ),
        }

    if all_games:
        pd.DataFrame(all_games).to_parquet(
            clean / "team_game_efficiency.parquet", index=False
        )
    if all_weeks:
        pd.DataFrame(all_weeks).to_parquet(
            clean / "team_week_efficiency.parquet", index=False
        )
        finals = season_final_from_snapshots(all_weeks)
        pd.DataFrame(finals).to_parquet(
            clean / "team_season_efficiency.parquet", index=False
        )

    inventory = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "seasons": list(seasons),
        "team_games": len(all_games),
        "week_rows": len(all_weeks),
        "by_season": by_season,
        "garbage": GARBAGE_DEFAULTS,
        "shrink_plays": SHRINK_PLAYS,
        "adj_iters": ADJ_ITERS,
        "explosive": {"epa": EXPLOSIVE_EPA, "yards": EXPLOSIVE_YARDS},
        "leakage": "week W snapshot uses only same-season week < W",
        "dir": str(clean),
    }
    (clean / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    return inventory
