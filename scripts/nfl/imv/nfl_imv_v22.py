#!/usr/bin/env python3
"""IMV v2.2 (f9b25e81). Do not run the builder or W7 until IMV code-checks.

Gating before any Mac run:
  X-1 expected store sha from OUTSIDE the store (no file-pin fallback)
  X-8 builder network deny + EPERM probe
  X-9 builder refuses existing OUT; stamps helper sha

Model evidence:
  X-2 §5.3 strength-index rebuild (lag-only, pinned BASE backbone)
  X-3 parity vs prod: many keys, real fixture, FAIL on value mismatch
  X-4 per-row injury record (no hardcoded defaulted_injury=false)
  X-5 enforce cap pair pbp == game-1; W7 refused
  X-6 5g = last 5 played REG games before kickoff (bye/postseason skipped)
  X-7 lag-only test + run label BLOCKED_NO_MODEL_EXECUTION / RETROSPECTIVE /
      PROSPECTIVE-RESEARCH
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import nfl_imv_v21 as v21

RULING = "f9b25e81"
SCRIPT_ID = "nfl-imv-v2.2"
CERT_CANDIDATE = v21.CERT_CANDIDATE
ALLOWED_GAME_WEEK_CAPS = frozenset({4, 5, 6, 8})  # W4–W6 retro, W8; never 7
POSTSEASON_TYPES = frozenset(
    {"POST", "POSTSEASON", "WC", "DIV", "CON", "SB", "WILDCARD", "DIVISIONAL", "CONFERENCE", "SUPERBOWL"}
)
PARITY_KEYS = (
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_pressure_allowed_5g",
    "away_pressure_allowed_5g",
    "home_rest_days",
    "away_rest_days",
    "diff_off_epa_5g",
    "roof_dome",
)
# Re-export v21 names the sealed runner already calls.
parse_product_week = v21.parse_product_week
require_kickoff = v21.require_kickoff
record_as_of_check = v21.record_as_of_check
read_and_assert_hfa = v21.read_and_assert_hfa
model_execution_label = v21.model_execution_label
injury_allowed_flagged = v21.injury_allowed_flagged

WINDOW_5G_RULE = (
    "last 5 completed REG team-games with (season, week) < game; "
    "bye weeks omitted (no row); postseason omitted; 2025 REG tail fills early 2026"
)


def enforce_cap_pair(game_week_cap: int, pbp_week_cap: int) -> Dict[str, Any]:
    """X-5: pbp_week_cap must be game_week_cap - 1. W7 refused."""
    g, p = int(game_week_cap), int(pbp_week_cap)
    if g == 7 or p == 7 and g != 8:
        # pbp=7 is required for W8 (g=8). g=7 is W7 mode → refused.
        if g == 7:
            return {"ok": False, "flag": "W7_REFUSED", "game_week_cap": g, "pbp_week_cap": p}
    if g not in ALLOWED_GAME_WEEK_CAPS:
        return {"ok": False, "flag": "CAP_GAME_WEEK_NOT_ALLOWED", "game_week_cap": g, "pbp_week_cap": p}
    if p != g - 1:
        return {
            "ok": False,
            "flag": "CAP_PAIR_MISMATCH",
            "game_week_cap": g,
            "pbp_week_cap": p,
            "required_pbp_week_cap": g - 1,
        }
    return {"ok": True, "flag": None, "game_week_cap": g, "pbp_week_cap": p}


def assert_feature_store_pin(store: Path, expected: Optional[str]) -> Dict[str, Any]:
    """X-1: expected sha MUST come from outside the store. No FEATURE_STORE.sha256 fallback."""
    if not store.is_dir():
        return {"status": "BLOCKED", "reason": "FEATURE_STORE_MISSING", "path": str(store)}
    got = v21.feature_store_digest(store)
    pin = (expected or "").strip()
    if not pin:
        return {
            "status": "BLOCKED",
            "reason": "FEATURE_STORE_SHA_UNPINNED_EXTERNAL",
            "got": got,
            "expected": None,
            "fallback_used": False,
        }
    if got.lower() != pin.lower():
        return {
            "status": "BLOCKED",
            "reason": "FEATURE_STORE_SHA_MISMATCH",
            "got": got,
            "expected": pin.lower(),
            "fallback_used": False,
        }
    return {"status": "OK", "sha256": got, "expected": pin.lower(), "fallback_used": False}


def injury_row_record(feat: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """X-4: per-row injury record. defaulted_injury is derived, never hardcoded false."""
    rec = v21.injury_allowed_flagged(feat)
    rec["defaulted_injury"] = "FLAG_IMPUTED_INJURY_DEFAULT" in rec["flags"]
    rec["missing_nowcast"] = "FLAG_MISSING_KOSEDGE_INJURY_NOWCAST" in rec["flags"]
    rec["recorded"] = True
    return rec


def run_label(
    *,
    blocked: Sequence[str],
    any_null: bool,
    mode: str,
    model_calls_ok: int,
) -> str:
    """X-7: null / no model → BLOCKED_NO_MODEL_EXECUTION. W8 success is PROSPECTIVE-RESEARCH."""
    if any_null or int(model_calls_ok) <= 0:
        return "BLOCKED_NO_MODEL_EXECUTION"
    if blocked:
        return "BLOCKED"
    if mode == "retrospective-w4w6":
        return "RETROSPECTIVE"
    if mode == "w8-pregame":
        return "PROSPECTIVE-RESEARCH"
    return "BLOCKED"


def is_postseason_play(play: Mapping[str, Any]) -> bool:
    st = str(play.get("season_type") or play.get("game_type") or "REG").upper()
    if st in POSTSEASON_TYPES:
        return True
    try:
        week = int(play.get("week") or 0)
    except (TypeError, ValueError):
        week = 0
    return week > 18


def last_n_played_reg(
    weekly: Mapping[Tuple[int, int, str], Mapping[str, Any]],
    *,
    team: str,
    before_season: int,
    before_week: int,
    n: int = 5,
) -> List[Tuple[int, int]]:
    """X-6: last n REG team-games strictly before (season, week). Byes absent. No POST."""
    played: List[Tuple[int, int]] = []
    for season, week, t in weekly:
        if t != team:
            continue
        if week < 1 or week > 18:
            continue
        if (int(season), int(week)) >= (int(before_season), int(before_week)):
            continue
        played.append((int(season), int(week)))
    played = sorted(set(played))
    return played[-int(n) :]


def weekly_situational_reg(
    plays: Iterable[Mapping[str, Any]],
    *,
    pbp_week_cap: int,
) -> Dict[Tuple[int, int, str], Dict[str, Any]]:
    """REG-only weekly rates + play counts. Postseason dropped."""
    kept = [p for p in plays if not is_postseason_play(p)]
    p25 = [p for p in kept if int(p.get("season") or 0) == 2025]
    p26 = [p for p in kept if int(p.get("season") or 0) == 2026]
    weekly = {}
    weekly.update(v21.weekly_situational_from_pbp(p25, pbp_week_cap=18))
    weekly.update(v21.weekly_situational_from_pbp(p26, pbp_week_cap=pbp_week_cap))
    counts: Dict[Tuple[int, int, str], Dict[str, int]] = {}
    for play in kept:
        try:
            season = int(play.get("season") or 0)
            week = int(play.get("week") or 0)
        except (TypeError, ValueError):
            continue
        if week < 1 or week > 18:
            continue
        if season == 2026 and week > int(pbp_week_cap):
            continue
        posteam = v21.canon_team(str(play.get("posteam") or ""))
        defteam = v21.canon_team(str(play.get("defteam") or ""))
        if posteam:
            counts.setdefault((season, week, posteam), {"off_plays": 0, "def_plays": 0})
            counts[(season, week, posteam)]["off_plays"] += 1
        if defteam:
            counts.setdefault((season, week, defteam), {"off_plays": 0, "def_plays": 0})
            counts[(season, week, defteam)]["def_plays"] += 1
    for key, rec in weekly.items():
        c = counts.get(key) or {}
        rec["off_plays"] = int(c.get("off_plays") or 0)
        rec["def_plays"] = int(c.get("def_plays") or 0)
        rec["n_weeks"] = 1
        rec["game_type"] = "REG"
    return weekly


def attach_lagged_rolling_played(
    weekly: Mapping[Tuple[int, int, str], Mapping[str, Any]],
    *,
    season: int,
    team: str,
    game_week: int,
    window: int = 5,
) -> Tuple[Dict[str, Optional[float]], List[str]]:
    """5g over last played REG games, not calendar weeks (bye/postseason)."""
    played = last_n_played_reg(
        weekly, team=team, before_season=season, before_week=game_week, n=window
    )
    field_map = {
        "off_epa_per_play_5g": "off_epa_per_play",
        "def_epa_allowed_per_play_5g": "def_epa_allowed_per_play",
        "pressure_rate_allowed_5g": "pressure_rate_allowed",
        "pressure_rate_generated_5g": "pressure_rate_generated",
        "pass_rate_5g": "pass_rate",
        "early_down_pass_rate_5g": "early_down_pass_rate",
        "red_zone_td_rate_5g": "red_zone_td_rate",
        "success_rate_offense_5g": "success_rate_offense",
        "success_rate_defense_allowed_5g": "success_rate_defense_allowed",
    }
    out: Dict[str, Optional[float]] = {}
    used = [v21.source_week_key(s, w) for s, w in played]
    for dest, src in field_map.items():
        nums = []
        for s, w in played:
            rec = weekly.get((s, w, team))
            if rec is None or rec.get(src) is None:
                continue
            nums.append(float(rec[src]))
        out[dest] = (sum(nums) / len(nums)) if nums else None
    return out, used


def _season_row_from_weekly(
    weekly: Mapping[Tuple[int, int, str], Mapping[str, Any]],
    *,
    team: str,
    season: int,
    week_max: int,
) -> Optional[Dict[str, Any]]:
    rows = [
        weekly[(s, w, t)]
        for (s, w, t) in weekly
        if t == team and s == season and 1 <= w <= week_max and w <= 18
    ]
    if not rows:
        return None

    def avg(key: str) -> Optional[float]:
        xs = [float(r[key]) for r in rows if r.get(key) is not None]
        return (sum(xs) / len(xs)) if xs else None

    off_plays = sum(int(r.get("off_plays") or 0) for r in rows)
    def_plays = sum(int(r.get("def_plays") or 0) for r in rows)
    return {
        "off_epa_per_play": avg("off_epa_per_play"),
        "def_epa_allowed_per_play": avg("def_epa_allowed_per_play"),
        "success_rate_offense": avg("success_rate_offense"),
        "success_rate_defense_allowed": avg("success_rate_defense_allowed"),
        "pass_rate": avg("pass_rate"),
        "red_zone_td_rate": avg("red_zone_td_rate"),
        "pressure_rate_generated": avg("pressure_rate_generated"),
        "pressure_rate_allowed": avg("pressure_rate_allowed"),
        "offensive_plays": off_plays,
        "defensive_plays": def_plays,
        "n_weeks": len(rows),
        "games_played": len(rows),
    }


def import_backbone(base: Path) -> Dict[str, Any]:
    ms = Path(base) / "services" / "model-service"
    if not (ms / "src" / "services" / "nfl_season_engine" / "efficiency_backbone.py").is_file():
        return {"ok": False, "reason": "efficiency_backbone.py missing in BASE"}
    if str(ms) not in sys.path:
        sys.path.insert(0, str(ms))
    try:
        from src.services.nfl_season_engine.efficiency_backbone import (  # type: ignore
            blend_packages,
            build_package_from_season_row,
            package_to_strength_indices,
            prior_current_blend_weight,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "build_package_from_season_row": build_package_from_season_row,
        "blend_packages": blend_packages,
        "prior_current_blend_weight": prior_current_blend_weight,
        "package_to_strength_indices": package_to_strength_indices,
        "source": "BASE:nfl_season_engine.efficiency_backbone",
    }


def rebuild_strength_indices(
    *,
    base: Path,
    weekly: Mapping[Tuple[int, int, str], Mapping[str, Any]],
    team: str,
    game_week: int,
    game_season: int = 2026,
    input_shas: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """X-2 / §5.3: lag-only backbone rebuild. Never emit dataclass 1.0 on miss."""
    as_of_week = int(game_week) - 1
    empty = {
        "offense_index": None,
        "defense_index": None,
        "prior_source": None,
        "as_of_week": as_of_week,
        "w_current": None,
        "ok": False,
        "flag": "FLAG_MISSING_TRUE_PR_PRIOR",
    }
    if as_of_week < 1 and game_season == 2026:
        # week 1: current empty; prior 2025 still legal
        pass
    bb = import_backbone(base)
    if not bb.get("ok"):
        empty["reason"] = bb.get("reason")
        return empty
    prior_row = _season_row_from_weekly(weekly, team=team, season=2025, week_max=18)
    curr_row = _season_row_from_weekly(
        weekly, team=team, season=game_season, week_max=max(as_of_week, 0)
    )
    if prior_row is None and (curr_row is None or as_of_week < 1):
        empty["reason"] = "no lagged season rows"
        return empty
    try:
        prior_pkg = bb["build_package_from_season_row"](
            team,
            prior_row
            or {
                "off_epa_per_play": None,
                "n_weeks": 0,
            },
            as_of="2025-W18",
            source="pbp_rolling_backbone",
            prior_season=2025,
        )
        if prior_row is None:
            return {**empty, "reason": "2025 prior package required; missing"}
        if curr_row is None:
            curr_games = 0
            # current empty → blend weight 0, but still need a current package
            curr_pkg = bb["build_package_from_season_row"](
                team,
                {"n_weeks": 0, "games_played": 0},
                as_of=f"{game_season}-W{max(as_of_week, 0):02d}",
                source="pbp_rolling_backbone",
                prior_season=2025,
            )
        else:
            curr_games = int(curr_row["games_played"])
            curr_pkg = bb["build_package_from_season_row"](
                team,
                curr_row,
                as_of=f"{game_season}-W{as_of_week:02d}",
                source="pbp_rolling_backbone",
                prior_season=2025,
            )
        w_cur = float(bb["prior_current_blend_weight"](current_games=curr_games))
        blended = bb["blend_packages"](prior_pkg, curr_pkg, current_games=curr_games)
        idx = bb["package_to_strength_indices"](blended)
        off = v21.parse_num(idx.get("offense_index"))
        deff = v21.parse_num(idx.get("defense_index"))
        if off is None or deff is None:
            return {**empty, "reason": "backbone returned null index"}
        # 1.0 is legal only as a computed blend, never as a silent default.
        return {
            "offense_index": off,
            "defense_index": deff,
            "prior_source": "pbp_rolling_backbone",
            "as_of_week": as_of_week,
            "w_current": w_cur,
            "current_games": curr_games,
            "backbone": bb["source"],
            "input_shas": dict(input_shas or {}),
            "ok": True,
            "flag": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {**empty, "reason": f"{type(exc).__name__}: {exc}"}


def build_feature_store(
    *,
    base: Path,
    games_csv: Path,
    pbp_paths: Sequence[Path],
    out_dir: Path,
    game_week_cap: int,
    pbp_week_cap: int,
    pack_path: Optional[Path] = None,
    helper_sha: Optional[str] = None,
) -> Dict[str, Any]:
    """v2.2 store. X-9 caller must refuse if out_dir already exists."""
    caps = enforce_cap_pair(game_week_cap, pbp_week_cap)
    if not caps["ok"]:
        return {
            "script_id": SCRIPT_ID,
            "ruling": RULING,
            "status": "BLOCKED",
            "blocked": [caps["flag"]],
            "caps": caps,
            "w7_refused": True,
        }
    if out_dir.exists():
        return {
            "script_id": SCRIPT_ID,
            "ruling": RULING,
            "status": "BLOCKED",
            "blocked": ["OUT_DIR_EXISTS"],
            "path": str(out_dir),
        }
    out_dir.mkdir(parents=True)
    games = [
        g
        for g in v21._load_games_csv(games_csv)
        if g["season"] == 2026 and 1 <= g["week"] <= game_week_cap
    ]
    pack = v21._load_pack_kickoffs(
        pack_path or (base / "apps/web/lib/nfl-canonical-schedule-2026.json")
    )
    plays: List[Mapping[str, Any]] = []
    input_shas = {str(p): v21.sha256_file(Path(p)) for p in pbp_paths}
    input_shas[str(games_csv)] = v21.sha256_file(games_csv)
    for pbp in pbp_paths:
        plays.extend(list(v21._iter_pbp(Path(pbp))))
    weekly = weekly_situational_reg(plays, pbp_week_cap=pbp_week_cap)

    rows: List[Dict[str, Any]] = []
    flags_out: List[Dict[str, Any]] = []
    blocked: List[str] = []
    for game in games:
        gid = game["game_id_product"]
        pack_row = pack.get(gid) or {}
        kickoff = pack_row.get("kickoff_utc")
        ko = v21.require_kickoff(kickoff, game_id=gid)
        if not ko["ok"]:
            blocked.append(str(ko["flag"]) + " " + gid)
        home_roll, home_src = attach_lagged_rolling_played(
            weekly, season=2026, team=game["home_team"], game_week=int(game["week"])
        )
        away_roll, away_src = attach_lagged_rolling_played(
            weekly, season=2026, team=game["away_team"], game_week=int(game["week"])
        )
        src_weeks = sorted(set(home_src + away_src))
        as_of = v21.record_as_of_check(
            game_id=gid,
            game_week=int(game["week"]),
            source_weeks=src_weeks,
            kickoff_utc=kickoff,
            feature_as_of_week=int(game["week"]) - 1,
        )
        inj = injury_row_record({})
        home_idx = rebuild_strength_indices(
            base=base,
            weekly=weekly,
            team=game["home_team"],
            game_week=int(game["week"]),
            input_shas=input_shas,
        )
        away_idx = rebuild_strength_indices(
            base=base,
            weekly=weekly,
            team=game["away_team"],
            game_week=int(game["week"]),
            input_shas=input_shas,
        )
        feat: Dict[str, Any] = {
            "game_id_product": gid,
            "season": 2026,
            "week": int(game["week"]),
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "kickoff_utc": kickoff,
            "as_of": as_of.to_dict(),
            "as_of_week": as_of.as_of_week,
            "source_weeks": src_weeks,
            "window_5g_rule": WINDOW_5G_RULE,
            "pbp_week_cap": int(pbp_week_cap),
            "game_week_cap": int(game_week_cap),
            "rolling_window_sql": v21.LAGGED_WINDOW_SQL,
            "home_rest_days": game.get("home_rest"),
            "away_rest_days": game.get("away_rest"),
            "diff_rest_days": (
                None
                if game.get("home_rest") is None or game.get("away_rest") is None
                else float(game["home_rest"]) - float(game["away_rest"])
            ),
            "roof_dome": (
                1
                if str(game.get("roof") or "").lower() in {"dome", "closed"}
                else (0 if game.get("roof") else None)
            ),
            "surface_turf": (
                1
                if "turf" in str(game.get("surface") or "").lower()
                else (0 if game.get("surface") else None)
            ),
            "is_divisional_game": v21.parse_num(game.get("div_game")),
            "injury_record": inj,
            "injury_handling": inj["injury_handling"],
            "injury_source": inj["injury_source"],
            "defaulted_injury": inj["defaulted_injury"],
            "home_injury_impact": None,
            "away_injury_impact": None,
            "diff_injury_impact": None,
            "offense_index_home": home_idx.get("offense_index"),
            "offense_index_away": away_idx.get("offense_index"),
            "defense_index_home": home_idx.get("defense_index"),
            "defense_index_away": away_idx.get("defense_index"),
            "prior_source": "pbp_rolling_backbone" if home_idx.get("ok") and away_idx.get("ok") else None,
            "strength_as_of_week": home_idx.get("as_of_week"),
            "w_current_home": home_idx.get("w_current"),
            "w_current_away": away_idx.get("w_current"),
            "strength_input_shas": input_shas,
        }
        for roll_key, (hk, ak) in v21.SIDE_MAP.items():
            feat[hk] = home_roll.get(roll_key)
            feat[ak] = away_roll.get(roll_key)
        for a, b, dest in (
            ("home_off_epa_5g", "away_off_epa_5g", "diff_off_epa_5g"),
            ("home_def_epa_allowed_5g", "away_def_epa_allowed_5g", "diff_def_epa_allowed_5g"),
            ("home_pressure_generated_5g", "away_pressure_generated_5g", "diff_pressure_generated_5g"),
            ("home_pressure_allowed_5g", "away_pressure_allowed_5g", "diff_pressure_allowed_5g"),
            ("home_red_zone_td_rate_5g", "away_red_zone_td_rate_5g", "diff_red_zone_td_rate_5g"),
            ("home_success_offense_5g", "away_success_offense_5g", "diff_success_rate_5g"),
        ):
            ha, aa = v21.parse_num(feat.get(a)), v21.parse_num(feat.get(b))
            feat[dest] = None if ha is None or aa is None else ha - aa
        if as_of.status != "PASS":
            blocked.append(f"as_of {gid} {as_of.flags}")
        row_flags = list(as_of.flags) + list(inj["flags"])
        if not home_idx.get("ok") or not away_idx.get("ok"):
            row_flags.append("FLAG_MISSING_TRUE_PR_PRIOR")
            blocked.append(f"strength {gid}")
        if game.get("home_rest") is None or game.get("away_rest") is None:
            row_flags.append("FLAG_MISSING_REST")
        if feat.get("home_off_epa_5g") is None or feat.get("away_off_epa_5g") is None:
            row_flags.append("FLAG_MISSING_EPA")
        rows.append(feat)
        for fl in row_flags:
            flags_out.append({"game_id_product": gid, "flag": fl, "as_of_week": as_of.as_of_week})

    feat_path = out_dir / "features.jsonl"
    flag_path = out_dir / "feature-flags.jsonl"
    with feat_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    with flag_path.open("w", encoding="utf-8") as fh:
        for row in flags_out:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    if helper_sha:
        (out_dir / "HELPER.sha256").write_text(helper_sha.strip() + "\n", encoding="utf-8")
    pin = v21.write_feature_store_pin(out_dir)
    report = {
        "script_id": SCRIPT_ID,
        "ruling": RULING,
        "status": "BLOCKED" if blocked else "BUILT",
        "blocked": blocked,
        "n_rows": len(rows),
        "caps": caps,
        "window_5g_rule": WINDOW_5G_RULE,
        "feature_store_sha256": pin["feature_store_sha256"],
        "helper_sha256": helper_sha,
        "w7_refused": True,
        "do_not_run_until_imv_code_check": True,
    }
    (out_dir / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    v21.write_feature_store_pin(out_dir)
    return report


def parity_vs_prod(
    local_rows: Sequence[Mapping[str, Any]],
    prod_rows: Sequence[Mapping[str, Any]],
    *,
    week_cap: int,
    keys: Sequence[str] = PARITY_KEYS,
) -> Dict[str, Any]:
    """X-3: FAIL on any value mismatch. More than two keys. Week-capped."""
    if len(keys) < 3:
        return {"status": "FAIL_TOO_FEW_KEYS", "n_keys": len(keys)}
    local = {
        r.get("game_id_product") or r.get("game_id"): r
        for r in v21.apply_week_cap(local_rows, week_cap)
    }
    prod = {
        r.get("game_id_product") or r.get("game_id"): r
        for r in v21.apply_week_cap(prod_rows, week_cap)
    }
    diffs: List[Dict[str, Any]] = []
    prod_leaks: List[str] = []
    local_leaks: List[str] = []
    compared = 0
    for gid, lrow in sorted(local.items()):
        prow = prod.get(gid)
        if prow is None:
            diffs.append({"game_id": gid, "reason": "missing_in_prod"})
            continue
        compared += 1
        week = int(lrow["week"])
        if lrow.get("as_of_week") is not None and int(lrow["as_of_week"]) >= week:
            local_leaks.append(gid)
        if prow.get("as_of_week") is None or int(prow["as_of_week"]) >= week:
            prod_leaks.append(gid)
        src = lrow.get("source_weeks") or []
        if any(v21._source_after_or_same_game(str(w), 2026, week) for w in src):
            local_leaks.append(gid)
        for key in keys:
            lv, pv = v21.parse_num(lrow.get(key)), v21.parse_num(prow.get(key))
            if lv is None and pv is None:
                continue
            if lv is None or pv is None or abs(lv - pv) > 1e-9:
                diffs.append({"game_id": gid, "key": key, "local": lv, "prod": pv})
    if local_leaks:
        status = "BLOCKED_LOCAL_LEAK"
    elif diffs:
        status = "FAIL_VALUE_MISMATCH"
    else:
        status = "PASS"
    return {
        "status": status,
        "week_cap": int(week_cap),
        "keys": list(keys),
        "n_keys": len(keys),
        "compared": compared,
        "n_local": len(local),
        "n_prod": len(prod),
        "diffs": diffs,
        "prod_same_week_leak": sorted(set(prod_leaks)),
        "local_same_week_leak": sorted(set(local_leaks)),
        "fails_on_value_mismatch": True,
    }


def _cmd_build(args: argparse.Namespace) -> int:
    helper = Path(__file__).resolve()
    report = build_feature_store(
        base=Path(args.base),
        games_csv=Path(args.games_csv),
        pbp_paths=[Path(p) for p in args.pbp],
        out_dir=Path(args.out),
        game_week_cap=int(args.game_week_cap),
        pbp_week_cap=int(args.pbp_week_cap),
        pack_path=Path(args.pack) if args.pack else None,
        helper_sha=v21.sha256_file(helper),
    )
    print(json.dumps(report, indent=2))
    return 6 if report["status"] == "BLOCKED" else 0


def _cmd_parity(args: argparse.Namespace) -> int:
    def load_jsonl(path: Path) -> List[Dict[str, Any]]:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    doc = parity_vs_prod(
        load_jsonl(Path(args.local)),
        load_jsonl(Path(args.prod)),
        week_cap=int(args.week_cap),
    )
    print(json.dumps(doc, indent=2))
    return 0 if doc["status"] == "PASS" else 6


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="nfl_imv_v22")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--base", required=True)
    b.add_argument("--games-csv", required=True)
    b.add_argument("--pbp", action="append", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--game-week-cap", type=int, required=True)
    b.add_argument("--pbp-week-cap", type=int, required=True)
    b.add_argument("--pack", default="")
    b.set_defaults(func=_cmd_build)
    p = sub.add_parser("parity")
    p.add_argument("--local", required=True)
    p.add_argument("--prod", required=True)
    p.add_argument("--week-cap", type=int, required=True)
    p.set_defaults(func=_cmd_parity)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
