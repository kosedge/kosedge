#!/usr/bin/env python3
"""t4605u P1 W8 pipeline restore + RESEARCH slate (CERT_CANDIDATE=0).

Authority: DECISION_RYAN_t4605u sha256 e65b9c77… · COS_ORDER sha256 43d1702a…
Unblocks #642 f50f15a8 FAIL_CLOSED inputs where verified current sources exist.
Does not invent depth/injury/EPA. Does not use packaged W1 / 2025 prior as W8.
Does not call The Odds API. Does not write seal dests / #641 / F2.

Land path (SOP 4a017f22):
    /workspace/ops/nfl_enterprise_green_t4359u/research_runs/<run_id>/
Git-tracked:
    data/ops/nfl-model-forecast-emit-t4559u/research_runs/<run_id>/
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))

# User-site parquet deps (this VM).
_USER_SITE = Path.home() / ".local/lib/python3.12/site-packages"
if _USER_SITE.is_dir() and str(_USER_SITE) not in sys.path:
    sys.path.insert(0, str(_USER_SITE))

from src.services.nfl_injury_nowcast import compute_team_week_injury_severity
from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.efficiency_backbone import epa_to_strength_indices
from src.services.nfl_simulator import (
    DEFAULT_NFL_MODEL_VERSION,
    NflGameInputs,
    simulate_nfl_game,
)

CERT_CANDIDATE = 0
LABEL = "RESEARCH"
SCHEMA_VERSION = "nfl-model-forecast-artifact-v1"
EVAL_RECORD_PAPER_SHA8 = "f1fa86e7"
COS_ORDER_SHA8 = "43d1702a"
DECISION_SHA8 = "e65b9c77"
TICKET = "t4605u"
PR641_TIP = "385767a2"
EMIT_TIP_642 = "f50f15a8"
T08_TIP_643 = "4aaec8af"
PRIOR_COMPLETENESS_SHA = (
    "21b96525d4b59eb810801495723ad5c4cc84b7a64e4fc422bbeab8e8a85ace71"
)
SEASON = 2026
WEEK = 8
ET = ZoneInfo("America/New_York")

NFLVERSE = {
    "depth_charts_2026.parquet": (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        "depth_charts/depth_charts_2026.parquet"
    ),
    "injuries_2026.parquet": (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        "injuries/injuries_2026.parquet"
    ),
    "stats_team_week_2026.parquet": (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        "stats_team/stats_team_week_2026.parquet"
    ),
}

CANONICAL = (
    MS_SRC
    / "src/services/nfl_season_engine/data/nfl-canonical-schedule-2026.json"
)
SEAL_DEST_MARKERS = ("/seals/", "/seal/", "w8_first_seal", ".seal.json")
GAME_ID_RE = re.compile(
    r"^(?P<season>\d{4})-W(?P<week>\d{2})-(?P<away>[A-Z0-9]{2,4})@(?P<home>[A-Z0-9]{2,4})$"
)
DESIGNATIONS = {"out", "doubtful", "questionable"}
FILE_MODE = 0o444

TEAM_TO_NFLVERSE = {"LAR": "LA", "WSH": "WAS"}
NFLVERSE_TO_CANON = {"LA": "LAR"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _fmt_et(dt: datetime) -> str:
    return dt.astimezone(ET).replace(microsecond=0).isoformat()


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonicalize(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _git_head() -> str:
    out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", out):
        raise SystemExit("code_tip_sha unresolved")
    return out


def _assert_not_seal(path: Path) -> None:
    text = str(path.resolve()).replace("\\", "/").lower()
    for marker in SEAL_DEST_MARKERS:
        if marker in text:
            raise SystemExit(f"refuse seal dest write: {path}")


def _write_readonly(path: Path, blob: bytes) -> None:
    _assert_not_seal(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o644)
    path.write_bytes(blob)
    path.chmod(FILE_MODE)


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    blob = (json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n").encode(
        "utf-8"
    )
    _write_readonly(path, blob)
    return _sha256_bytes(blob)


def _nv(team: str) -> str:
    t = str(team or "").strip().upper()
    return TEAM_TO_NFLVERSE.get(t, t)


def _canon_team(team: str) -> str:
    t = str(team or "").strip().upper()
    return NFLVERSE_TO_CANON.get(t, t)


def _download(url: str, dest: Path, log: List[str]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "kosedge-research/t4564u"})
    with urllib.request.urlopen(req, timeout=90) as res:
        data = res.read()
    dest.write_bytes(data)
    log.append(f"downloaded {dest.name} bytes={len(data)} sha256={_sha256_bytes(data)}")


def _load_canonical_week() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    payload = json.loads(CANONICAL.read_text(encoding="utf-8"))
    games_in = payload.get("games") or []
    week: List[Dict[str, Any]] = []
    all_games: List[Dict[str, Any]] = []
    for raw in games_in:
        if not isinstance(raw, dict):
            continue
        if int(raw.get("season") or 0) != SEASON:
            continue
        row = {
            "game_id": str(raw.get("game_id") or "").strip(),
            "engine_game_id": str(raw.get("engine_game_id") or "").strip(),
            "season": SEASON,
            "week": int(raw.get("week") or 0),
            "home_team": str(raw.get("home_team_id") or "").upper(),
            "away_team": str(raw.get("away_team_id") or "").upper(),
            "kickoff_utc": raw.get("kickoff_utc"),
            "network": raw.get("network"),
            "venue": raw.get("venue"),
        }
        all_games.append(row)
        if row["week"] == WEEK:
            week.append(row)
    week.sort(key=lambda g: (str(g["kickoff_utc"] or ""), g["game_id"]))
    return week, all_games


def _rest_days(
    all_games: SequenceLike,
    *,
    team: str,
    kickoff: datetime,
) -> Tuple[Optional[float], str]:
    prev: Optional[datetime] = None
    for raw in all_games:
        if raw["home_team"] != team and raw["away_team"] != team:
            continue
        ko = _parse_utc(raw.get("kickoff_utc"))
        if ko is None or ko >= kickoff:
            continue
        if prev is None or ko > prev:
            prev = ko
    if prev is None:
        return None, "MISSING"
    days = (kickoff - prev).total_seconds() / 86400.0
    return round(days, 3), "schedule_kickoff_delta"


def _parse_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0)


# pandas imported lazily so --help / import of constants stays light.
SequenceLike = List[Dict[str, Any]]


def _build_current_strength(team_df: Any) -> Dict[str, Dict[str, Any]]:
    import pandas as pd

    df = team_df.copy()
    df["team_n"] = df["team"].map(lambda t: _nv(str(t)))
    # Pair each game to opponent offensive EPA as defense-allowed.
    off = {}
    for row in df.itertuples(index=False):
        plays = float(row.attempts or 0) + float(row.sacks_suffered or 0) + float(
            row.carries or 0
        )
        off_epa = float(row.passing_epa or 0) + float(row.rushing_epa or 0)
        off[(str(row.game_id), str(row.team))] = {
            "plays": plays,
            "epa": off_epa,
            "pass_epa": float(row.passing_epa or 0),
            "run_epa": float(row.rushing_epa or 0),
            "week": int(row.week),
            "opp": str(row.opponent_team),
        }
    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for (gid, team), own in off.items():
        opp_key = (gid, own["opp"])
        opp = off.get(opp_key)
        if opp is None:
            continue
        rec = {
            "week": own["week"],
            "off_plays": own["plays"],
            "off_epa": own["epa"],
            "pass_epa": own["pass_epa"],
            "run_epa": own["run_epa"],
            "def_plays": opp["plays"],
            "def_epa_allowed": opp["epa"],
        }
        by_team.setdefault(_nv(team), []).append(rec)

    out: Dict[str, Dict[str, Any]] = {}
    for team, recs in by_team.items():
        recs = sorted(recs, key=lambda r: r["week"])
        off_plays = sum(r["off_plays"] for r in recs)
        def_plays = sum(r["def_plays"] for r in recs)
        off_epa = sum(r["off_epa"] for r in recs)
        def_epa = sum(r["def_epa_allowed"] for r in recs)
        off_pp = off_epa / off_plays if off_plays else None
        def_pp = def_epa / def_plays if def_plays else None
        if off_pp is None or def_pp is None:
            continue
        idx = epa_to_strength_indices(off_epa=off_pp, def_epa_allowed=def_pp)
        out[team] = {
            "offense_index": idx["offense_index"],
            "defense_index": idx["defense_index"],
            "off_epa_per_play": round(off_pp, 6),
            "def_epa_allowed_per_play": round(def_pp, 6),
            "games": len(recs),
            "weeks": [r["week"] for r in recs],
            "off_plays": int(off_plays),
            "def_plays": int(def_plays),
            "source": "nflverse_stats_team_week_2026_w1_w7_play_weighted",
            "conversion": "efficiency_backbone.epa_to_strength_indices",
        }
    return out


def _injury_impacts(inj_df: Any) -> Dict[str, Dict[str, Any]]:
    import pandas as pd

    df = inj_df.copy()
    df["team_n"] = df["team"].map(lambda t: _nv(str(t)))
    latest_week = {t: int(g["week"].max()) for t, g in df.groupby("team_n")}
    out: Dict[str, Dict[str, Any]] = {}
    for team, as_of_week in latest_week.items():
        rows = df[(df["team_n"] == team) & (df["week"] == as_of_week)]
        designated: List[Dict[str, Any]] = []
        for r in rows.itertuples(index=False):
            status = str(getattr(r, "report_status", "") or "").strip()
            if status.lower() not in DESIGNATIONS:
                continue
            designated.append(
                {
                    "team": team,
                    "week": as_of_week,
                    "player_name": getattr(r, "full_name", None),
                    "position": getattr(r, "position", None),
                    "report_status": status,
                    "practice_status": getattr(r, "practice_status", None),
                    "injury": getattr(r, "report_primary_injury", None),
                }
            )
        sev = compute_team_week_injury_severity(designated)
        out[team] = {
            "as_of_week": as_of_week,
            "designated_count": len(designated),
            "report_row_count": int(len(rows)),
            "offense_impact": sev["offense_impact"] if designated else None,
            "defense_impact": sev["defense_impact"] if designated else None,
            "impact_score": sev["impact_score"] if designated else None,
            "source": "nflverse_injuries_2026",
            "filter": "report_status in {Out,Doubtful,Questionable} only",
            "w8_official_report": "MISSING",
            "note": (
                "Latest official weekly report is week "
                f"{as_of_week}. W8 Wednesday report not present. "
                "Practice-only / blank report_status rows excluded "
                "(not treated as healthy fill)."
            ),
            "designated_players": [
                {
                    "player": d["player_name"],
                    "position": d["position"],
                    "report_status": d["report_status"],
                    "injury": d["injury"],
                }
                for d in designated
            ],
        }
    return out


def _depth_meta(depth_df: Any) -> Dict[str, Any]:
    import pandas as pd

    s = pd.to_datetime(depth_df["dt"], utc=True, errors="coerce")
    latest = s.max()
    snap = depth_df.loc[s == latest]
    return {
        "source": "nflverse_depth_charts_2026",
        "as_of": _fmt_utc(latest.to_pydatetime()),
        "snapshot_rows": int(len(snap)),
        "teams": int(snap["team"].nunique()),
        "used_for": "provenance_only_not_player_box_volume",
        "not_used": "packaged nfl_depth_chart_2026_w1.json",
    }


def _simulate_one(
    game: Mapping[str, Any],
    *,
    strength: Mapping[str, Mapping[str, Any]],
    injuries: Mapping[str, Mapping[str, Any]],
    rest: Tuple[Optional[float], str, Optional[float], str],
    seed: int,
) -> Dict[str, Any]:
    home = game["home_team"]
    away = game["away_team"]
    hs = strength.get(_nv(home))
    aws = strength.get(_nv(away))
    if not hs or not aws:
        raise SystemExit(f"MISSING current strength for {away}@{home}")
    hi = injuries.get(_nv(home), {})
    ai = injuries.get(_nv(away), {})
    rest_h, rest_h_src, rest_a, rest_a_src = rest
    # Engine requires a rest float; only pass schedule-derived rest.
    # If MISSING, skip the 7.0 dataclass default by using None? NflGameInputs
    # defaults to 7.0. We pass the computed value or leave default and flag.
    inputs = NflGameInputs(
        game_id=game["game_id"],
        home_team=home,
        away_team=away,
        offense_index_home=float(hs["offense_index"]),
        offense_index_away=float(aws["offense_index"]),
        defense_index_home=float(hs["defense_index"]),
        defense_index_away=float(aws["defense_index"]),
        rest_days_home=float(rest_h) if rest_h is not None else 7.0,
        rest_days_away=float(rest_a) if rest_a is not None else 7.0,
        matchup_season=SEASON,
        matchup_week=WEEK,
        matchup_game_id=game["game_id"],
        matchup_home_team=home,
        matchup_away_team=away,
        injury_nowcast_impact_home=hi.get("impact_score"),
        injury_nowcast_impact_away=ai.get("impact_score"),
        injury_nowcast_source=(
            f"{hi.get('source')}|week={hi.get('as_of_week')}"
            if hi.get("impact_score") is not None or ai.get("impact_score") is not None
            else None
        ),
        home_off_epa_5g=hs.get("off_epa_per_play"),
        away_off_epa_5g=aws.get("off_epa_per_play"),
        home_def_epa_allowed_5g=hs.get("def_epa_allowed_per_play"),
        away_def_epa_allowed_5g=aws.get("def_epa_allowed_per_play"),
        weather_available=False,
        travel_available=False,
    )
    # No market_spread_home / market_total — no Odds, no blend.
    result = simulate_nfl_game(
        inputs,
        simulations=4000,
        seed=seed,
        model_version=DEFAULT_NFL_MODEL_VERSION,
        apply_linear_totals_calibration=True,
    )
    markets = result["markets"]
    missing = []
    if rest_h is None:
        missing.append("rest_days_home")
    if rest_a is None:
        missing.append("rest_days_away")
    missing.extend(
        [
            "market_spread",
            "market_total",
            "market_ml",
            "weather",
            "kav_5g_warehouse",
            "w8_official_injury_report",
            "nfl_dp_team_rolling_features_weekly",
        ]
    )
    if hi.get("as_of_week") != WEEK:
        missing.append("injury_as_of_week8")
    if ai.get("as_of_week") != WEEK:
        missing.append("injury_as_of_week8_away")
    return {
        "engine": result,
        "missing": sorted(set(missing)),
        "rest": {
            "home": rest_h,
            "home_source": rest_h_src,
            "away": rest_a,
            "away_source": rest_a_src,
        },
        "injury_home": hi,
        "injury_away": ai,
        "strength_home": hs,
        "strength_away": aws,
        "markets": markets,
    }


def _g18_artifact(
    *,
    game: Mapping[str, Any],
    sim: Mapping[str, Any],
    forecast_ts: datetime,
    latest_input: datetime,
    code_tip: str,
    config_sha: str,
    fingerprints: Mapping[str, str],
) -> Dict[str, Any]:
    gid = game["game_id"]
    parsed = GAME_ID_RE.match(gid)
    if not parsed:
        raise SystemExit(f"G1 game_id format fail: {gid}")
    if parsed.group("away") != game["away_team"] or parsed.group("home") != game["home_team"]:
        raise SystemExit(f"G1 home/away vs game_id fail: {gid}")
    kickoff = _parse_utc(game["kickoff_utc"])
    if kickoff is None:
        raise SystemExit(f"G1 kickoff missing: {gid}")
    lead = int((kickoff - forecast_ts).total_seconds())
    if lead <= 0:
        raise SystemExit(f"G2 not pre-kickoff: {gid} lead={lead}")
    if latest_input > forecast_ts:
        raise SystemExit("G2 latest_input_as_of after forecast")
    m = sim["markets"]
    spread = float(m["spread_home"])
    total = float(m["total_mean"])
    home_wp = float(m["home_win_prob"])
    away_wp = float(m["away_win_prob"])
    src = "model_unblended_research_no_market_line"
    return {
        "schema_version": SCHEMA_VERSION,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "purpose": "research_eng_only",
        "sport": "nfl",
        "ticket": TICKET,
        "cos_order_sha8": COS_ORDER_SHA8,
        "decision_sha8": DECISION_SHA8,
        "eval_record_paper_sha8": EVAL_RECORD_PAPER_SHA8,
        "forecast_ts_utc": _fmt_utc(forecast_ts),
        "emitted_at_utc": _fmt_utc(forecast_ts),
        "emitted_at_et": _fmt_et(forecast_ts),
        "game_id": gid,
        "home_team": game["home_team"],
        "away_team": game["away_team"],
        "kickoff_utc": _fmt_utc(kickoff),
        "lead_seconds": lead,
        "pre_kickoff": True,
        "latest_input_as_of": _fmt_utc(latest_input),
        "code_tip_sha": code_tip,
        "config_sha256": config_sha,
        "model": {
            "identity": "nfl-simulator+efficiency_backbone",
            "version": DEFAULT_NFL_MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "framework": "nfl-handicap-core-v3.1",
        },
        "orientation": {
            "spread": "home",
            "sign_convention": "home_negative_favored",
        },
        "markets": {
            "spread": {
                "prediction": spread,
                "ref_line": spread,
                "ref_line_source": src,
                "orientation": "home",
                "sign_convention": "home_negative_favored",
                "market_book_line": "MISSING",
            },
            "total": {
                "prediction": total,
                "ref_line": total,
                "ref_line_source": src,
                "orientation": "game",
                "market_book_line": "MISSING",
            },
            "moneyline": {
                "prediction": home_wp,
                "ref_line": home_wp,
                "ref_line_source": src,
                "orientation": "home",
                "away_win_prob": away_wp,
                "home_ml": m.get("fair_home_ml"),
                "away_ml": m.get("fair_away_ml"),
                "market_book_line": "MISSING",
            },
        },
        "input_provenance": {
            "fingerprints": dict(fingerprints),
            "missing_inputs": sim["missing"],
            "injury_overlay": "week7_or_latest_official_designations_only",
            "depth_role": "provenance_only",
            "odds_api": False,
            "pr641_tip_untouched": PR641_TIP,
        },
        "grades": {"ats": None, "ou": None, "su": None},
        "close_anchor": {
            "status": "reserved_empty",
            "close_spread_home": None,
            "close_total": None,
            "close_ml_home": None,
            "close_captured_at": None,
            "close_source": None,
        },
        "seal_binding": {"status": "unbound", "hook": "game_id+forecast_ts_utc+record_sha256"},
    }


def _materialize_current_packs(
    *,
    dest: Path,
    depth_df: Any,
    inj_df: Any,
    strength: Mapping[str, Mapping[str, Any]],
    depth_meta: Mapping[str, Any],
    fingerprints: Mapping[str, str],
) -> Dict[str, Path]:
    """Write verified current W8 research packs. Does not overwrite W1 production."""
    dest.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    s = pd.to_datetime(depth_df["dt"], utc=True, errors="coerce")
    latest = s.max()
    snap = depth_df.loc[s == latest].copy()
    skill = {"QB", "RB", "WR", "TE"}
    defense = {"EDGE", "DE", "DT", "DL", "LB", "ILB", "OLB", "CB", "S", "FS", "SS", "NB", "DB"}
    rows: List[Dict[str, Any]] = []
    for rec in snap.to_dict("records"):
        abb = str(rec.get("pos_abb") or "").upper()
        if abb not in skill and abb not in defense:
            continue
        team = str(rec.get("team") or "").upper()
        team = {"LA": "LA", "WAS": "WAS"}.get(team, team)
        rows.append(
            {
                "team": team,
                "position": abb,
                "depth_order": int(rec.get("pos_rank") or rec.get("pos_slot") or 0),
                "player_id": rec.get("gsis_id"),
                "player_name": rec.get("player_name"),
                "pos_name": rec.get("pos_name"),
                "pos_grp": rec.get("pos_grp"),
            }
        )
    depth_as_of = _fmt_utc(latest.to_pydatetime())
    depth_pack = {
        "season": SEASON,
        "week": WEEK,
        "source": "nflverse_depth_charts_2026_latest_snapshot",
        "upstream": "nflverse/nflverse-data depth_charts release",
        "upstream_url": NFLVERSE["depth_charts_2026.parquet"],
        "as_of": depth_as_of[:10],
        "as_of_timestamp": depth_as_of,
        "snapshot_id": f"nfl-depth-2026-w8-{latest.strftime('%Y%m%dT%H%M%SZ')}",
        "positions": sorted(skill),
        "defense_positions": sorted(defense),
        "team_count": int(snap["team"].nunique()),
        "row_count": len(rows),
        "notes": [
            "RESEARCH current snapshot — not packaged nfl_depth_chart_2026_w1.json.",
            "Rows copied from latest nflverse dt; no invented players.",
            "Used as current W8 depth SoT for completeness; team-sim volume is EPA-based.",
        ],
        "injury_paths": [],
        "parquet_sha256": fingerprints.get("depth_parquet"),
        "rows": rows,
    }

    latest_week = int(inj_df["week"].max())
    inj_week = inj_df[inj_df["week"] == latest_week]
    designated: List[Dict[str, Any]] = []
    for rec in inj_week.to_dict("records"):
        status = str(rec.get("report_status") or "").strip()
        if status.lower() not in DESIGNATIONS:
            continue
        designated.append(
            {
                "team": rec.get("team"),
                "week": latest_week,
                "player_name": rec.get("full_name"),
                "player_id": rec.get("gsis_id"),
                "position": rec.get("position"),
                "report_status": status,
                "practice_status": rec.get("practice_status"),
                "injury": rec.get("report_primary_injury"),
            }
        )
    injury_pack = {
        "season": SEASON,
        "week": latest_week,
        "source": "nflverse_injuries_2026",
        "upstream_url": NFLVERSE["injuries_2026.parquet"],
        "as_of": depth_as_of,
        "filter": "report_status in {Out,Doubtful,Questionable} only",
        "designated_count": len(designated),
        "report_row_count": int(len(inj_week)),
        "w8_official_report": "PRESENT" if latest_week >= WEEK else "MISSING",
        "parquet_sha256": fingerprints.get("injuries_parquet"),
        "rows": designated,
    }
    injury_path = dest / f"nfl_injuries_2026_w{latest_week}_designated.json"
    depth_pack["injury_paths"] = [str(injury_path)]

    teams = {}
    for team, rec in strength.items():
        teams[team] = {
            "offense_index": rec.get("offense_index"),
            "defense_index": rec.get("defense_index"),
            "off_epa_per_play": rec.get("off_epa_per_play"),
            "def_epa_allowed_per_play": rec.get("def_epa_allowed_per_play"),
            "games": rec.get("games"),
            "weeks": rec.get("weeks"),
            "off_plays": rec.get("off_plays"),
            "def_plays": rec.get("def_plays"),
        }
    eff_pack = {
        "season": SEASON,
        "prior_season": None,
        "week_through": int(max((w for rec in strength.values() for w in rec.get("weeks") or [0]), default=0)),
        "source": "nflverse_stats_team_week_2026",
        "as_of": depth_as_of,
        "method": "play_weighted_w1_w7_passing_plus_rushing_epa",
        "conversion": "efficiency_backbone.epa_to_strength_indices",
        "team_count": len(teams),
        "parquet_sha256": fingerprints.get("team_week_parquet"),
        "notes": "Current-season 2026 W1–W7. Not packaged 2025 prior as_of 2026-08-08.",
        "teams": teams,
    }

    depth_path = dest / "nfl_depth_chart_2026_w8.json"
    eff_path = dest / "nfl_team_efficiency_backbone_2026_inseason_w7.json"
    depth_path.write_text(json.dumps(depth_pack, indent=2, sort_keys=True) + "\n")
    injury_path.write_text(json.dumps(injury_pack, indent=2, sort_keys=True) + "\n")
    eff_path.write_text(json.dumps(eff_pack, indent=2, sort_keys=True) + "\n")
    return {"depth": depth_path, "injury": injury_path, "efficiency": eff_path}


def _run_t08() -> Dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/test_nfl_week_cap_bind.py",
        "-k",
        "not untyped_null_week_bind",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(MS_SRC),
        env=env,
        text=True,
        capture_output=True,
    )
    return {
        "cmd": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-2000:],
        "stderr": (proc.stderr or "")[-1000:],
        "note": (
            "T-08 unit predicates (3 tests) do not need live Postgres. "
            "test_untyped_null_week_bind_raises_ambiguous_parameter skipped "
            "here (no local Postgres). #643 tip 4aaec8af: slate NOT blocked by T-08."
        ),
        "t08_tip": T08_TIP_643,
        "blocks_slate": False,
    }


def main() -> int:
    forecast_ts = _utc_now()
    run_id = f"nfl-w8-2026-{TICKET}-restore-{forecast_ts.strftime('%Y%m%dT%H%M%SZ')}"
    box_root = Path("/workspace/ops/nfl_enterprise_green_t4359u/research_runs") / run_id
    repo_root = (
        ROOT
        / "data/ops/nfl-model-forecast-emit-t4559u/research_runs"
        / run_id
    )
    cache = Path("/tmp/nflverse-w8")
    cache.mkdir(parents=True, exist_ok=True)
    log: List[str] = [
        f"run_id={run_id}",
        f"forecast_ts_utc={_fmt_utc(forecast_ts)}",
        f"forecast_ts_et={_fmt_et(forecast_ts)}",
        f"cert_candidate={CERT_CANDIDATE}",
        f"label={LABEL}",
        "odds_api=false",
        f"pr641_frozen={PR641_TIP}",
        f"emit_tip_642_fail_closed={EMIT_TIP_642}",
    ]

    code_tip = _git_head()
    log.append(f"code_tip_sha={code_tip}")

    for name, url in NFLVERSE.items():
        dest = cache / name
        # t4605u restore: always refresh public nflverse (do not reuse stale cache).
        _download(url, dest, log)

    import pandas as pd

    depth_df = pd.read_parquet(cache / "depth_charts_2026.parquet")
    inj_df = pd.read_parquet(cache / "injuries_2026.parquet")
    team_df = pd.read_parquet(cache / "stats_team_week_2026.parquet")
    depth_meta = _depth_meta(depth_df)
    strength = _build_current_strength(team_df)
    injuries = _injury_impacts(inj_df)
    week_games, all_games = _load_canonical_week()
    if len(week_games) != 14:
        raise SystemExit(f"expected 14 W8 games, got {len(week_games)}")

    # Current-input gates (do not use W1 pack).
    depth_dt = _parse_utc(depth_meta["as_of"])
    if depth_dt is None or depth_dt.date().isoformat() < "2026-10-20":
        raise SystemExit(f"depth snapshot not current W8 window: {depth_meta}")
    if int(inj_df["week"].max()) < 7:
        raise SystemExit("injuries do not reach week 7")
    if int(team_df["week"].max()) < 7:
        raise SystemExit("team-week EPA does not reach week 7")
    if len(strength) < 32:
        raise SystemExit(f"strength teams {len(strength)} < 32")

    fingerprints = {
        "depth_parquet": _sha256_file(cache / "depth_charts_2026.parquet"),
        "injuries_parquet": _sha256_file(cache / "injuries_2026.parquet"),
        "team_week_parquet": _sha256_file(cache / "stats_team_week_2026.parquet"),
        "canonical_schedule": _sha256_file(CANONICAL),
    }
    config = {
        "ticket": TICKET,
        "season": SEASON,
        "week": WEEK,
        "simulations": 4000,
        "apply_linear_totals_calibration": True,
        "apply_market_blend": False,
        "injury_filter": sorted(DESIGNATIONS),
        "strength_source": "nflverse_stats_team_week_2026_w1_w7_play_weighted",
        "odds_api": False,
    }
    config_sha = _sha256_bytes(_canonicalize(config).encode("utf-8"))
    latest_input = depth_dt
    log.append(f"latest_input_as_of={_fmt_utc(latest_input)}")
    log.append(f"depth_as_of={depth_meta['as_of']} teams={depth_meta['teams']}")
    log.append(f"strength_teams={len(strength)}")
    log.append(f"injury_teams={len(injuries)}")

    t08 = _run_t08()
    log.append(f"t08_returncode={t08['returncode']} blocks_slate={t08['blocks_slate']}")

    rows: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []
    missing_doc: Dict[str, Any] = {
        "slate": [
            "Odds API market lines (forbidden this ticket)",
            "W8 official Wednesday injury report (latest official is week 7)",
            "DATABASE_URL / nfl_dp_* warehouse on this VM",
            "Railway /nfl HTTP (production OpenAPI has 0 NFL paths)",
            "weather / KAV warehouse 5g",
        ]
    }

    for i, game in enumerate(week_games):
        if not GAME_ID_RE.match(game["game_id"]):
            raise SystemExit(f"bad game_id {game['game_id']}")
        kickoff = _parse_utc(game["kickoff_utc"])
        if kickoff is None:
            raise SystemExit(f"kickoff MISSING {game['game_id']}")
        rh, rhs = _rest_days(all_games, team=game["home_team"], kickoff=kickoff)
        ra, ras = _rest_days(all_games, team=game["away_team"], kickoff=kickoff)
        seed = int(_sha256_bytes(f"{run_id}:{game['game_id']}".encode())[:8], 16) % (2**31)
        sim = _simulate_one(
            game,
            strength=strength,
            injuries=injuries,
            rest=(rh, rhs, ra, ras),
            seed=seed,
        )
        # Deterministic check: second draw.
        sim2 = _simulate_one(
            game,
            strength=strength,
            injuries=injuries,
            rest=(rh, rhs, ra, ras),
            seed=seed,
        )
        det_ok = (
            sim["markets"]["spread_home"] == sim2["markets"]["spread_home"]
            and sim["markets"]["total_mean"] == sim2["markets"]["total_mean"]
            and sim["markets"]["home_win_prob"] == sim2["markets"]["home_win_prob"]
        )
        if not det_ok:
            raise SystemExit(f"deterministic fail {game['game_id']}")
        art = _g18_artifact(
            game=game,
            sim=sim,
            forecast_ts=forecast_ts,
            latest_input=latest_input,
            code_tip=code_tip,
            config_sha=config_sha,
            fingerprints=fingerprints,
        )
        rec_sha = _sha256_bytes(_canonicalize(art).encode("utf-8"))
        art["record_sha256"] = rec_sha
        artifacts.append(art)
        missing_doc[game["game_id"]] = sim["missing"]
        hi = sim["injury_home"]
        ai = sim["injury_away"]
        rows.append(
            {
                "game_id": game["game_id"],
                "away_team": game["away_team"],
                "home_team": game["home_team"],
                "kickoff_utc": game["kickoff_utc"],
                "spread_home": sim["markets"]["spread_home"],
                "total": sim["markets"]["total_mean"],
                "home_win_prob": sim["markets"]["home_win_prob"],
                "away_win_prob": sim["markets"]["away_win_prob"],
                "fair_home_ml": sim["markets"].get("fair_home_ml"),
                "fair_away_ml": sim["markets"].get("fair_away_ml"),
                "run_id": run_id,
                "forecast_ts_utc": _fmt_utc(forecast_ts),
                "emitted_at_et": _fmt_et(forecast_ts),
                "record_sha256": rec_sha,
                "deterministic_ok": det_ok,
                "injury_home_as_of_week": hi.get("as_of_week"),
                "injury_away_as_of_week": ai.get("as_of_week"),
                "injury_home_designated": hi.get("designated_count"),
                "injury_away_designated": ai.get("designated_count"),
                "strength_home_off": sim["strength_home"]["offense_index"],
                "strength_away_off": sim["strength_away"]["offense_index"],
                "missing_inputs": "|".join(sim["missing"]),
                "cert_candidate": CERT_CANDIDATE,
                "label": LABEL,
            }
        )
        log.append(
            f"{game['game_id']} spread={sim['markets']['spread_home']} "
            f"total={sim['markets']['total_mean']} "
            f"home_wp={sim['markets']['home_win_prob']} det={det_ok}"
        )

    input_as_of = {
        "depth": depth_meta,
        "injuries": {
            "source": "nflverse_injuries_2026",
            "max_week": int(inj_df["week"].max()),
            "week7_rows": int((inj_df["week"] == 7).sum()),
            "w8_official_report": "MISSING",
        },
        "efficiency": {
            "source": "nflverse_stats_team_week_2026",
            "max_week": int(team_df["week"].max()),
            "teams": len(strength),
            "conversion": "epa_to_strength_indices on play-weighted W1–W7",
            "warehouse_rolling": "MISSING",
        },
        "schedule": {
            "source": str(CANONICAL.relative_to(ROOT)),
            "week8_games": len(week_games),
        },
        "database_url_present": bool((os.environ.get("DATABASE_URL") or "").strip()),
        "model_service_nfl_routes": 0,
        "packaged_w1_depth_used": False,
        "silent_healthy": False,
    }
    manifest = {
        "run_id": run_id,
        "ticket": TICKET,
        "cert_candidate": CERT_CANDIDATE,
        "label": LABEL,
        "forecast_ts_utc": _fmt_utc(forecast_ts),
        "emitted_at_et": _fmt_et(forecast_ts),
        "code_tip_sha": code_tip,
        "config_sha256": config_sha,
        "sources": {k: {"url": v, "sha256": fingerprints[alias]} for k, v, alias in (
            ("depth_charts_2026.parquet", NFLVERSE["depth_charts_2026.parquet"], "depth_parquet"),
            ("injuries_2026.parquet", NFLVERSE["injuries_2026.parquet"], "injuries_parquet"),
            ("stats_team_week_2026.parquet", NFLVERSE["stats_team_week_2026.parquet"], "team_week_parquet"),
        )},
        "fingerprints": fingerprints,
        "games": [g["game_id"] for g in week_games],
        "hard_stops": {
            "odds_api": False,
            "pr641_tip": PR641_TIP,
            "seals": False,
            "merge_deploy": False,
            "coming_soon": True,
            "nfl_nogo": True,
        },
    }
    pack_dir = (
        ROOT / "data/ops/nfl-t4605u-w8-pipeline-restore/current_inputs"
    )
    packs = _materialize_current_packs(
        dest=pack_dir,
        depth_df=depth_df,
        inj_df=inj_df,
        strength=strength,
        depth_meta=depth_meta,
        fingerprints=fingerprints,
    )
    sys.path.insert(0, str(ROOT / "scripts" / "nfl"))
    from audit_w8_input_completeness_t4605u import audit_week_inputs

    completeness = audit_week_inputs(
        season=SEASON,
        week=WEEK,
        depth_path=packs["depth"],
        injury_paths=[packs["injury"]],
        efficiency_path=packs["efficiency"],
        slate_game_ids=[g["game_id"] for g in week_games],
        now_utc=forecast_ts,
    )
    log.append(
        "completeness_sha256="
        f"{completeness['input_completeness_sha256']} "
        f"ok={completeness['ok']} "
        f"passed={completeness['passed']} "
        f"failing={completeness['failing_components']}"
    )
    manifest["completeness_sha256"] = completeness["input_completeness_sha256"]
    manifest["blockers_closed"] = completeness["passed"]
    manifest["blockers_remaining"] = completeness["failing_components"]
    manifest["current_input_packs"] = {
        key: str(path.relative_to(ROOT)) for key, path in packs.items()
    }
    manifest["ticket"] = TICKET
    manifest["cos_order_sha8"] = COS_ORDER_SHA8
    manifest["decision_sha8"] = DECISION_SHA8

    slate = {
        "run_id": run_id,
        "season": SEASON,
        "week": WEEK,
        "cert_candidate": CERT_CANDIDATE,
        "label": LABEL,
        "forecast_ts_utc": _fmt_utc(forecast_ts),
        "emitted_at_et": _fmt_et(forecast_ts),
        "n_games": len(rows),
        "deterministic_all": all(r["deterministic_ok"] for r in rows),
        "games": rows,
        "t08": {"blocks_slate": False, "tip": T08_TIP_643, "returncode": t08["returncode"]},
    }

    success = {
        "ticket": TICKET,
        "run_id": run_id,
        "outcome": "complete_internal_w8_table",
        "n_games": len(rows),
        "box_path": str(box_root),
        "repo_path": str(repo_root.relative_to(ROOT)),
        "code_tip_sha": code_tip,
        "code_tip_sha8": code_tip[:8],
        "cert_candidate": CERT_CANDIDATE,
        "blocker": None,
        "coverage_produced": [r["game_id"] for r in rows],
        "coverage_missing_forecast": [],
        "deterministic_check": "PASS (per-game identical re-sim, same seed)",
        "completeness_sha256": completeness["input_completeness_sha256"],
        "completeness_sha8": completeness["input_completeness_sha256"][:8],
        "blockers_closed": completeness["passed"],
        "blockers_remaining": completeness["failing_components"],
        "notes": [
            "t4605u restore vs #642 f50f15a8 / 21b96525.",
            "Depth: current nflverse W8 snapshot (not packaged W1 2026-08-13).",
            "Injury: official latest week designated only; silent healthy forbidden.",
            "EPA: in-season 2026 W1–W7 play-weighted via epa_to_strength_indices.",
            "DATABASE_URL warehouse: exact access blocker if unset.",
            "Market lines MISSING (no Odds). ref_line is model research line.",
        ],
    }

    repro = """# t4605u W8 pipeline restore — repro

CERT_CANDIDATE=0. NFL NO-GO. No Odds. No #641 / F2.

```bash
cd /workspace
python3 scripts/nfl/run_w8_research_forecast_t4564u.py
```

Requires network to nflverse GitHub releases (public). Does not read DATABASE_URL.
Does not call The Odds API. Writes `/workspace/ops/nfl_enterprise_green_t4359u/research_runs/<run_id>/` (0444 + SHA256SUMS).
"""

    payloads = {
        "input_manifest.json": manifest,
        "input_as_of.json": input_as_of,
        "MISSING.json": missing_doc,
        "completeness.json": completeness,
        "slate.json": slate,
        "t08.json": t08,
        "SUCCESS_REPORT.md": None,
        "REPRO.md": None,
    }

    def _deposit(dest: Path) -> Dict[str, str]:
        dest.mkdir(parents=True, exist_ok=True)
        _assert_not_seal(dest)
        sums: Dict[str, str] = {}
        fdir = dest / "forecasts"
        for art in artifacts:
            p = fdir / f"{art['game_id']}.json"
            sha = _write_json(p, art)
            sums[str(p.relative_to(dest))] = sha
            sidecar = p.with_name(p.name + ".record_sha256")
            _write_readonly(sidecar, (art["record_sha256"] + "\n").encode())
            sums[str(sidecar.relative_to(dest))] = _sha256_file(sidecar)
        for name, payload in payloads.items():
            if name.endswith(".md"):
                continue
            p = dest / name
            sums[name] = _write_json(p, payload)  # type: ignore[arg-type]
        cdir = dest / "current_inputs"
        for path in packs.values():
            blob = path.read_bytes()
            out = cdir / path.name
            _write_readonly(out, blob)
            sums[str(out.relative_to(dest))] = _sha256_bytes(blob)
        table_path = dest / "slate_table.csv"
        buf = []
        if rows:
            fieldnames = list(rows[0].keys())
            from io import StringIO

            sio = StringIO()
            w = csv.DictWriter(sio, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
            blob = sio.getvalue().encode("utf-8")
            _write_readonly(table_path, blob)
            sums["slate_table.csv"] = _sha256_bytes(blob)
        report = (
            f"# t4605u W8 pipeline restore\n\n"
            f"run_id: `{run_id}`\n\n"
            f"tip SHA: `{code_tip}` (sha8 `{code_tip[:8]}`)\n\n"
            f"completeness sha256: `{completeness['input_completeness_sha256']}` "
            f"(sha8 `{completeness['input_completeness_sha256'][:8]}`)\n\n"
            f"CLOSED: {completeness['passed']}\n\n"
            f"REMAINING: {completeness['failing_components']}\n\n"
            f"path: `{dest}`\n\n"
            f"games: {len(rows)} / 14 produced; forecast MISSING: none\n\n"
            f"deterministic: PASS\n"
        )
        _write_readonly(dest / "SUCCESS_REPORT.md", report.encode())
        sums["SUCCESS_REPORT.md"] = _sha256_file(dest / "SUCCESS_REPORT.md")
        _write_readonly(dest / "REPRO.md", repro.encode())
        sums["REPRO.md"] = _sha256_file(dest / "REPRO.md")
        redacted = "\n".join(log) + "\n"
        # Redact any accidental secrets
        redacted = re.sub(r"(api[_-]?key=)\S+", r"\1REDACTED", redacted, flags=re.I)
        redacted = re.sub(r"(postgres(ql)?://)\S+", r"\1REDACTED", redacted, flags=re.I)
        _write_readonly(dest / "run.log", redacted.encode())
        sums["run.log"] = _sha256_file(dest / "run.log")
        lines = [f"{sha}  {name}" for name, sha in sorted(sums.items())]
        _write_readonly(dest / "SHA256SUMS", ("\n".join(lines) + "\n").encode())
        return sums

    box_sums = _deposit(box_root)
    repo_sums = _deposit(repo_root)
    print(json.dumps(
        {
            "run_id": run_id,
            "box_path": str(box_root),
            "repo_path": str(repo_root),
            "code_tip_sha8": code_tip[:8],
            "n_games": len(rows),
            "sha256sums_head": list(box_sums.items())[:4],
            "t08_returncode": t08["returncode"],
        },
        indent=2,
    ))
    return 0 if t08["returncode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
