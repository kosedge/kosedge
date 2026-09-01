#!/usr/bin/env python3
"""Build WNBA Chapter 2 packs: 3y player talent × minutes grid → rebased teams.

Sources: Basketball-Reference WNBA player Advanced for 2024 / 2025 / 2026
(BPM not published on BR WNBA advanced — talent = PER − 15, centered).
stats.wnba.com timed out in build env (Ch0/Ch1 failover).

Minute grid v0 = class grid (star 30–34 / starter 24–30 / bench residual),
sums to **200** (40×5). Not NBA 240. Not 15 handwritten teams.

Roster seed = 2026 YTD primary team (midseason). Expansion TOR/POR players
with only 2026 rows stay on TOR/POR (YTD-only weights renormalize).
No invented 2025 for expansion. Ch1 shrink 0.85 unchanged.
"""

from __future__ import annotations

import html as htmlmod
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "services/model-service/src/services/wnba_season_engine/data"
CH1_PATH = DATA / "wnba_team_prior_2026.json"

SEASON_URLS = {
    "2024": "https://www.basketball-reference.com/wnba/years/2024_advanced.html",
    "2025": "https://www.basketball-reference.com/wnba/years/2025_advanced.html",
    "2026": "https://www.basketball-reference.com/wnba/years/2026_advanced.html",
}
WEIGHTS = {"2024": 0.20, "2025": 0.30, "2026": 0.50}

# Canonical desk keys (matches wnba_data / Ch1 pack).
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
# BR abbreviations → canonical.
BR_ALIAS = {
    "LVA": "LAS",  # Las Vegas Aces
    "LAS": "LA",  # Los Angeles Sparks on BR
    "NYL": "NY",
    "PHO": "PHX",
    "WAS": "WSH",
}
COMBINED_TEAM_MARKERS = frozenset({"TOT", "2TM", "3TM", "4TM"})
EXPANSION_TEAMS = frozenset({"TOR", "POR"})

# Class grid — WNBA bands (NOT NBA 32–36 / 28–32).
STAR_MIN = 32.0  # mid of 30–34
STARTER_MIN = 27.0  # mid of 24–30
ROTATION_N = 9
MINUTE_GRID_SUM = 200.0
RESIDUAL_CAP = 3.0  # WNBA_TEAM_REBASE_RESIDUAL_CAP
MIN_SEASON_MP = 50.0  # shorter season than NBA
PER_CENTER = 15.0
UA = {"User-Agent": "Mozilla/5.0 (compatible; KosEdgeWnbaCh2/1.0)"}


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", "replace").replace("<!--", "").replace("-->", "")


def _clean_name(name: str) -> str:
    return re.sub(r"</?strong>?", "", name or "").strip()


def _canon_team(raw: str) -> str:
    t = (raw or "").strip().upper()
    if t in COMBINED_TEAM_MARKERS or re.fullmatch(r"[2-9]TM", t or ""):
        return t
    return BR_ALIAS.get(t, t)


def parse_advanced(html: str, season: str) -> list[dict]:
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

        def fnum(key: str) -> float | None:
            s = (fields.get(key) or "").strip()
            if not s:
                return None
            try:
                return float(s)
            except ValueError:
                return None

        per = fnum("per")
        if per is None:
            continue
        rows.append(
            {
                "player_id": href.group(1),
                "player_name": name,
                "team": team,
                "pos": fields.get("pos") or "",
                "g": int(fnum("g") or 0),
                "mp": float(fnum("mp") or 0),
                "per": per,
                "talent": round(per - PER_CENTER, 4),  # PER − 15
                "ws40": fnum("ws_per_40"),
                "season": season,
            }
        )
    return rows


def _is_combined_team(team: str) -> bool:
    if team in COMBINED_TEAM_MARKERS:
        return True
    return bool(re.fullmatch(r"[2-9]TM", team or ""))


def season_player_row(rows_for_player: list[dict]) -> dict:
    """Prefer BR combined total; never sum splits + total."""
    combined = [r for r in rows_for_player if _is_combined_team(r["team"])]
    if combined:
        return max(combined, key=lambda r: r["mp"])
    real = [r for r in rows_for_player if r["team"] in TEAM_CODES]
    if not real:
        real = list(rows_for_player)
    if len(real) == 1:
        return real[0]
    mp = sum(r["mp"] for r in real) or 1.0
    per = sum(r["per"] * r["mp"] for r in real) / mp
    base = max(real, key=lambda r: r["mp"])
    return {
        **base,
        "per": per,
        "talent": round(per - PER_CENTER, 4),
        "mp": mp,
        "g": sum(r["g"] for r in real),
        "team": "MIX",
    }


def _primary_team_from_rows(rows: list[dict]) -> str | None:
    real = [r for r in rows if r["team"] in TEAM_CODES]
    if not real:
        return None
    return max(real, key=lambda r: r["mp"])["team"]


def main() -> None:
    ch1 = json.loads(CH1_PATH.read_text(encoding="utf-8"))
    by_season: dict[str, list[dict]] = {}
    for season, url in SEASON_URLS.items():
        cache = Path(f"/tmp/wnba_{season}_advanced.html")
        if cache.is_file():
            html = cache.read_text(encoding="utf-8", errors="replace").replace(
                "<!--", ""
            ).replace("-->", "")
        else:
            html = _get(url)
            cache.write_text(html, encoding="utf-8")
        by_season[season] = parse_advanced(html, season)
        print(f"{season}: {len(by_season[season])} rows")

    players: dict[str, dict] = defaultdict(lambda: {"seasons": {}, "name": ""})
    for season, rows in by_season.items():
        by_p: dict[str, list] = defaultdict(list)
        for r in rows:
            by_p[r["player_id"]].append(r)
        for pid, plist in by_p.items():
            row = season_player_row(plist)
            players[pid]["name"] = row["player_name"]
            players[pid]["seasons"][season] = {
                "talent": float(row["talent"]),
                "per": round(float(row["per"]), 4),
                "mp": row["mp"],
                "g": row["g"],
                "team": row["team"],
                "pos": row["pos"],
            }

    # Midseason roster seed = 2026 YTD primary franchise.
    roster_team: dict[str, str] = {}
    from_team_2026: dict[str, str] = {}
    mp_by: dict[str, dict[str, float]] = defaultdict(dict)
    for r in by_season["2026"]:
        if r["team"] in TEAM_CODES:
            mp_by[r["player_id"]][r["team"]] = r["mp"]
    for pid, teams in mp_by.items():
        home = max(teams.items(), key=lambda kv: kv[1])[0]
        roster_team[pid] = home
        from_team_2026[pid] = home

    talent_pack_players = {}
    for pid, team in roster_team.items():
        num = den = 0.0
        detail = {}
        for season, w in WEIGHTS.items():
            row = players[pid]["seasons"].get(season)
            if not row or float(row["mp"]) < MIN_SEASON_MP:
                continue
            num += w * float(row["talent"])
            den += w
            detail[season] = row
        if den <= 0:
            continue
        seasons_present = set(detail)
        expansion_only = team in EXPANSION_TEAMS and seasons_present <= {"2026"}
        talent_pack_players[pid] = {
            "player_id": pid,
            "player_name": players[pid]["name"],
            "team_2026": team,
            "expansion_only": expansion_only,
            "talent": round(num / den, 4),
            "weight_mass": round(den, 4),
            "seasons": detail,
        }

    grids: dict[str, list] = {}
    for team in sorted(TEAM_CODES):
        cands = []
        for pid, row in talent_pack_players.items():
            if row["team_2026"] != team:
                continue
            mp26 = float((row["seasons"].get("2026") or {}).get("mp") or 0)
            cands.append((pid, float(row["talent"]), mp26))
        cands.sort(key=lambda x: (-x[1], -x[2]))
        rot = cands[:ROTATION_N]
        if len(rot) < ROTATION_N:
            print(f"WARN {team}: only {len(rot)} rotation candidates")
        base = []
        for i, (pid, tal, _mp) in enumerate(rot):
            if i < 2:
                role, mins = "star", STAR_MIN
            elif i < 5:
                role, mins = "starter", STARTER_MIN
            else:
                role, mins = "bench", 0.0
            base.append(
                {
                    "player_id": pid,
                    "player_name": talent_pack_players[pid]["player_name"],
                    "role": role,
                    "minutes": mins,
                    "talent": tal,
                    "expansion_only": talent_pack_players[pid]["expansion_only"],
                }
            )
        assigned = sum(b["minutes"] for b in base)
        bench = [b for b in base if b["role"] == "bench"]
        remain = MINUTE_GRID_SUM - assigned
        if bench:
            each = remain / len(bench)
            for b in bench:
                b["minutes"] = each
        elif base:
            # fewer than 5 on roster — scale stars/starters to 200
            pass
        total = sum(b["minutes"] for b in base) or 1.0
        scale = MINUTE_GRID_SUM / total
        for b in base:
            b["minutes"] = round(b["minutes"] * scale, 4)
        drift = MINUTE_GRID_SUM - sum(b["minutes"] for b in base)
        if base:
            base[0]["minutes"] = round(base[0]["minutes"] + drift, 4)
        grids[team] = base

    rebased = {}
    for team in sorted(TEAM_CODES):
        grid = grids[team]
        player_net = sum(b["talent"] * b["minutes"] for b in grid) / MINUTE_GRID_SUM
        ch1_net = float(ch1["teams"][team]["net_rating"])
        raw_resid = ch1_net - player_net
        resid = max(-RESIDUAL_CAP, min(RESIDUAL_CAP, raw_resid))
        team_net = player_net + resid
        lm_ortg = float(ch1["league_mean_post"]["ortg"])
        lm_drtg = float(ch1["league_mean_post"]["drtg"])
        ortg = lm_ortg + team_net / 2.0
        drtg = lm_drtg - team_net / 2.0
        pace = float(ch1["teams"][team]["pace"])
        rebased[team] = {
            "team": team,
            "team_name": ch1["teams"][team]["team_name"],
            "player_net": round(player_net, 4),
            "ch1_net": round(ch1_net, 4),
            "residual_raw": round(raw_resid, 4),
            "residual": round(resid, 4),
            "net_rating": round(team_net, 4),
            "ortg": round(ortg, 4),
            "drtg": round(drtg, 4),
            "pace": pace,
            "implied_ppg": round(pace * (ortg / 100.0), 2),
            "minutes_sum": round(sum(b["minutes"] for b in grid), 4),
            "rotation_n": len(grid),
            "expansion_only_on_grid": sum(1 for b in grid if b.get("expansion_only")),
        }

    DATA.mkdir(parents=True, exist_ok=True)

    expansion_players = [
        p
        for p in talent_pack_players.values()
        if p["expansion_only"] and p["team_2026"] in EXPANSION_TEAMS
    ]

    talent_out = {
        "engine_version": "wnba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "metric": "per_minus_15",
        "metric_note": (
            "BPM not on BR WNBA advanced; talent = PER − 15 (centered). "
            "Same Advanced path concepts as stats.wnba.com."
        ),
        "PLAYER_YEAR_WEIGHTS": WEIGHTS,
        "MIN_SEASON_MP": MIN_SEASON_MP,
        "source": "basketball-reference.com/wnba/years/{2024,2025,2026}_advanced.html",
        "notes": [
            "Season rows prefer BR combined markers TOT/2TM/3TM/4TM (never sum with splits).",
            "Roster seed = 2026 YTD primary team (midseason).",
            "Expansion TOR/POR: players with only 2026 seasons stay expansion_only; weights renormalize.",
            "Does not blend Aug-1 leftover fair-lines 401857105/401857106.",
        ],
        "player_count": len(talent_pack_players),
        "expansion_only_count": len(expansion_players),
        "players": talent_pack_players,
    }
    (DATA / "wnba_player_talent_3y_2026.json").write_text(
        json.dumps(talent_out, indent=2) + "\n", encoding="utf-8"
    )

    grid_out = {
        "engine_version": "wnba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "season": "2026",
        "MINUTE_GRID_SUM": int(MINUTE_GRID_SUM),
        "class_grid": {
            "star_minutes": STAR_MIN,
            "starter_minutes": STARTER_MIN,
            "rotation_n": ROTATION_N,
            "note": "star 30–34 mid=32; starter 24–30 mid=27; bench residual to 200 — not NBA classes",
        },
        "teams": {t: grids[t] for t in sorted(grids)},
    }
    (DATA / "wnba_minutes_grid_2026.json").write_text(
        json.dumps(grid_out, indent=2) + "\n", encoding="utf-8"
    )

    ppgs = [r["implied_ppg"] for r in rebased.values()]
    rebase_out = {
        "engine_version": "wnba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "season": "2026",
        "WNBA_TEAM_CARRY_SHRINK": ch1["WNBA_TEAM_CARRY_SHRINK"],
        "WNBA_TEAM_REBASE_RESIDUAL_CAP": RESIDUAL_CAP,
        "MINUTE_GRID_SUM": int(MINUTE_GRID_SUM),
        "formula": (
            "player_net = Σ(talent × minutes) / 200; "
            "residual = clip(ch1_net - player_net, ±WNBA_TEAM_REBASE_RESIDUAL_CAP); "
            "team_net = player_net + residual"
        ),
        "ch1_pack": str(CH1_PATH.name),
        "ppg_band_registered": {"low": 75.0, "high": 91.0},
        "ppg_observed": {"min": round(min(ppgs), 2), "max": round(max(ppgs), 2)},
        "forbidden_leftover_fair_line_game_ids": ["401857105", "401857106"],
        "team_count": len(rebased),
        "teams": rebased,
        "does_not": [
            "emit KEI onto /edge-board/wnba",
            "props / Edge tags",
            "change WNBA_TEAM_CARRY_SHRINK",
            "copy NBA minute classes as-is",
            "blend Aug-1 leftover fair-lines",
            "NBA/CFB/NFL packs",
        ],
    }
    (DATA / "wnba_team_prior_rebased_2026.json").write_text(
        json.dumps(rebase_out, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"wrote talent={len(talent_pack_players)} grids={len(grids)} "
        f"rebased={len(rebased)} ppg=[{min(ppgs):.1f},{max(ppgs):.1f}] "
        f"expansion_only={len(expansion_players)}"
    )


if __name__ == "__main__":
    main()
