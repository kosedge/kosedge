#!/usr/bin/env python3
"""Publish season-engine launch research JSON → web preseason CSV bundle.

Creates ``data/ops/nfl-preseason-sim-2026-<stamp>/`` so power ratings, fantasy,
and projection desks pick up the 100k launch-current numbers via existing
``nfl-preseason-artifacts`` loaders.

Does not touch Edge Board / Railway request-path sim caps.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]

# conference, division-label (matches older team_regular_season_outcomes.csv)
TEAM_META: Dict[str, Tuple[str, str]] = {
    "ARI": ("NFC", "NFC West"),
    "ATL": ("NFC", "NFC South"),
    "BAL": ("AFC", "AFC North"),
    "BUF": ("AFC", "AFC East"),
    "CAR": ("NFC", "NFC South"),
    "CHI": ("NFC", "NFC North"),
    "CIN": ("AFC", "AFC North"),
    "CLE": ("AFC", "AFC North"),
    "DAL": ("NFC", "NFC East"),
    "DEN": ("AFC", "AFC West"),
    "DET": ("NFC", "NFC North"),
    "GB": ("NFC", "NFC North"),
    "HOU": ("AFC", "AFC South"),
    "IND": ("AFC", "AFC South"),
    "JAX": ("AFC", "AFC South"),
    "KC": ("AFC", "AFC West"),
    "LA": ("NFC", "NFC West"),
    "LAC": ("AFC", "AFC West"),
    "LAR": ("NFC", "NFC West"),
    "LV": ("AFC", "AFC West"),
    "MIA": ("AFC", "AFC East"),
    "MIN": ("NFC", "NFC North"),
    "NE": ("AFC", "AFC East"),
    "NO": ("NFC", "NFC South"),
    "NYG": ("NFC", "NFC East"),
    "NYJ": ("AFC", "AFC East"),
    "PHI": ("NFC", "NFC East"),
    "PIT": ("AFC", "AFC North"),
    "SEA": ("NFC", "NFC West"),
    "SF": ("NFC", "NFC West"),
    "TB": ("NFC", "NFC South"),
    "TEN": ("AFC", "AFC South"),
    "WAS": ("NFC", "NFC East"),
    "WSH": ("NFC", "NFC East"),
}


def _softmax(xs: List[float]) -> List[float]:
    if not xs:
        return []
    m = max(xs)
    ex = [math.exp(x - m) for x in xs]
    s = sum(ex) or 1.0
    return [e / s for e in ex]


def _playoff_prob(hist: Dict[str, int], n: int, cutoff: int = 9) -> float:
    if n <= 0:
        return 0.0
    return sum(int(hist.get(str(w), 0)) for w in range(cutoff, 18)) / float(n)


def publish(source: Path, stamp: str | None) -> Path:
    summary = json.loads((source / "run_summary.json").read_text(encoding="utf-8"))
    teams = json.loads((source / "team_win_distributions.json").read_text(encoding="utf-8"))
    players = []
    player_path = source / "player_season_totals.json"
    if player_path.exists():
        players = json.loads(player_path.read_text(encoding="utf-8"))

    generated = summary.get("generated_at_utc") or datetime.now(timezone.utc).isoformat()
    if not stamp:
        # Prefer ISO compact from generated_at
        raw = str(generated).replace("-", "").replace(":", "").replace("+00:00", "Z")
        if "T" in raw:
            stamp = raw.split(".")[0]
            if not stamp.endswith("Z"):
                stamp = stamp + "Z"
        else:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    out_name = f"nfl-preseason-sim-2026-{stamp}"
    out_dir = ROOT / "data" / "ops" / out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Division-title soft proxy: softmax of expected wins within division
    by_div: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in teams:
        team = str(row["team"])
        conf, div = TEAM_META.get(team, ("UNK", "UNK"))
        by_div[div].append(row)

    div_title: Dict[str, float] = {}
    for div, rows in by_div.items():
        weights = _softmax([float(r["mean"]) for r in rows])
        for r, w in zip(rows, weights):
            div_title[str(r["team"])] = float(w)

    # Super Bowl soft proxy: league softmax of expected wins (research display only)
    sb_weights = _softmax([float(r["mean"]) for r in teams])
    sb_prob = {str(r["team"]): float(w) for r, w in zip(teams, sb_weights)}

    team_csv = out_dir / "team_regular_season_outcomes.csv"
    with team_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "season",
                "team",
                "conference",
                "division",
                "expected_wins",
                "wins_p10",
                "wins_p90",
                "playoff_prob",
                "division_title_prob",
                "super_bowl_win_prob",
            ]
        )
        season = int(summary.get("season") or 2026)
        for row in sorted(teams, key=lambda r: (-float(r["mean"]), str(r["team"]))):
            team = str(row["team"])
            conf, div = TEAM_META.get(team, ("UNK", "UNK"))
            n = int(row.get("n_sims") or 0)
            hist = row.get("win_histogram") or {}
            w.writerow(
                [
                    season,
                    team,
                    conf,
                    div,
                    round(float(row["mean"]), 4),
                    int(row.get("p10") or 0),
                    int(row.get("p90") or 0),
                    round(_playoff_prob(hist, n), 6),
                    round(div_title.get(team, 0.0), 6),
                    round(sb_prob.get(team, 0.0), 6),
                ]
            )

    # Copy win distributions for desks that want full hist
    shutil.copy2(source / "team_win_distributions.json", out_dir / "team_win_distributions.json")
    shutil.copy2(source / "team_week_win_rates.json", out_dir / "team_week_win_rates.json")
    if (source / "survivor_week1_evaluate.json").exists():
        shutil.copy2(
            source / "survivor_week1_evaluate.json",
            out_dir / "survivor_week1_evaluate.json",
        )

    reg_csv = out_dir / "player_regular_season_totals.csv"
    playoff_csv = out_dir / "player_playoff_totals.csv"
    headers = [
        "season",
        "player_key",
        "player_name",
        "team",
        "position",
        "games_projected",
        "pass_yards_total",
        "rush_yards_total",
        "receiving_yards_total",
        "receptions_total",
        "pass_tds_total",
        "rush_tds_total",
        "rec_tds_total",
        "anytime_td_prob",
    ]
    season = int(summary.get("season") or 2026)
    with reg_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for p in players:
            rush_td = float(p.get("rush_tds_mean") or 0)
            rec_td = float(p.get("rec_tds_mean") or 0)
            anytime = min(0.9999, max(0.0, 1.0 - math.exp(-(rush_td + rec_td))))
            w.writerow(
                [
                    season,
                    p.get("player_key") or "",
                    p.get("player_name") or "Unknown",
                    p.get("team") or "UNK",
                    p.get("position") or "UNK",
                    int(round(float(p.get("games_mean") or 0))),
                    round(float(p.get("pass_yards_mean") or 0), 3),
                    round(float(p.get("rush_yards_mean") or 0), 3),
                    round(float(p.get("rec_yards_mean") or 0), 3),
                    round(float(p.get("receptions_mean") or 0), 3),
                    round(float(p.get("pass_tds_mean") or 0), 3),
                    round(rush_td, 3),
                    round(rec_td, 3),
                    round(anytime, 4),
                ]
            )

    # Honest empty playoff totals (research bundle did not run playoff bracket paths)
    with playoff_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(headers)

    quality = {
        "source": "season_engine_launch_research",
        "engine_version": summary.get("engine_version"),
        "n_team_sims": summary.get("n_team_sims"),
        "n_player_sims": summary.get("n_player_sims"),
        "preseason": True,
        "honesty": {
            "playoff_prob": "P(wins>=9) from 100k team W/L win_histogram",
            "division_title_prob": "softmax(expected_wins) within division (display proxy)",
            "super_bowl_win_prob": "softmax(expected_wins) league-wide (display proxy; not bracket sims)",
            "playoff_player_totals": "empty — full player paths were regular-season only",
        },
        "source_bundle": str(source.relative_to(ROOT) if source.is_relative_to(ROOT) else source),
        "sanity": {
            "sum_super_bowl_prob": round(sum(sb_prob.values()), 6),
            "sum_division_title_prob": round(sum(div_title.values()), 6),
            "sum_playoff_prob": None,
        },
    }
    (out_dir / "quality_checks.json").write_text(
        json.dumps(quality, indent=2) + "\n", encoding="utf-8"
    )

    web_summary = {
        **summary,
        "web_bundle_id": out_name,
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "label": "launch_current_web_preseason_bundle",
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(web_summary, indent=2, default=str) + "\n", encoding="utf-8"
    )

    pointer = {
        "bundle_id": out_name,
        "engine_version": summary.get("engine_version"),
        "n_team_sims": summary.get("n_team_sims"),
        "n_player_sims": summary.get("n_player_sims"),
        "generated_at_utc": generated,
        "source_dir": str(source.relative_to(ROOT) if source.is_relative_to(ROOT) else source),
        "preseason": True,
        "identity": f"{summary.get('engine_version')} · N_team={summary.get('n_team_sims')} · {stamp}",
    }
    (ROOT / "data" / "ops" / "nfl-web-launch-bundle.json").write_text(
        json.dumps(pointer, indent=2) + "\n", encoding="utf-8"
    )

    # Keep markdown pointer in sync
    (ROOT / "data" / "ops" / "nfl-launch-research-sims-current.md").write_text(
        "\n".join(
            [
                "# NFL launch research sims — current pointer",
                "",
                f"- **Web bundle:** `{out_name}`",
                f"- **Source research:** `{pointer['source_dir']}`",
                f"- **Engine:** `{pointer['engine_version']}`",
                f"- **Team W/L N:** {pointer['n_team_sims']}",
                f"- **Player full N:** {pointer['n_player_sims']}",
                f"- **Generated:** {generated}",
                f"- **Identity:** {pointer['identity']}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # HD mirror if present
    hd = Path("/Volumes/KosEdgeData/clean/nfl/research")
    if hd.is_dir():
        hd_out = hd / out_name
        if hd_out.exists():
            shutil.rmtree(hd_out)
        shutil.copytree(out_dir, hd_out)

    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source",
        type=Path,
        default=ROOT
        / "data/ops/nfl-season-engine-launch-nfl-season-engine-v1.12-survivor-planner-ux-Nteam100000-Nplayer1000-20260807T172531Z",
    )
    ap.add_argument("--stamp", default=None, help="Override nfl-preseason-sim-2026-<stamp>")
    args = ap.parse_args()
    out = publish(args.source.resolve(), args.stamp)
    print(f"PUBLISHED {out}")
    print(f"POINTER data/ops/nfl-web-launch-bundle.json")


if __name__ == "__main__":
    main()
