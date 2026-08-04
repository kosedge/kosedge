#!/usr/bin/env python3
"""Final smoke / trust checks for the NFL season engine (live BFF or Railway).

Writes artifacts under data/ops/nfl-season-engine-final-smoke-YYYYMMDD/.

Examples:
  python scripts/nfl/final_smoke_season_engine.py
  python scripts/nfl/final_smoke_season_engine.py --base https://www.kosedge.com
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "data" / "ops" / f"nfl-season-engine-final-smoke-{date.today().strftime('%Y%m%d')}"


def _req(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any], float]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8")
            elapsed = time.time() - t0
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"_raw": raw[:2000]}
            return res.status, payload if isinstance(payload, dict) else {"_list": payload}, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"_raw": raw[:2000]}
        return e.code, payload if isinstance(payload, dict) else {"error": str(payload)}, elapsed
    except Exception as e:  # noqa: BLE001
        elapsed = time.time() - t0
        return 0, {"error": str(e)}, elapsed


def _find_player(players: list[dict[str, Any]], name_substr: str, team: str | None = None) -> dict[str, Any] | None:
    needle = name_substr.lower()
    for p in players:
        if team and p.get("team") != team:
            continue
        if needle in str(p.get("player_name", "")).lower():
            return p
    return None


def _pe(p: dict[str, Any] | None, key: str) -> float | None:
    if not p:
        return None
    pe = p.get("point_estimate") or {}
    v = pe.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_nanish(v: Any) -> bool:
    if v is None:
        return False
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return False


def _scan_nans(obj: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(_scan_nans(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:200]):
            hits.extend(_scan_nans(v, f"{path}[{i}]"))
    elif _is_nanish(obj):
        hits.append(path)
    return hits


def summarize_players(players: list[dict[str, Any]], team: str) -> list[dict[str, Any]]:
    out = []
    for p in players:
        if p.get("team") != team:
            continue
        pe = p.get("point_estimate") or {}
        out.append(
            {
                "name": p.get("player_name"),
                "pos": p.get("position"),
                "role": p.get("usage_role"),
                "pass_yds": pe.get("pass_yards"),
                "pass_td": pe.get("pass_td"),
                "int": pe.get("interceptions") or pe.get("pass_int"),
                "rush_yds": pe.get("rush_yards"),
                "rush_td": pe.get("rush_td"),
                "rec": pe.get("receptions"),
                "rec_yds": pe.get("receiving_yards"),
                "rec_td": pe.get("receiving_td"),
            }
        )
    # sort QB/RB/WR/TE
    order = {"QB": 0, "RB": 1, "WR": 2, "TE": 3}
    out.sort(key=lambda r: (order.get(str(r["pos"]), 9), -(float(r.get("rec_yds") or r.get("rush_yds") or r.get("pass_yds") or 0))))
    return out


def check_game_sanity(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    players = payload.get("players") or []
    if not players:
        findings.append({"level": "fail", "check": f"{label}:players", "detail": "empty players"})
        return findings

    nan_hits = _scan_nans(players)
    if nan_hits:
        findings.append({"level": "fail", "check": f"{label}:nan", "detail": nan_hits[:20]})

    # QB checks
    for team in (payload.get("home_team"), payload.get("away_team")):
        qbs = [p for p in players if p.get("team") == team and p.get("position") == "QB"]
        if not qbs:
            findings.append({"level": "fail", "check": f"{label}:{team}:qb", "detail": "no QB row"})
            continue
        qb = max(qbs, key=lambda p: float((p.get("point_estimate") or {}).get("pass_yards") or 0))
        py = _pe(qb, "pass_yards")
        ptd = _pe(qb, "pass_td")
        pint = _pe(qb, "interceptions")
        if pint is None:
            pint = _pe(qb, "pass_int")
        if py is None or not (120 <= py <= 380):
            findings.append(
                {
                    "level": "weak" if py and 80 <= py <= 420 else "fail",
                    "check": f"{label}:{team}:qb_pass_yds",
                    "detail": {"player": qb.get("player_name"), "pass_yards": py},
                }
            )
        else:
            findings.append(
                {
                    "level": "pass",
                    "check": f"{label}:{team}:qb_pass_yds",
                    "detail": {"player": qb.get("player_name"), "pass_yards": py, "pass_td": ptd, "int": pint},
                }
            )
        if ptd is not None and not (0.3 <= ptd <= 3.8):
            findings.append(
                {
                    "level": "weak",
                    "check": f"{label}:{team}:qb_pass_td",
                    "detail": {"player": qb.get("player_name"), "pass_td": ptd},
                }
            )
        if pint is not None and not (0.1 <= pint <= 2.2):
            findings.append(
                {
                    "level": "weak",
                    "check": f"{label}:{team}:qb_int",
                    "detail": {"player": qb.get("player_name"), "int": pint},
                }
            )

    # RB rush yards — RB1 should not be absurd; Cook-100 regression was ~100+ wrong scale
    for team in (payload.get("home_team"), payload.get("away_team")):
        rbs = [p for p in players if p.get("team") == team and p.get("position") == "RB"]
        for rb in rbs[:3]:
            ry = _pe(rb, "rush_yards")
            role = str(rb.get("usage_role") or "")
            if ry is None:
                continue
            if ry > 140:
                findings.append(
                    {
                        "level": "fail",
                        "check": f"{label}:{team}:rb_rush_high",
                        "detail": {"player": rb.get("player_name"), "role": role, "rush_yards": ry},
                    }
                )
            elif "RB1" in role.upper() or role.upper().startswith("RB1") or "lead" in role.lower():
                if not (25 <= ry <= 120):
                    findings.append(
                        {
                            "level": "weak",
                            "check": f"{label}:{team}:rb1_rush",
                            "detail": {"player": rb.get("player_name"), "role": role, "rush_yards": ry},
                        }
                    )
                else:
                    findings.append(
                        {
                            "level": "pass",
                            "check": f"{label}:{team}:rb1_rush",
                            "detail": {"player": rb.get("player_name"), "role": role, "rush_yards": ry},
                        }
                    )

    # WR receptions — WR1 shouldn't be ~9-catch regression absurdity; allow 3–9
    for team in (payload.get("home_team"), payload.get("away_team")):
        wrs = [p for p in players if p.get("team") == team and p.get("position") == "WR"]
        for wr in sorted(wrs, key=lambda p: float((p.get("point_estimate") or {}).get("receptions") or 0), reverse=True)[:2]:
            rec = _pe(wr, "receptions")
            ryd = _pe(wr, "receiving_yards")
            if rec is not None and rec > 12:
                findings.append(
                    {
                        "level": "fail",
                        "check": f"{label}:{team}:wr_rec_high",
                        "detail": {"player": wr.get("player_name"), "receptions": rec, "rec_yds": ryd},
                    }
                )
            elif rec is not None and ryd is not None:
                level = "pass" if 2.0 <= rec <= 9.5 and 25 <= ryd <= 140 else "weak"
                findings.append(
                    {
                        "level": level,
                        "check": f"{label}:{team}:wr_top",
                        "detail": {"player": wr.get("player_name"), "role": wr.get("usage_role"), "receptions": rec, "rec_yds": ryd},
                    }
                )

    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://www.kosedge.com", help="BFF base URL")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--n-replicates", type=int, default=40)
    ap.add_argument("--n-sims", type=int, default=120)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = args.base.rstrip("/")

    report: dict[str, Any] = {
        "as_of": date.today().isoformat(),
        "base": base,
        "checks": [],
        "artifacts": [],
    }

    # --- status ---
    code, status, elapsed = _req("GET", f"{base}/api/nfl/season-engine/status")
    (out_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    report["artifacts"].append("status.json")
    ok_status = (
        code == 200
        and status.get("mode") == "real"
        and status.get("schedule_game_count") == 272
        and "real-depth" in str(status.get("engine_version", ""))
        and status.get("depth_named_skill_teams") == 32
    )
    report["checks"].append(
        {
            "level": "pass" if ok_status else "fail",
            "check": "status",
            "http": code,
            "elapsed_s": round(elapsed, 2),
            "detail": {
                "engine_version": status.get("engine_version"),
                "mode": status.get("mode"),
                "schedule_source": status.get("schedule_source"),
                "schedule_game_count": status.get("schedule_game_count"),
                "depth_source": status.get("depth_source"),
                "depth_as_of": status.get("depth_as_of"),
                "depth_named_skill_teams": status.get("depth_named_skill_teams"),
                "error": status.get("error"),
            },
        }
    )

    matchups = [
        {"label": "SF@LA_W1", "homeTeam": "LA", "awayTeam": "SF", "week": 1, "expect_roles": [
            ("SF", "McCaffrey", "RB"),
            ("SF", "Purdy", "QB"),
            ("LA", "Nacua", "WR"),
            ("LA", "Stafford", "QB"),
            ("LA", "Williams", "RB"),
        ]},
        {"label": "DET@BUF_W2", "homeTeam": "BUF", "awayTeam": "DET", "week": 2, "expect_roles": [
            ("BUF", "Allen", "QB"),
            ("BUF", "Cook", "RB"),
            ("DET", "Gibbs", "RB"),  # may vary by depth
        ]},
        {"label": "KC@MIA_W3", "homeTeam": "MIA", "awayTeam": "KC", "week": 3, "expect_roles": [
            ("KC", "Mahomes", "QB"),
            ("KC", "Kelce", "TE"),
        ]},
        {"label": "LAC@SEA_W4", "homeTeam": "SEA", "awayTeam": "LAC", "week": 4, "expect_roles": [
            ("SEA", "Smith-Njigba", "WR"),
            ("SEA", "Darnold", "QB"),
        ]},
        {"label": "ARI@DAL_W8", "homeTeam": "DAL", "awayTeam": "ARI", "week": 8, "expect_roles": [
            ("DAL", "Prescott", "QB"),
        ]},
    ]

    for m in matchups:
        body = {
            "homeTeam": m["homeTeam"],
            "awayTeam": m["awayTeam"],
            "week": m["week"],
            "season": 2026,
            "nReplicates": args.n_replicates,
            "seed": 42,
            "includeDiagnostics": True,
        }
        code, payload, elapsed = _req("POST", f"{base}/api/nfl/season-engine/game-boxes", body)
        fname = f"game-boxes-{m['label']}.json"
        (out_dir / fname).write_text(json.dumps(payload, indent=2) + "\n")
        report["artifacts"].append(fname)

        players = payload.get("players") or []
        role_findings = []
        for team, name_sub, pos in m.get("expect_roles", []):
            p = _find_player(players, name_sub, team)
            if not p:
                # soft if Gibbs missing etc.
                level = "weak" if name_sub in ("Gibbs",) else "fail"
                role_findings.append({"level": level, "player": name_sub, "team": team, "detail": "missing"})
            else:
                ok_pos = p.get("position") == pos
                role_findings.append(
                    {
                        "level": "pass" if ok_pos else "weak",
                        "player": p.get("player_name"),
                        "team": team,
                        "position": p.get("position"),
                        "usage_role": p.get("usage_role"),
                        "rush_yds": _pe(p, "rush_yards"),
                        "rec": _pe(p, "receptions"),
                        "pass_yds": _pe(p, "pass_yards"),
                    }
                )

        sanity = check_game_sanity(payload, m["label"]) if code == 200 else [
            {"level": "fail", "check": f"{m['label']}:http", "detail": payload.get("error") or code}
        ]
        summary = {
            "home": summarize_players(players, m["homeTeam"]),
            "away": summarize_players(players, m["awayTeam"]),
            "game_script": payload.get("game_script_summary"),
            "notes": payload.get("notes"),
            "mode": payload.get("mode"),
            "engine_version": payload.get("engine_version"),
            "depth_source": payload.get("roster_source") or payload.get("depth_source"),
        }
        (out_dir / f"summary-{m['label']}.json").write_text(json.dumps(summary, indent=2) + "\n")
        report["checks"].append(
            {
                "level": "fail" if any(x.get("level") == "fail" for x in sanity + role_findings) else (
                    "weak" if any(x.get("level") == "weak" for x in sanity + role_findings) else "pass"
                ),
                "check": f"game_boxes:{m['label']}",
                "http": code,
                "elapsed_s": round(elapsed, 2),
                "roles": role_findings,
                "sanity": sanity,
            }
        )

    # --- Injury: CMC W1-4 ---
    base_body = {
        "homeTeam": "LA",
        "awayTeam": "SF",
        "week": 1,
        "season": 2026,
        "nReplicates": args.n_replicates,
        "seed": 7,
        "includeDiagnostics": True,
    }
    code_b, base_box, el_b = _req("POST", f"{base}/api/nfl/season-engine/game-boxes", base_body)
    inj_body = {
        **base_body,
        "injuryPaths": [
            {
                "team": "SF",
                "player_name": "Christian McCaffrey",
                "status": "out",
                "week_start": 1,
                "week_end": 4,
            }
        ],
    }
    code_i, inj_box, el_i = _req("POST", f"{base}/api/nfl/season-engine/game-boxes", inj_body)
    (out_dir / "injury-cmc-baseline-SF@LA-W1.json").write_text(json.dumps(base_box, indent=2) + "\n")
    (out_dir / "injury-cmc-out-SF@LA-W1.json").write_text(json.dumps(inj_box, indent=2) + "\n")

    cmc_b = _find_player(base_box.get("players") or [], "McCaffrey", "SF")
    cmc_i = _find_player(inj_box.get("players") or [], "McCaffrey", "SF")
    # RB2 candidate
    james_b = _find_player(base_box.get("players") or [], "Jordan James", "SF") or _find_player(
        base_box.get("players") or [], "James", "SF"
    )
    james_i = _find_player(inj_box.get("players") or [], "Jordan James", "SF") or _find_player(
        inj_box.get("players") or [], "James", "SF"
    )
    # Best non-CMC RB by rush yards after injury
    def top_rb(players, team, exclude_substr=None):
        rbs = [p for p in players if p.get("team") == team and p.get("position") == "RB"]
        if exclude_substr:
            rbs = [p for p in rbs if exclude_substr.lower() not in str(p.get("player_name", "")).lower()]
        if not rbs:
            return None
        return max(rbs, key=lambda p: float((p.get("point_estimate") or {}).get("rush_yards") or 0))

    rb2_i = top_rb(inj_box.get("players") or [], "SF", "McCaffrey")
    cmc_rush_b = _pe(cmc_b, "rush_yards")
    cmc_rush_i = _pe(cmc_i, "rush_yards")
    rb2_rush_b = _pe(james_b or top_rb(base_box.get("players") or [], "SF", "McCaffrey"), "rush_yards")
    rb2_rush_i = _pe(rb2_i, "rush_yards")

    cmc_ok = (
        code_b == 200
        and code_i == 200
        and cmc_rush_i is not None
        and cmc_rush_b is not None
        and cmc_rush_i <= max(3.0, 0.15 * cmc_rush_b)
        and rb2_rush_i is not None
        and rb2_rush_b is not None
        and rb2_rush_i > rb2_rush_b + 5
    )
    report["checks"].append(
        {
            "level": "pass" if cmc_ok else "fail",
            "check": "injury:CMC_W1-4",
            "http": [code_b, code_i],
            "elapsed_s": [round(el_b, 2), round(el_i, 2)],
            "detail": {
                "cmc_rush_baseline": cmc_rush_b,
                "cmc_rush_injured": cmc_rush_i,
                "rb2_name": (rb2_i or {}).get("player_name") if rb2_i else None,
                "rb2_rush_baseline": rb2_rush_b,
                "rb2_rush_injured": rb2_rush_i,
                "rb2_role_injured": (rb2_i or {}).get("usage_role") if rb2_i else None,
            },
        }
    )

    # Outside injury range: week 5 SF game
    w5_body = {
        "homeTeam": "SF",
        "awayTeam": "WAS",  # W6 actually WAS@SF; use W5 opponent for SF
        "week": 5,
        "season": 2026,
        "nReplicates": args.n_replicates,
        "seed": 7,
        "includeDiagnostics": True,
        "injuryPaths": [
            {
                "team": "SF",
                "player_name": "Christian McCaffrey",
                "status": "out",
                "week_start": 1,
                "week_end": 4,
            }
        ],
    }
    # Find SF week 5 opponent from packaged schedule if needed
    sched_path = ROOT / "services/model-service/src/services/nfl_season_engine/data/nfl_regular_schedule_2026.json"
    if sched_path.exists():
        sched = json.loads(sched_path.read_text())
        for g in sched["games"]:
            if g["week"] == 5 and "SF" in (g["home_team"], g["away_team"]):
                w5_body["homeTeam"] = g["home_team"]
                w5_body["awayTeam"] = g["away_team"]
                break
            if g["week"] == 6 and g["home_team"] == "SF":
                # fallback later
                pass

    code_w5, w5_box, el_w5 = _req("POST", f"{base}/api/nfl/season-engine/game-boxes", w5_body)
    (out_dir / "injury-cmc-outside-range.json").write_text(json.dumps({"request": w5_body, "response": w5_box}, indent=2) + "\n")
    cmc_w5 = _find_player(w5_box.get("players") or [], "McCaffrey", "SF")
    cmc_w5_rush = _pe(cmc_w5, "rush_yards")
    outside_ok = code_w5 == 200 and cmc_w5_rush is not None and cmc_w5_rush >= 20
    report["checks"].append(
        {
            "level": "pass" if outside_ok else "weak",
            "check": "injury:CMC_outside_W1-4",
            "http": code_w5,
            "elapsed_s": round(el_w5, 2),
            "detail": {
                "matchup": f"{w5_body['awayTeam']}@{w5_body['homeTeam']} W{w5_body['week']}",
                "cmc_rush": cmc_w5_rush,
                "note": "CMC should recover usage outside injury window",
            },
        }
    )

    # --- WR1 out: Mike Evans SF W1-3 ---
    wr_base = {
        "homeTeam": "LA",
        "awayTeam": "SF",
        "week": 1,
        "season": 2026,
        "nReplicates": args.n_replicates,
        "seed": 11,
        "includeDiagnostics": True,
    }
    code_wb, wr_b, el_wb = _req("POST", f"{base}/api/nfl/season-engine/game-boxes", wr_base)
    wr_inj = {
        **wr_base,
        "injuryPaths": [
            {
                "team": "SF",
                "player_name": "Mike Evans",
                "status": "out",
                "week_start": 1,
                "week_end": 3,
            }
        ],
    }
    code_wi, wr_i, el_wi = _req("POST", f"{base}/api/nfl/season-engine/game-boxes", wr_inj)
    (out_dir / "injury-wr1-evans-baseline.json").write_text(json.dumps(wr_b, indent=2) + "\n")
    (out_dir / "injury-wr1-evans-out.json").write_text(json.dumps(wr_i, indent=2) + "\n")

    evans_b = _find_player(wr_b.get("players") or [], "Evans", "SF")
    evans_i = _find_player(wr_i.get("players") or [], "Evans", "SF")
    # Other WRs should gain targets/receptions
    def wr_targets(players, team, exclude=None):
        rows = []
        for p in players:
            if p.get("team") != team or p.get("position") != "WR":
                continue
            if exclude and exclude.lower() in str(p.get("player_name", "")).lower():
                continue
            pe = p.get("point_estimate") or {}
            rows.append((p.get("player_name"), float(pe.get("receptions") or 0), float(pe.get("receiving_yards") or 0), p.get("usage_role")))
        rows.sort(key=lambda x: x[1], reverse=True)
        return rows

    wr_others_b = wr_targets(wr_b.get("players") or [], "SF", "Evans")
    wr_others_i = wr_targets(wr_i.get("players") or [], "SF", "Evans")
    sum_rec_b = sum(r[1] for r in wr_others_b[:3])
    sum_rec_i = sum(r[1] for r in wr_others_i[:3])
    evans_rec_i = _pe(evans_i, "receptions")
    evans_rec_b = _pe(evans_b, "receptions")
    wr_ok = (
        code_wb == 200
        and code_wi == 200
        and evans_rec_i is not None
        and evans_rec_b is not None
        and evans_rec_i <= max(0.5, 0.2 * evans_rec_b)
        and sum_rec_i > sum_rec_b + 0.5
    )
    report["checks"].append(
        {
            "level": "pass" if wr_ok else "fail",
            "check": "injury:WR1_Evans_W1-3",
            "http": [code_wb, code_wi],
            "elapsed_s": [round(el_wb, 2), round(el_wi, 2)],
            "detail": {
                "evans_rec_baseline": evans_rec_b,
                "evans_rec_injured": evans_rec_i,
                "other_wr_rec_sum_top3_baseline": sum_rec_b,
                "other_wr_rec_sum_top3_injured": sum_rec_i,
                "other_wrs_injured": wr_others_i[:4],
            },
        }
    )

    # --- Survivor ---
    survivor_cases = [
        {"label": "W1_clean", "week": 1, "alreadyUsed": [], "expect_home_fav_near_top": True},
        {"label": "W1_used_BUF_KC", "week": 1, "alreadyUsed": ["BUF", "KC"], "excluded": ["BUF", "KC"]},
        {"label": "W5_byes_CAR_KC", "week": 5, "alreadyUsed": [], "bye_teams": ["CAR", "KC"]},
        {"label": "W2_clean", "week": 2, "alreadyUsed": ["DET"], "excluded": ["DET"]},
    ]
    for sc in survivor_cases:
        body = {
            "week": sc["week"],
            "alreadyUsed": sc["alreadyUsed"],
            "nSims": args.n_sims,
            "season": 2026,
            "seed": 99,
            "topN": 20,
            "includeDiagnostics": True,
        }
        code, payload, elapsed = _req("POST", f"{base}/api/nfl/season-engine/survivor", body, timeout=180)
        fname = f"survivor-{sc['label']}.json"
        (out_dir / fname).write_text(json.dumps(payload, indent=2) + "\n")
        report["artifacts"].append(fname)

        ranked = payload.get("ranked_picks") or []
        all_week = payload.get("all_teams_week") or ranked
        findings = []
        if code != 200 or payload.get("error"):
            findings.append({"level": "fail", "detail": payload.get("error") or f"http {code}"})
        elif not ranked:
            findings.append({"level": "fail", "detail": "empty ranked_picks"})
        else:
            findings.append({"level": "pass", "detail": f"{len(ranked)} ranked picks"})

        for t in sc.get("excluded", []):
            in_ranked = any(p.get("team") == t and not p.get("already_used") for p in ranked)
            # should be excluded from pickable ranked or marked already_used
            pickable = [p for p in ranked if not p.get("already_used")]
            if any(p.get("team") == t for p in pickable):
                findings.append({"level": "fail", "detail": f"{t} still pickable after already_used"})
            else:
                findings.append({"level": "pass", "detail": f"{t} excluded from pickable"})

        for t in sc.get("bye_teams", []):
            row = next((p for p in all_week if p.get("team") == t), None)
            if row is None:
                # may simply omit bye teams from ranked
                in_ranked_pickable = any(p.get("team") == t and p.get("plays_this_week", True) for p in ranked)
                if in_ranked_pickable:
                    findings.append({"level": "fail", "detail": f"bye team {t} ranked as playing"})
                else:
                    findings.append({"level": "pass", "detail": f"bye team {t} not pickable / omitted"})
            else:
                if row.get("plays_this_week") is False or row.get("opponent") in (None, "", "BYE"):
                    findings.append({"level": "pass", "detail": f"bye team {t} flagged", "row": {
                        "plays_this_week": row.get("plays_this_week"),
                        "opponent": row.get("opponent"),
                        "win_rate": row.get("win_rate"),
                    }})
                else:
                    findings.append({"level": "fail", "detail": f"bye team {t} looks active", "row": row})

        # Ranking sanity: top pick win_rate should be high-ish for early weeks
        if ranked:
            top = ranked[0]
            wr = float(top.get("win_rate") or top.get("win_prob") or 0)
            if wr < 0.45:
                findings.append({"level": "weak", "detail": f"top pick win_rate low ({top.get('team')} {wr})"})
            else:
                findings.append(
                    {
                        "level": "pass",
                        "detail": {
                            "top3": [
                                {
                                    "team": p.get("team"),
                                    "opp": p.get("opponent"),
                                    "ha": p.get("home_away"),
                                    "win_rate": p.get("win_rate"),
                                    "pick_now": p.get("pick_now_score"),
                                }
                                for p in ranked[:5]
                            ]
                        },
                    }
                )

        level = "fail" if any(f.get("level") == "fail" for f in findings) else (
            "weak" if any(f.get("level") == "weak" for f in findings) else "pass"
        )
        report["checks"].append(
            {
                "level": level,
                "check": f"survivor:{sc['label']}",
                "http": code,
                "elapsed_s": round(elapsed, 2),
                "mode": payload.get("mode"),
                "findings": findings,
            }
        )

    # Edge: bye-week game boxes for a team on bye (should error or empty cleanly)
    bye_body = {
        "homeTeam": "KC",
        "awayTeam": "CAR",
        "week": 5,
        "season": 2026,
        "nReplicates": 20,
        "seed": 1,
    }
    code_bye, bye_payload, el_bye = _req("POST", f"{base}/api/nfl/season-engine/game-boxes", bye_body)
    (out_dir / "edge-KC-CAR-W5-both-bye.json").write_text(json.dumps(bye_payload, indent=2) + "\n")
    # Both on bye — expect error or empty, not crash with NaNs
    nan_hits = _scan_nans(bye_payload)
    bye_ok = code_bye in (200, 400, 422, 502) and not nan_hits and (
        bye_payload.get("error")
        or not (bye_payload.get("players") or [])
        or bye_payload.get("notes")
    )
    # If it returns players for a non-game, that's weak
    if code_bye == 200 and (bye_payload.get("players") or []) and not bye_payload.get("error"):
        report["checks"].append(
            {
                "level": "weak",
                "check": "edge:both_bye_matchup",
                "http": code_bye,
                "elapsed_s": round(el_bye, 2),
                "detail": "Returned players for KC vs CAR in W5 when both are on bye — UI should not offer this matchup",
            }
        )
    else:
        report["checks"].append(
            {
                "level": "pass" if bye_ok and not nan_hits else "fail",
                "check": "edge:both_bye_matchup",
                "http": code_bye,
                "elapsed_s": round(el_bye, 2),
                "detail": {"error": bye_payload.get("error"), "n_players": len(bye_payload.get("players") or []), "nans": nan_hits[:10]},
            }
        )

    # Tallies
    counts = {"pass": 0, "weak": 0, "fail": 0}
    for c in report["checks"]:
        counts[c.get("level", "weak")] = counts.get(c.get("level", "weak"), 0) + 1
    report["summary"] = counts

    (out_dir / "smoke-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"out_dir": str(out_dir), "summary": counts}, indent=2))
    for c in report["checks"]:
        mark = {"pass": "PASS", "weak": "WEAK", "fail": "FAIL"}.get(c["level"], "?")
        print(f"[{mark}] {c['check']}")
    return 1 if counts.get("fail", 0) else 0


if __name__ == "__main__":
    sys.exit(main())
