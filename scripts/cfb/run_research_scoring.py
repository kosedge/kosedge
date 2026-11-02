#!/usr/bin/env python3
"""Research-only CFB efficiency → scoring (points → margin/total).

Protocol (locked before knobs): docs/cfb/EVAL_PROTOCOL.md

  PYTHONPATH=services/model-service python3 scripts/cfb/run_research_scoring.py \\
      --as-of 20260915 --write-ops

Does not retune #560 EPA knobs. production_promote=false. No board reopen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _load_or_build(hist: Path, seasons: tuple[int, ...]):
    from src.services.cfb_warehouse.research_hist_features import (
        load_restored_epa_games,
        load_season_frame,
        rows_to_team_game_epa,
    )
    from src.services.cfb_warehouse.research_opp_adj import aggregate_team_game_epa
    from src.services.cfb_warehouse.research_scoring import (
        extract_official_scores,
        extract_team_pace,
    )

    epa_rows = load_restored_epa_games(hist)
    if epa_rows:
        games = rows_to_team_game_epa(epa_rows)
    else:
        games = []
        for season in seasons:
            raw = hist / f"play_by_play_{int(season)}.parquet"
            if not raw.exists():
                continue
            df = load_season_frame(raw)
            recs = df.to_dict(orient="records")
            for rec in recs:
                gid = rec.get("game_id")
                if gid is not None:
                    rec["game_id"] = str(gid).split(".")[0]
            games.extend(aggregate_team_game_epa(recs))

    scores = {}
    pace = {}
    extra_cols = (
        "season",
        "week",
        "game_id",
        "pos_team",
        "def_pos_team",
        "homeTeamName",
        "awayTeamName",
        "homeTeamAbbrev",
        "awayTeamAbbrev",
        "home",
        "away",
        "neutral",
        "neutral_site",
        "end.homeScore",
        "end.awayScore",
        "homeScore",
        "awayScore",
        "period",
        "qtr",
        "scrimmage_play",
        "pass",
        "rush",
        "pos_score_diff",
        "drive.id",
        "drive_id",
        "EPA",
    )
    for season in seasons:
        raw = hist / f"play_by_play_{int(season)}.parquet"
        if not raw.exists():
            continue
        df = load_season_frame(raw, columns=extra_cols)
        recs = df.to_dict(orient="records")
        for rec in recs:
            gid = rec.get("game_id")
            if gid is not None:
                rec["game_id"] = str(gid).split(".")[0]
        scores.update(extract_official_scores(recs))
        pace.update(extract_team_pace(recs))
    return games, scores, pace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default="20260915")
    parser.add_argument("--write-ops", action="store_true")
    parser.add_argument("--hist-dir", default="")
    parser.add_argument("--seasons", default="2014-2025")
    args = parser.parse_args(argv)

    from src.services.cfb_warehouse.paths import REPO_ROOT, pbp_hist_research_dir
    from src.services.cfb_warehouse.research_scoring_validate import run_scoring_suite

    as_of = "".join(ch for ch in args.as_of if ch.isdigit())[:8]
    start, end = (int(x) for x in args.seasons.split("-"))
    seasons = tuple(s for s in range(start, end + 1))
    hist = Path(args.hist_dir) if args.hist_dir else pbp_hist_research_dir(as_of)

    print(f"== scoring inputs from {hist} ==", flush=True)
    epa_games, scores, pace = _load_or_build(hist, seasons)
    if not epa_games:
        raise SystemExit(f"no EPA team-games at {hist}")
    if not scores:
        raise SystemExit(f"no official scores extracted at {hist}")
    print(
        f"epa_games={len(epa_games)} scored_games={len(scores)} pace_rows={len(pace)}",
        flush=True,
    )

    print("== fit train / select 2023 / seal 2024 W>=10 ==", flush=True)
    report = run_scoring_suite(epa_games=epa_games, scores=scores, pace_rows=pace)
    rec = report["recommendation"]
    print(
        f"selected={report['selection']['selected']} "
        f"confirm_n={rec.get('n')} call={rec.get('recommendation')} "
        f"promote={rec.get('production_promote')} "
        f"h_pts={report['hfa']['h_pts']}",
        flush=True,
    )

    dest = REPO_ROOT / "data" / "ops" / f"cfb-research-eff-scoring-{as_of}"
    if args.write_ops:
        dest.mkdir(parents=True, exist_ok=True)
        _write(dest / "scoring_validation_report.json", report)
        summary = {
            "pipeline_version": report["pipeline_version"],
            "research_only": True,
            "production_promote": False,
            "as_of": as_of,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "protocol": report["protocol"],
            "recommendation": rec,
            "selected": report["selection"]["selected"],
            "h_pts": report["hfa"]["h_pts"],
            "h_prior": report["hfa"]["h_prior"],
            "h_window": report["hfa"]["h_window"],
            "hfa_k": report["hfa"]["hfa_k"],
            "pace_source": report["pace"]["source_selected"],
            "ppp": report["pace"]["ppp"],
            "confirmation_n": rec.get("n"),
            "boards_stay_coming_soon": True,
            "production_sp_plus_unchanged": True,
            "production_kei_unchanged": True,
        }
        _write(dest / "scoring_summary.json", summary)
        checksums = {
            name: {
                "sha256": _sha256(dest / name),
                "bytes": (dest / name).stat().st_size,
            }
            for name in (
                "scoring_validation_report.json",
                "scoring_summary.json",
            )
            if (dest / name).exists()
        }
        _write(dest / "scoring_checksums.json", checksums)
        print(f"ops written → {dest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
