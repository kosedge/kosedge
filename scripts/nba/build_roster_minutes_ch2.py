#!/usr/bin/env python3
"""Build NBA Chapter 2 packs: 3y player talent × minutes grid → rebased teams.

Sources: Basketball-Reference player Advanced (BPM) for 2023-24 / 2024-25 / 2025-26
(same concepts as NBA Stats Advanced; stats.nba.com timed out in build env).

Minute grid v0 = class grid (star / starter / bench), not 30 handwritten teams.
Offseason movers = one transaction map (no compose team-if).
"""

from __future__ import annotations

import html as htmlmod
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "services/model-service/src/services/nba_season_engine/data"
CH1_PATH = DATA / "nba_team_prior_2025_26_carry_2026_27.json"

SEASON_URLS = {
    "2023-24": "https://www.basketball-reference.com/leagues/NBA_2024_advanced.html",
    "2024-25": "https://www.basketball-reference.com/leagues/NBA_2025_advanced.html",
    "2025-26": "https://www.basketball-reference.com/leagues/NBA_2026_advanced.html",
}
WEIGHTS = {"2023-24": 0.20, "2024-25": 0.30, "2025-26": 0.50}
TEAM_CODES = {
    "ATL",
    "BOS",
    "BKN",
    "CHA",
    "CHI",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GSW",
    "HOU",
    "IND",
    "LAC",
    "LAL",
    "MEM",
    "MIA",
    "MIL",
    "MIN",
    "NOP",
    "NYK",
    "OKC",
    "ORL",
    "PHI",
    "PHX",
    "POR",
    "SAC",
    "SAS",
    "TOR",
    "UTA",
    "WAS",
}
BR_ALIAS = {"BRK": "BKN", "CHO": "CHA", "PHO": "PHX"}

# One transaction map — star / accompanying movers for 2026 offseason.
# Applied after 2025-26 primary team assignment. Not compose ifs.
TRANSACTIONS = [
    {"player_id": "jamesle01", "to_team": "PHI", "note": "FA: LeBron James → 76ers"},
    {"player_id": "antetgi01", "to_team": "MIA", "note": "Trade: Giannis Bucks → Heat"},
    {"player_id": "portibo01", "to_team": "MIA", "note": "Trade: Portis with Giannis → Heat"},
    {"player_id": "brownja02", "to_team": "PHI", "note": "Trade: Jaylen Brown Celtics → 76ers"},
    {"player_id": "georgpa01", "to_team": "BOS", "note": "Trade: Paul George in Brown deal → Celtics"},
    {"player_id": "leonaka01", "to_team": "TOR", "note": "Trade: Kawhi Clippers → Raptors"},
    {"player_id": "kesslwa01", "to_team": "LAL", "note": "S&T: Walker Kessler Jazz → Lakers"},
    {"player_id": "herroty01", "to_team": "MIL", "note": "Trade return: Herro Heat → Bucks"},
    {"player_id": "wareke01", "to_team": "MIL", "note": "Trade return: Ware Heat → Bucks"},
    {"player_id": "jaqueja01", "to_team": "MIL", "note": "Trade return: Jaquez Heat → Bucks"},
    {"player_id": "derozde01", "to_team": "DEN", "note": "FA: DeMar DeRozan → Nuggets"},
    {"player_id": "thompkl01", "to_team": "MIA", "note": "FA: Klay Thompson → Heat"},
]

STAR_MIN = 34.0  # class mid of 32–36
STARTER_MIN = 30.0  # class mid of 28–32
ROTATION_N = 9
RESIDUAL_CAP = 3.0
MIN_SEASON_MP = 100.0
UA = {"User-Agent": "Mozilla/5.0 (compatible; KosEdgeNbaCh2/1.0)"}


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", "replace").replace("<!--", "").replace("-->", "")


def parse_advanced(html: str, season: str) -> list[dict]:
    table = re.search(r'<table[^>]*id="advanced"[^>]*>.*?</table>', html, flags=re.S | re.I)
    if not table:
        raise SystemExit(f"missing advanced table for {season}")
    rows: list[dict] = []
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", table.group(0), flags=re.S | re.I):
        if 'data-stat="name_display"' not in tr:
            continue
        fields: dict[str, str] = {}
        m = re.search(r'data-append-csv="([^"]+)"', tr)
        if m:
            fields["player_id"] = m.group(1)
        for k, v in re.findall(
            r'<t[dh][^>]*data-stat="([^"]+)"[^>]*>(.*?)</t[dh]>', tr, flags=re.S | re.I
        ):
            fields[k] = htmlmod.unescape(re.sub(r"<[^>]+>", "", v)).strip()
        pid = fields.get("player_id")
        name = fields.get("name_display")
        if not pid or not name:
            continue
        team = BR_ALIAS.get(fields.get("team_name_abbr") or "", fields.get("team_name_abbr") or "")
        try:
            g = int(fields.get("games") or 0)
            mp = float(fields.get("mp") or 0)
            bpm = float(fields.get("bpm") or 0)
        except ValueError:
            continue
        rows.append(
            {
                "player_id": pid,
                "player_name": name,
                "team": team,
                "pos": fields.get("pos") or "",
                "g": g,
                "mp": mp,
                "bpm": bpm,
                "season": season,
            }
        )
    return rows


def season_player_row(rows_for_player: list[dict]) -> dict:
    tot = [r for r in rows_for_player if r["team"] == "TOT"]
    if tot:
        return tot[0]
    if len(rows_for_player) == 1:
        return rows_for_player[0]
    mp = sum(r["mp"] for r in rows_for_player) or 1.0
    bpm = sum(r["bpm"] * r["mp"] for r in rows_for_player) / mp
    base = max(rows_for_player, key=lambda r: r["mp"])
    return {**base, "bpm": bpm, "mp": mp, "g": sum(r["g"] for r in rows_for_player), "team": "MIX"}


def main() -> None:
    ch1 = json.loads(CH1_PATH.read_text(encoding="utf-8"))
    by_season: dict[str, list[dict]] = {}
    for season, url in SEASON_URLS.items():
        cache = Path(f"/tmp/nba_{season.replace('-', '_')}_advanced.html")
        # reuse year-coded caches from earlier fetch when present
        year = {"2023-24": 2024, "2024-25": 2025, "2025-26": 2026}[season]
        alt = Path(f"/tmp/nba_{year}_advanced.html")
        if alt.is_file():
            html = alt.read_text(encoding="utf-8", errors="replace").replace("<!--", "").replace("-->", "")
        elif cache.is_file():
            html = cache.read_text(encoding="utf-8", errors="replace")
        else:
            html = _get(url)
            cache.write_text(html, encoding="utf-8")
        by_season[season] = parse_advanced(html, season)

    players: dict[str, dict] = defaultdict(lambda: {"seasons": {}, "name": ""})
    for season, rows in by_season.items():
        by_p: dict[str, list] = defaultdict(list)
        for r in rows:
            by_p[r["player_id"]].append(r)
        for pid, plist in by_p.items():
            row = season_player_row(plist)
            players[pid]["name"] = row["player_name"]
            players[pid]["seasons"][season] = {
                "bpm": round(row["bpm"], 4),
                "mp": row["mp"],
                "g": row["g"],
                "team": row["team"],
                "pos": row["pos"],
            }

    roster_team: dict[str, str] = {}
    from_team_25: dict[str, str] = {}
    mp_by: dict[str, dict[str, float]] = defaultdict(dict)
    for r in by_season["2025-26"]:
        if r["team"] in TEAM_CODES:
            mp_by[r["player_id"]][r["team"]] = r["mp"]
    for pid, teams in mp_by.items():
        home = max(teams.items(), key=lambda kv: kv[1])[0]
        roster_team[pid] = home
        from_team_25[pid] = home

    tx_applied = []
    for tx in TRANSACTIONS:
        pid = tx["player_id"]
        if pid not in roster_team:
            continue
        fr = roster_team[pid]
        roster_team[pid] = tx["to_team"]
        tx_applied.append({**tx, "from_team": fr, "player_name": players[pid]["name"]})

    talent_pack_players = {}
    for pid, team in roster_team.items():
        num = den = 0.0
        detail = {}
        for season, w in WEIGHTS.items():
            row = players[pid]["seasons"].get(season)
            if not row or row["mp"] < MIN_SEASON_MP:
                continue
            num += w * float(row["bpm"])
            den += w
            detail[season] = row
        if den <= 0:
            continue
        talent_pack_players[pid] = {
            "player_id": pid,
            "player_name": players[pid]["name"],
            "team_2026_27": team,
            "team_2025_26": from_team_25.get(pid),
            "talent_bpm": round(num / den, 4),
            "weight_mass": round(den, 4),
            "seasons": detail,
        }

    grids: dict[str, list] = {}
    for team in sorted(TEAM_CODES):
        cands = []
        for pid, row in talent_pack_players.items():
            if row["team_2026_27"] != team:
                continue
            mp25 = float((row["seasons"].get("2025-26") or {}).get("mp") or 0)
            cands.append((pid, float(row["talent_bpm"]), mp25))
        cands.sort(key=lambda x: (-x[1], -x[2]))
        rot = cands[:ROTATION_N]
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
                    "talent_bpm": tal,
                }
            )
        assigned = sum(b["minutes"] for b in base)
        bench = [b for b in base if b["role"] == "bench"]
        remain = 240.0 - assigned
        if bench:
            each = remain / len(bench)
            for b in bench:
                b["minutes"] = each
        total = sum(b["minutes"] for b in base) or 1.0
        scale = 240.0 / total
        for b in base:
            b["minutes"] = round(b["minutes"] * scale, 4)
        # fix float drift on last bench/star
        drift = 240.0 - sum(b["minutes"] for b in base)
        if base:
            base[0]["minutes"] = round(base[0]["minutes"] + drift, 4)
        grids[team] = base

    rebased = {}
    for team in sorted(TEAM_CODES):
        grid = grids[team]
        player_net = sum(b["talent_bpm"] * b["minutes"] for b in grid) / 240.0
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
        }

    DATA.mkdir(parents=True, exist_ok=True)

    talent_out = {
        "engine_version": "nba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "metric": "bpm",
        "PLAYER_YEAR_WEIGHTS": WEIGHTS,
        "source": "basketball-reference.com leagues NBA_{2024,2025,2026}_advanced.html",
        "player_count": len(talent_pack_players),
        "players": talent_pack_players,
    }
    (DATA / "nba_player_talent_3y_2026.json").write_text(
        json.dumps(talent_out, indent=2) + "\n", encoding="utf-8"
    )

    tx_out = {
        "engine_version": "nba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "season": "2026-27",
        "note": "Single offseason transaction map applied after 2025-26 primary team. Not compose ifs.",
        "transactions": tx_applied,
    }
    (DATA / "nba_transactions_2026.json").write_text(
        json.dumps(tx_out, indent=2) + "\n", encoding="utf-8"
    )

    grid_out = {
        "engine_version": "nba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "season": "2026-27",
        "MINUTE_GRID_SUM": 240,
        "class_grid": {
            "star_minutes": STAR_MIN,
            "starter_minutes": STARTER_MIN,
            "rotation_n": ROTATION_N,
            "note": "star 32–36 mid=34; starter 28–32 mid=30; bench residual to 240",
        },
        "teams": {t: grids[t] for t in sorted(grids)},
    }
    (DATA / "nba_minutes_grid_2026.json").write_text(
        json.dumps(grid_out, indent=2) + "\n", encoding="utf-8"
    )

    rebase_out = {
        "engine_version": "nba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "carry_to_season": "2026-27",
        "TEAM_CARRY_SHRINK": ch1["TEAM_CARRY_SHRINK"],
        "TEAM_REBASE_RESIDUAL_CAP": RESIDUAL_CAP,
        "formula": (
            "player_net = Σ(talent_bpm × minutes) / 240; "
            "residual = clip(ch1_net - player_net, ±TEAM_REBASE_RESIDUAL_CAP); "
            "team_net = player_net + residual"
        ),
        "ch1_pack": str(CH1_PATH.name),
        "team_count": len(rebased),
        "league_mean_net": round(sum(r["net_rating"] for r in rebased.values()) / 30, 6),
        "implied_ppg_range": [
            min(r["implied_ppg"] for r in rebased.values()),
            max(r["implied_ppg"] for r in rebased.values()),
        ],
        "teams": rebased,
    }
    (DATA / "nba_team_prior_rebased_2026_27.json").write_text(
        json.dumps(rebase_out, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"wrote talent={len(talent_pack_players)} grids=30 rebased=30 "
        f"tx={len(tx_applied)} residual_cap={RESIDUAL_CAP}"
    )


if __name__ == "__main__":
    main()
