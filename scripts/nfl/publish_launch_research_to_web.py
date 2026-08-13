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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from services.nfl_canonical_teams import (  # noqa: E402
    CONFERENCE_OF,
    canonicalize_team,
    division_label,
)
from nfl_playoff_from_week_rates import (  # noqa: E402
    apply_playoff_probs_to_team_rows,
    recompute_playoff_probs,
)

# conference, division-label — product canonical Rams = LAR (LA alias only).
TEAM_META: Dict[str, Tuple[str, str]] = {
    t: (CONFERENCE_OF[t], division_label(t)) for t in CONFERENCE_OF
}


def _softmax(xs: List[float]) -> List[float]:
    if not xs:
        return []
    m = max(xs)
    ex = [math.exp(x - m) for x in xs]
    s = sum(ex) or 1.0
    return [e / s for e in ex]


def _run_invariant_gate(bundle_dir: Path) -> None:
    """Hard-fail publish when Truth Layer invariants fail."""
    script = ROOT / "scripts" / "nfl" / "check_nfl_invariants.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--bundle", str(bundle_dir)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise SystemExit(
            f"Truth Layer invariants failed for {bundle_dir} — publish blocked"
        )


def publish(source: Path, stamp: str | None, *, skip_gate: bool = False) -> Path:
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

    # Super Bowl soft proxy: league softmax of expected wins (research display only).
    # Playoff / division titles come from 7-seed MC (not P(wins>=9)).
    canon_teams: List[Dict[str, Any]] = []
    for row in teams:
        team = canonicalize_team(str(row["team"])) or str(row["team"])
        canon_teams.append({**row, "team": team})
    sb_weights = _softmax([float(r["mean"]) for r in canon_teams])
    sb_prob = {str(r["team"]): float(w) for r, w in zip(canon_teams, sb_weights)}

    week_rates_path = source / "team_week_win_rates.json"
    if not week_rates_path.exists():
        raise SystemExit(f"missing week win rates for playoff Truth Layer: {week_rates_path}")
    week_rates = json.loads(week_rates_path.read_text(encoding="utf-8"))
    playoff_recompute = recompute_playoff_probs(
        week_rates, n_replicates=20_000, seed=20260810, run_super_bowl=True
    )

    draft_rows: List[Dict[str, Any]] = []
    season = int(summary.get("season") or 2026)
    for row in sorted(canon_teams, key=lambda r: (-float(r["mean"]), str(r["team"]))):
        team = str(row["team"])
        conf, div = TEAM_META.get(team, ("UNK", "UNK"))
        draft_rows.append(
            {
                "season": season,
                "team": team,
                "conference": conf,
                "division": div,
                "expected_wins": round(float(row["mean"]), 4),
                "wins_p10": int(row.get("p10") or 0),
                "wins_p90": int(row.get("p90") or 0),
                "playoff_prob": 0.0,
                "division_title_prob": 0.0,
                # Placeholder; overwritten from path-bracket when available.
                "super_bowl_win_prob": round(sb_prob.get(team, 0.0), 6),
            }
        )
    team_rows = apply_playoff_probs_to_team_rows(
        draft_rows, playoff_recompute, rewrite_super_bowl=True
    )

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
        for row in sorted(
            team_rows, key=lambda r: (-float(r["expected_wins"]), str(r["team"]))
        ):
            w.writerow(
                [
                    row["season"],
                    row["team"],
                    row["conference"],
                    row["division"],
                    row["expected_wins"],
                    row["wins_p10"],
                    row["wins_p90"],
                    row["playoff_prob"],
                    row["division_title_prob"],
                    row["super_bowl_win_prob"],
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

    sum_afc = playoff_recompute["sanity"]["sum_playoff_afc"]
    sum_nfc = playoff_recompute["sanity"]["sum_playoff_nfc"]
    quality = {
        "source": "season_engine_launch_research",
        "engine_version": summary.get("engine_version"),
        "n_team_sims": summary.get("n_team_sims"),
        "n_player_sims": summary.get("n_player_sims"),
        "preseason": True,
        "kind": "Model",
        "honesty": {
            "playoff_prob": "7-seed MC from team_week_win_rates + wall-chart schedule",
            "division_title_prob": "division winner frequency from same 7-seed MC paths",
            "super_bowl_win_prob": (
                "path-record strength bracket on same 7-seed MC "
                "(fallback softmax(expected_wins) only if bracket disabled)"
            ),
            "playoff_player_totals": "empty — full player paths were regular-season only",
        },
        "source_bundle": str(source.relative_to(ROOT) if source.is_relative_to(ROOT) else source),
        "sanity": {
            "sum_super_bowl_prob": round(
                float(
                    (playoff_recompute.get("sanity") or {}).get("sum_super_bowl")
                    or sum(sb_prob.values())
                ),
                6,
            ),
            "sum_division_title_prob": playoff_recompute["sanity"]["sum_division_title"],
            "sum_playoff_prob": playoff_recompute["sanity"]["sum_playoff_league"],
            "sum_playoff_afc": sum_afc,
            "sum_playoff_nfc": sum_nfc,
            "sum_expected_wins": playoff_recompute["sanity"]["sum_expected_wins"],
        },
        "truth_layer": {
            "playoff_method": playoff_recompute["method"],
            "n_replicates": playoff_recompute["n_replicates"],
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
        "active_run_id": out_name,
        "bundle_id": out_name,
        "kind": "Model",
        "engine_version": summary.get("engine_version"),
        "n_team_sims": summary.get("n_team_sims"),
        "n_player_sims": summary.get("n_player_sims"),
        "generated_at_utc": generated,
        "source_dir": str(source.relative_to(ROOT) if source.is_relative_to(ROOT) else source),
        "preseason": True,
        "identity": f"{summary.get('engine_version')} · N_team={summary.get('n_team_sims')} · {stamp}",
        "team_id_scheme": "product_canonical_LAR",
        "lineage": {
            "run_id": out_name,
            "engine_version": summary.get("engine_version"),
            "generated_at": generated,
            "kind": "Model",
        },
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

    if not skip_gate:
        _run_invariant_gate(out_dir)
        from check_nfl_sot_qb_checksum import checksum as _sot_checksum

        chk = _sot_checksum(out_dir)
        pointer["sot_qb_checksum"] = chk
        (ROOT / "data" / "ops" / "nfl-web-launch-bundle.json").write_text(
            json.dumps(pointer, indent=2) + "\n", encoding="utf-8"
        )
        if not chk.get("ok"):
            raise SystemExit(
                "SoT QB checksum failed — publish blocked: " + "; ".join(chk.get("failed") or [])
            )

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
    ap.add_argument(
        "--skip-gate",
        action="store_true",
        help="Skip Truth Layer invariant gate (debug only)",
    )
    args = ap.parse_args()
    out = publish(args.source.resolve(), args.stamp, skip_gate=args.skip_gate)
    print(f"PUBLISHED {out}")
    print(f"POINTER data/ops/nfl-web-launch-bundle.json")


if __name__ == "__main__":
    main()
