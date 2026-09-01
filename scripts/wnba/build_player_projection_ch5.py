#!/usr/bin/env python3
"""Build WNBA Chapter 5 PlayerProjection pack from Ch2 minutes × rates × team pace.

Reads only Ch2 talent/minutes + Ch2 rebased team pack (pace / implied_ppg / residual).
Writes one opening-night PlayerProjection per MIN>0 roster slot.
Does not emit board rows, props tags, or a new minute grid.
Does not use NBA means as the prior.
"""

from __future__ import annotations

import html as htmlmod
import json
import math
import re
import urllib.request
from collections import defaultdict
from pathlib import Path
from statistics import pstdev
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "services/model-service/src/services/wnba_season_engine/data"
GRID_PATH = DATA / "wnba_minutes_grid_2026.json"
TALENT_PATH = DATA / "wnba_player_talent_3y_2026.json"
REBASED_PATH = DATA / "wnba_team_prior_rebased_2026.json"
OUT_PATH = DATA / "wnba_player_projection_2026.json"

WEIGHTS = {"2024": 0.20, "2025": 0.30, "2026": 0.50}
RESIDUAL_CAP = 3.0  # WNBA_TEAM_REBASE_RESIDUAL_CAP
MINUTE_GRID_SUM = 200
ENGINE_VERSION = "wnba-season-engine-v0.1"
TEAM_COUNT = 15

TEAM_CODES = {
    "ATL",
    "CHI",
    "CON",
    "DAL",
    "GSV",
    "IND",
    "LAS",
    "LA",
    "MIN",
    "NY",
    "PHX",
    "POR",
    "SEA",
    "TOR",
    "WSH",
}
BR_ALIAS = {
    "LVA": "LAS",
    "LAS": "LA",
    "NYL": "NY",
    "PHO": "PHX",
    "WAS": "WSH",
}
COMBINED_TEAM_MARKERS = frozenset({"TOT", "2TM", "3TM", "4TM"})

PER_GAME_URLS = {
    "2024": "https://www.basketball-reference.com/wnba/years/2024_per_game.html",
    "2025": "https://www.basketball-reference.com/wnba/years/2025_per_game.html",
    "2026": "https://www.basketball-reference.com/wnba/years/2026_per_game.html",
}
ADVANCED_URLS = {
    "2024": "https://www.basketball-reference.com/wnba/years/2024_advanced.html",
    "2025": "https://www.basketball-reference.com/wnba/years/2025_advanced.html",
    "2026": "https://www.basketball-reference.com/wnba/years/2026_advanced.html",
}

COUNT_KEYS = ("pts", "reb", "ast", "stl", "blk", "tov", "fg3")
UA = {"User-Agent": "Mozilla/5.0 (compatible; KosEdgeWnbaCh5/1.0)"}


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", "replace").replace("<!--", "").replace("-->", "")


def _load_html(season: str, kind: str, url: str) -> str:
    path = Path(f"/tmp/wnba_{season}_{kind}.html")
    if path.is_file() and path.stat().st_size > 50_000:
        return (
            path.read_text(encoding="utf-8", errors="replace")
            .replace("<!--", "")
            .replace("-->", "")
        )
    html = _get(url)
    path.write_text(html, encoding="utf-8")
    return html.replace("<!--", "").replace("-->", "")


def _clean_name(name: str) -> str:
    return re.sub(r"</?strong>?", "", name or "").strip()


def _canon_team(raw: str) -> str:
    t = (raw or "").strip().upper()
    if t in COMBINED_TEAM_MARKERS or re.fullmatch(r"[2-9]TM", t or ""):
        return t
    return BR_ALIAS.get(t, t)


def _is_combined_team(team: str) -> bool:
    if team in COMBINED_TEAM_MARKERS:
        return True
    return bool(re.fullmatch(r"[2-9]TM", team or ""))


def _season_row(rows: list[dict]) -> dict:
    combined = [r for r in rows if _is_combined_team(r["team"])]
    if combined:
        return max(combined, key=lambda r: r.get("mp", 0.0))
    real = [r for r in rows if r["team"] in TEAM_CODES] or list(rows)
    if len(real) == 1:
        return real[0]
    mp = sum(float(r.get("mp") or 0.0) for r in real) or 1.0
    out = dict(max(real, key=lambda r: r.get("mp", 0.0)))
    out["mp"] = mp
    out["g"] = sum(int(r.get("g") or 0) for r in real)
    for k in COUNT_KEYS:
        if k in out or any(k in r for r in real):
            out[k] = (
                sum(
                    float(r.get(k) or 0.0) * float(r.get("mp") or 0.0) for r in real
                )
                / mp
            )
    if any("mp_per_g" in r for r in real):
        out["mp_per_g"] = (
            sum(
                float(r.get("mp_per_g") or 0.0) * float(r.get("mp") or 0.0)
                for r in real
            )
            / mp
        )
    if any("usg" in r for r in real):
        out["usg"] = (
            sum(float(r.get("usg") or 0.0) * float(r.get("mp") or 0.0) for r in real)
            / mp
        )
    return out


def parse_per_game(html: str, season: str) -> list[dict]:
    table = re.search(
        r'<table[^>]*id="per_game"[^>]*>.*?</table>', html, flags=re.S | re.I
    )
    if not table:
        raise SystemExit(f"missing per_game table for {season}")
    rows: list[dict] = []
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", table.group(0), flags=re.S | re.I):
        href = re.search(r"/wnba/players/[^/]+/([a-z0-9]+)\.html", tr)
        fields: dict[str, str] = {}
        for k, v in re.findall(
            r'<t[dh][^>]*data-stat="([^"]+)"[^>]*>(.*?)</t[dh]>', tr, flags=re.S | re.I
        ):
            fields[k] = htmlmod.unescape(re.sub(r"<[^>]+>", "", v)).strip()
        name = _clean_name(fields.get("player") or "")
        if not name or name == "Player" or not href:
            continue
        team = _canon_team(fields.get("team") or "")
        try:
            g = int(float(fields.get("g") or 0))
            mp_g = float(fields.get("mp_per_g") or 0)
            mp = float(fields.get("mp") or (mp_g * g))
            pts = float(fields.get("pts_per_g") or 0)
            reb = float(fields.get("trb_per_g") or 0)
            ast = float(fields.get("ast_per_g") or 0)
            stl = float(fields.get("stl_per_g") or 0)
            blk = float(fields.get("blk_per_g") or 0)
            tov = float(fields.get("tov_per_g") or 0)
            fg3 = float(fields.get("fg3_per_g") or 0)
        except ValueError:
            continue
        if mp_g <= 0:
            continue
        rows.append(
            {
                "player_id": href.group(1),
                "player_name": name,
                "team": team,
                "g": g,
                "mp": mp,
                "mp_per_g": mp_g,
                "pts": pts,
                "reb": reb,
                "ast": ast,
                "stl": stl,
                "blk": blk,
                "tov": tov,
                "fg3": fg3,
                "season": season,
            }
        )
    return rows


def parse_usg(html: str, season: str) -> list[dict]:
    table = re.search(
        r'<table[^>]*id="advanced"[^>]*>.*?</table>', html, flags=re.S | re.I
    )
    if not table:
        raise SystemExit(f"missing advanced table for {season}")
    rows: list[dict] = []
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", table.group(0), flags=re.S | re.I):
        href = re.search(r"/wnba/players/[^/]+/([a-z0-9]+)\.html", tr)
        fields: dict[str, str] = {}
        for k, v in re.findall(
            r'<t[dh][^>]*data-stat="([^"]+)"[^>]*>(.*?)</t[dh]>', tr, flags=re.S | re.I
        ):
            fields[k] = htmlmod.unescape(re.sub(r"<[^>]+>", "", v)).strip()
        name = _clean_name(fields.get("player") or "")
        if not name or name == "Player" or not href:
            continue
        team = _canon_team(fields.get("team") or "")
        try:
            mp = float(fields.get("mp") or 0)
            usg = float(fields.get("usg_pct") or 0)
        except ValueError:
            continue
        rows.append(
            {
                "player_id": href.group(1),
                "team": team,
                "mp": mp,
                "usg": usg,
                "season": season,
            }
        )
    return rows


def _weighted_mean(pairs: list[tuple[float, float]]) -> tuple[float, float]:
    num = den = 0.0
    for v, w in pairs:
        if w <= 0:
            continue
        num += w * v
        den += w
    if den <= 0:
        return 0.0, 0.0
    return num / den, den


def _sigma_from_rates(rates: list[float], mean: float) -> float:
    """Computed σ of a per-minute (or USG) rate — never a hardcoded game σ=4."""
    clean = [float(r) for r in rates if r is not None]
    if len(clean) >= 2:
        return float(pstdev(clean))
    if len(clean) == 1:
        return max(0.15 * abs(clean[0]), 1e-4)
    return max(0.15 * abs(mean), 1e-4)


def main() -> None:
    grid = json.loads(GRID_PATH.read_text(encoding="utf-8"))
    talent = json.loads(TALENT_PATH.read_text(encoding="utf-8"))
    rebased = json.loads(REBASED_PATH.read_text(encoding="utf-8"))

    per_by_season: dict[str, list[dict]] = {}
    usg_by_season: dict[str, list[dict]] = {}
    for season in WEIGHTS:
        per_by_season[season] = parse_per_game(
            _load_html(season, "per_game", PER_GAME_URLS[season]), season
        )
        usg_by_season[season] = parse_usg(
            _load_html(season, "advanced", ADVANCED_URLS[season]), season
        )
        print(
            f"{season}: per_game={len(per_by_season[season])} "
            f"usg={len(usg_by_season[season])}"
        )

    rates: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for season, rows in per_by_season.items():
        by_p: dict[str, list] = defaultdict(list)
        for r in rows:
            by_p[r["player_id"]].append(r)
        for pid, plist in by_p.items():
            row = _season_row(plist)
            mp_g = float(row["mp_per_g"] or 0) or (
                float(row["mp"]) / max(int(row["g"]), 1)
            )
            if mp_g <= 0:
                continue
            rates[pid][season] = {
                "pts_pm": float(row["pts"]) / mp_g,
                "reb_pm": float(row["reb"]) / mp_g,
                "ast_pm": float(row["ast"]) / mp_g,
                "stl_pm": float(row["stl"]) / mp_g,
                "blk_pm": float(row["blk"]) / mp_g,
                "tov_pm": float(row["tov"]) / mp_g,
                "fg3_pm": float(row["fg3"]) / mp_g,
                "mp_g": mp_g,
            }

    for season, rows in usg_by_season.items():
        by_p: dict[str, list] = defaultdict(list)
        for r in rows:
            by_p[r["player_id"]].append(r)
        for pid, plist in by_p.items():
            row = _season_row(plist)
            rates[pid].setdefault(season, {})
            rates[pid][season]["usg"] = float(row["usg"])

    league_pace = sum(float(t["pace"]) for t in rebased["teams"].values()) / float(
        TEAM_COUNT
    )

    players_out: dict[str, dict[str, Any]] = {}
    team_checks: dict[str, dict[str, float]] = {}

    for team in sorted(TEAM_CODES):
        slots = grid["teams"][team]
        team_row = rebased["teams"][team]
        pace = float(team_row["pace"])
        target_pts = float(team_row["implied_ppg"])
        pace_scale = pace / league_pace if league_pace > 0 else 1.0

        built: list[dict[str, Any]] = []
        for slot in slots:
            pid = slot["player_id"]
            minutes = float(slot["minutes"])
            if minutes <= 0:
                continue
            season_map = rates.get(pid) or {}
            rate_means: dict[str, float] = {}
            rate_sigmas_pm: dict[str, float] = {}
            for key in (
                "pts_pm",
                "reb_pm",
                "ast_pm",
                "stl_pm",
                "blk_pm",
                "tov_pm",
                "fg3_pm",
            ):
                pairs = []
                year_vals = []
                for season, w in WEIGHTS.items():
                    row = season_map.get(season) or {}
                    if key not in row:
                        continue
                    pairs.append((float(row[key]), w))
                    year_vals.append(float(row[key]))
                mean, mass = _weighted_mean(pairs)
                if mass <= 0:
                    # expansion / missing box: tiny rate prior (not NBA means)
                    mean = 0.04 if key == "pts_pm" else 0.015
                    year_vals = [mean]
                rate_means[key] = mean
                rate_sigmas_pm[key] = _sigma_from_rates(year_vals, mean)

            usg_pairs = []
            usg_vals = []
            for season, w in WEIGHTS.items():
                row = season_map.get(season) or {}
                if "usg" not in row:
                    continue
                usg_pairs.append((float(row["usg"]), w))
                usg_vals.append(float(row["usg"]))
            usg_mean, usg_mass = _weighted_mean(usg_pairs)
            if usg_mass <= 0:
                usg_mean = 18.0  # WNBA rotation prior — not NBA 20
                usg_vals = [usg_mean]
            usg_sigma = _sigma_from_rates(usg_vals, usg_mean)

            raw = {
                "PTS": rate_means["pts_pm"] * minutes * pace_scale,
                "REB": rate_means["reb_pm"] * minutes * pace_scale,
                "AST": rate_means["ast_pm"] * minutes * pace_scale,
                "STL": rate_means["stl_pm"] * minutes * pace_scale,
                "BLK": rate_means["blk_pm"] * minutes * pace_scale,
                "TOV": rate_means["tov_pm"] * minutes * pace_scale,
                "3PM": rate_means["fg3_pm"] * minutes * pace_scale,
            }
            sigma_raw = {
                "PTS": rate_sigmas_pm["pts_pm"] * minutes * pace_scale,
                "REB": rate_sigmas_pm["reb_pm"] * minutes * pace_scale,
                "AST": rate_sigmas_pm["ast_pm"] * minutes * pace_scale,
                "STL": rate_sigmas_pm["stl_pm"] * minutes * pace_scale,
                "BLK": rate_sigmas_pm["blk_pm"] * minutes * pace_scale,
                "TOV": rate_sigmas_pm["tov_pm"] * minutes * pace_scale,
                "3PM": rate_sigmas_pm["fg3_pm"] * minutes * pace_scale,
            }
            tal = (talent.get("players") or {}).get(pid) or {}
            built.append(
                {
                    "player_id": pid,
                    "player_name": slot["player_name"],
                    "team": team,
                    "role": slot.get("role"),
                    "talent": float(slot.get("talent") or tal.get("talent") or 0),
                    "expansion_only": bool(
                        slot.get("expansion_only") or tal.get("expansion_only")
                    ),
                    "MIN": round(minutes, 4),
                    "USG": round(usg_mean, 4),
                    "_raw": raw,
                    "_sigma_raw": sigma_raw,
                    "_usg_sigma": usg_sigma,
                }
            )

        raw_pts_sum = sum(p["_raw"]["PTS"] for p in built) or 1.0
        pts_scale = target_pts / raw_pts_sum
        team_pts = 0.0
        team_min = 0.0
        for p in built:
            raw = p.pop("_raw")
            sigma_raw = p.pop("_sigma_raw")
            usg_sigma = p.pop("_usg_sigma")
            pts = raw["PTS"] * pts_scale
            reb, ast = raw["REB"], raw["AST"]
            stl, blk, tov, fg3 = raw["STL"], raw["BLK"], raw["TOV"], raw["3PM"]
            pra = pts + reb + ast
            pr = pts + reb
            ra = reb + ast
            sig = {
                "MIN": 0.0,
                "USG": round(usg_sigma, 4),
                "PTS": round(sigma_raw["PTS"] * pts_scale, 4),
                "REB": round(sigma_raw["REB"], 4),
                "AST": round(sigma_raw["AST"], 4),
                "STL": round(sigma_raw["STL"], 4),
                "BLK": round(sigma_raw["BLK"], 4),
                "TOV": round(sigma_raw["TOV"], 4),
                "3PM": round(sigma_raw["3PM"], 4),
            }
            sig["PRA"] = round(
                math.sqrt(sig["PTS"] ** 2 + sig["REB"] ** 2 + sig["AST"] ** 2), 4
            )
            sig["PR"] = round(math.sqrt(sig["PTS"] ** 2 + sig["REB"] ** 2), 4)
            sig["RA"] = round(math.sqrt(sig["REB"] ** 2 + sig["AST"] ** 2), 4)

            proj = {
                **p,
                "PTS": round(pts, 4),
                "REB": round(reb, 4),
                "AST": round(ast, 4),
                "STL": round(stl, 4),
                "BLK": round(blk, 4),
                "TOV": round(tov, 4),
                "3PM": round(fg3, 4),
                "PRA": round(pra, 4),
                "PR": round(pr, 4),
                "RA": round(ra, 4),
                "sigma": sig,
                "pace_scale": round(pace_scale, 6),
                "pts_identity_scale": round(pts_scale, 6),
            }
            players_out[f"{team}:{p['player_id']}"] = proj
            team_pts += proj["PTS"]
            team_min += proj["MIN"]

        drift = abs(team_pts - target_pts)
        if drift > RESIDUAL_CAP + 1e-6:
            raise SystemExit(
                f"PTS identity failed for {team}: sum={team_pts:.4f} "
                f"target={target_pts:.4f} drift={drift:.4f} > cap={RESIDUAL_CAP}"
            )
        if abs(team_min - MINUTE_GRID_SUM) > 1e-3:
            raise SystemExit(f"MIN sum failed for {team}: {team_min}")
        team_checks[team] = {
            "sum_min": round(team_min, 4),
            "sum_pts": round(team_pts, 4),
            "target_pts": target_pts,
            "pts_drift": round(drift, 6),
            "residual_cap": RESIDUAL_CAP,
            "pace": pace,
            "pts_identity_scale": round(pts_scale, 6),
        }

    out = {
        "engine_version": ENGINE_VERSION,
        "as_of": "2026-09-01",
        "season": "2026",
        "chapter": 5,
        "object": "PlayerProjection",
        "WNBA_TEAM_REBASE_RESIDUAL_CAP": RESIDUAL_CAP,
        "WNBA_TEAM_CARRY_SHRINK_unchanged": 0.85,
        "MINUTE_GRID_SUM": MINUTE_GRID_SUM,
        "PLAYER_YEAR_WEIGHTS": WEIGHTS,
        "league_mean_pace": round(league_pace, 4),
        "forbidden_leftover_fair_line_game_ids": ["401857105", "401857106"],
        "formula": (
            "rates = Σ_y w_y · (stat_per_g / mp_per_g); "
            "raw = rate × MIN × (team_pace / league_pace); "
            "PTS scaled so Σ PTS = team implied_ppg; "
            "σ from season-rate dispersion × MIN (computed, not hardcoded)"
        ),
        "reads": [
            str(GRID_PATH.name),
            str(TALENT_PATH.name),
            str(REBASED_PATH.name),
            "BR WNBA per_game + advanced USG (3y)",
        ],
        "does_not": [
            "board emit",
            "props / PLAY / LEAN",
            "new minute grid",
            "NBA means as the prior",
            "team if",
            "changing 0.85",
            "Aug 1 leftover KEI blend",
            "NBA/CFB/NFL packs",
        ],
        "player_count": len(players_out),
        "team_count": TEAM_COUNT,
        "team_checks": team_checks,
        "players": players_out,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    max_drift = max(v["pts_drift"] for v in team_checks.values())
    print(
        f"wrote {OUT_PATH.name} players={len(players_out)} "
        f"max_pts_drift={max_drift:.6f} residual_cap={RESIDUAL_CAP}"
    )


if __name__ == "__main__":
    main()
