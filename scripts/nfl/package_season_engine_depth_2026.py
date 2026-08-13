#!/usr/bin/env python3
"""Package latest nflverse 2026 skill depth into the season-engine artifact.

Reads ``depth_charts_2026.parquet`` (local path or download URL) and writes
``services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json``.

Usage:
  python scripts/nfl/package_season_engine_depth_2026.py \\
      --parquet /tmp/nfl_depth/depth_charts_2026.parquet

  python scripts/nfl/package_season_engine_depth_2026.py --download
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = (
    REPO_ROOT
    / "services/model-service/src/services/nfl_season_engine/data"
    / "nfl_depth_chart_2026_w1.json"
)
DEFAULT_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "depth_charts/depth_charts_2026.parquet"
)
SKILL = ("QB", "RB", "WR", "TE")
TEAM_MAP = {"LAR": "LA"}

# Enterprise depth SoT overrides applied after nflverse packaging.
# Depth/roster changes update this map + the JSON pack — never engine hardcodes.
SOT_QB_OVERRIDES: dict[str, list[tuple[str, str]]] = {
    # team -> [(depth_order, player_name), ...]
    "ARI": [(1, "Jacoby Brissett"), (2, "Gardner Minshew II"), (3, "Carson Beck")],
    "MIN": [(1, "Kyler Murray"), (2, "J.J. McCarthy"), (3, "Carson Wentz")],
    # Tua signed ATL; Penix still in the room (open_competition). Willis is MIA QB1.
    "ATL": [(1, "Tua Tagovailoa"), (2, "Michael Penix Jr.")],
    "MIA": [(1, "Malik Willis")],
}

# Non-QB skill SoT overlays (camp / FA landings). Applied after QB overrides.
# Format: team -> position -> [(depth_order, player_name, player_id|""), ...]
SOT_SKILL_OVERRIDES: dict[str, dict[str, list[tuple[int, str, str]]]] = {
    "WAS": {
        "WR": [
            (1, "Terry McLaurin", "00-0035659"),
            (2, "Stefon Diggs", "00-0031588"),
            (3, "Antonio Williams", "00-0041040"),
        ],
        "TE": [
            (1, "Chig Okonkwo", "00-0037809"),
            (2, "Ben Sinnott", "00-0039912"),
            (3, "John Bates", "00-0036628"),
        ],
    },
}


def _load_frame(parquet_path: Path):
    try:
        import polars as pl
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("polars is required to package depth charts") from exc
    return pl.read_parquet(str(parquet_path))


def _apply_sot_qb_overrides(rows: list[dict]) -> list[dict]:
    """Enforce enterprise QB depth SoT after raw nflverse packaging."""
    by_name = {
        str(r.get("player_name") or "").strip(): r for r in rows if r.get("player_name")
    }
    # Drop overridden QB slots; reinsert SoT identities (preserve player_id when known).
    drop_keys: set[tuple[str, int]] = set()
    for team, slots in SOT_QB_OVERRIDES.items():
        for depth, _name in slots:
            drop_keys.add((team, int(depth)))
    # Also remove SoT QBs from any other team slot so they aren't duplicated.
    sot_names = {name for slots in SOT_QB_OVERRIDES.values() for _, name in slots}
    kept: list[dict] = []
    for r in rows:
        if str(r.get("position") or "") != "QB":
            kept.append(r)
            continue
        team = str(r.get("team") or "")
        depth = int(r.get("depth_order") or 0)
        name = str(r.get("player_name") or "").strip()
        if (team, depth) in drop_keys or name in sot_names:
            continue
        kept.append(r)
    for team, slots in SOT_QB_OVERRIDES.items():
        for depth, name in slots:
            prior = by_name.get(name) or {}
            kept.append(
                {
                    "team": team,
                    "position": "QB",
                    "depth_order": int(depth),
                    "player_id": str(prior.get("player_id") or f"{team}-QB-{depth}"),
                    "player_name": name,
                    "depth_slot": {1: "starter", 2: "backup", 3: "rotation"}.get(
                        int(depth), "depth"
                    ),
                    "role_confidence": 0.85
                    if int(depth) == 1
                    else (0.65 if int(depth) == 2 else 0.5),
                }
            )
    kept.sort(key=lambda r: (r["team"], r["position"], int(r["depth_order"])))
    return kept


def _apply_sot_skill_overrides(rows: list[dict]) -> list[dict]:
    """Enforce non-QB skill depth SoT (camp/FA) after nflverse packaging."""
    by_name = {
        str(r.get("player_name") or "").strip(): r for r in rows if r.get("player_name")
    }
    drop_keys: set[tuple[str, str, int]] = set()
    sot_names: set[str] = set()
    for team, by_pos in SOT_SKILL_OVERRIDES.items():
        for pos, slots in by_pos.items():
            for depth, name, _pid in slots:
                drop_keys.add((team, pos, int(depth)))
                sot_names.add(name)
    kept: list[dict] = []
    for r in rows:
        team = str(r.get("team") or "")
        pos = str(r.get("position") or "")
        depth = int(r.get("depth_order") or 0)
        name = str(r.get("player_name") or "").strip()
        if pos == "QB":
            kept.append(r)
            continue
        if (team, pos, depth) in drop_keys:
            continue
        if name in sot_names and pos in {
            p for tp in SOT_SKILL_OVERRIDES.values() for p in tp
        }:
            # Drop SoT names from any competing slot/team at that position.
            continue
        kept.append(r)
    for team, by_pos in SOT_SKILL_OVERRIDES.items():
        for pos, slots in by_pos.items():
            for depth, name, pid in slots:
                prior = by_name.get(name) or {}
                kept.append(
                    {
                        "team": team,
                        "position": pos,
                        "depth_order": int(depth),
                        "player_id": str(
                            pid or prior.get("player_id") or f"{team}-{pos}-{depth}"
                        ),
                        "player_name": name,
                        "depth_slot": {1: "starter", 2: "backup", 3: "rotation"}.get(
                            int(depth), "depth"
                        ),
                        "role_confidence": 0.85
                        if int(depth) == 1
                        else (0.65 if int(depth) == 2 else 0.5),
                    }
                )
    kept.sort(key=lambda r: (r["team"], r["position"], int(r["depth_order"])))
    return kept


def package(*, parquet_path: Path, out_path: Path, upstream_last_updated: str = "") -> dict:
    import polars as pl

    df = _load_frame(parquet_path)
    latest_dt = df.select(pl.col("dt").cast(pl.Utf8).max()).item()
    latest = df.filter(pl.col("dt").cast(pl.Utf8) == latest_dt)
    skill = latest.filter(pl.col("pos_abb").is_in(list(SKILL)))

    rows_out = []
    seen: set[tuple[str, str, int]] = set()
    for row in skill.sort(["team", "pos_abb", "pos_rank"]).iter_rows(named=True):
        team = TEAM_MAP.get(str(row["team"]).upper(), str(row["team"]).upper())
        pos = str(row["pos_abb"])
        rank = int(row["pos_rank"] or 0)
        name = str(row["player_name"] or "").strip()
        if rank < 1 or rank > 3 or not name:
            continue
        key = (team, pos, rank)
        if key in seen:
            continue
        seen.add(key)
        player_id = str(row.get("gsis_id") or row.get("espn_id") or "").strip()
        rows_out.append(
            {
                "team": team,
                "position": pos,
                "depth_order": rank,
                "player_id": player_id or f"{team}-{pos}-{rank}",
                "player_name": name,
                "depth_slot": {1: "starter", 2: "backup", 3: "rotation"}.get(rank, "depth"),
                "role_confidence": 0.85 if rank == 1 else (0.65 if rank == 2 else 0.5),
            }
        )

    rows_out = _apply_sot_qb_overrides(rows_out)
    rows_out = _apply_sot_skill_overrides(rows_out)

    teams = {r["team"] for r in rows_out}
    full = 0
    for team in teams:
        has = {(r["position"], r["depth_order"]) for r in rows_out if r["team"] == team}
        if all((p, 1) in has for p in SKILL):
            full += 1

    payload = {
        "season": 2026,
        "week": 1,
        "source": "packaged_nflverse_depth_2026",
        "upstream": "nflverse/nflverse-data depth_charts release",
        "upstream_url": DEFAULT_URL,
        "as_of": str(latest_dt)[:10],
        "as_of_timestamp": latest_dt,
        "upstream_last_updated": upstream_last_updated or "",
        "positions": list(SKILL),
        "max_depth_order": 3,
        "team_count": len(teams),
        "row_count": len(rows_out),
        "full_skill_starter_teams": full,
        "notes": [
            "Skill-position slice (QB/RB/WR/TE) from latest nflverse depth-chart snapshot.",
            "Preseason/camp depth — roles can shift; rookies and free-agent landings may be incomplete or volatile.",
            "AUTHORITATIVE player-to-team SoT for the season engine and intel depth/roster surfaces.",
            "DB weekly/official must not override these identities when this pack is present.",
            "QB SoT overrides applied post-nflverse: Kyler→MIN1, Brissett→ARI1, Penix→ATL1, Tua→MIA1.",
            "Skill SoT overlays (SOT_SKILL_OVERRIDES) preserve camp/FA landings (e.g. WAS Diggs/Bates).",
        ],
        "rows": rows_out,
    }
    # Preserve daily intel sections from an existing pack so re-packaging
    # nflverse rows does not wipe ol_roles / camp_intel / injury_paths.
    if out_path.is_file():
        try:
            prior = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior = {}
        for key in (
            "daily_intel_as_of",
            "ol_roles",
            "camp_intel",
            "injury_paths",
        ):
            if key in prior and prior.get(key) not in (None, "", [], {}):
                payload[key] = prior[key]
        # Carry forward injury_* fields on matching SoT skill identities.
        prior_by_key = {
            (
                str(r.get("team") or ""),
                str(r.get("position") or ""),
                int(r.get("depth_order") or 0),
                str(r.get("player_name") or "").strip(),
            ): r
            for r in (prior.get("rows") or [])
            if isinstance(r, dict)
        }
        for r in payload["rows"]:
            key = (
                str(r.get("team") or ""),
                str(r.get("position") or ""),
                int(r.get("depth_order") or 0),
                str(r.get("player_name") or "").strip(),
            )
            prev = prior_by_key.get(key) or {}
            for ik in (
                "injury_status",
                "injury_window",
                "injury_note",
                "injury_sources",
            ):
                if ik in prev and prev.get(ik) not in (None, ""):
                    r[ik] = prev[ik]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    pos_counts = Counter(r["position"] for r in rows_out)
    print(
        json.dumps(
            {
                "out": str(out_path),
                "teams": len(teams),
                "rows": len(rows_out),
                "full_skill_starter_teams": full,
                "as_of": payload["as_of"],
                "pos_counts": dict(pos_counts),
            },
            indent=2,
        )
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, help="Local depth_charts_2026.parquet")
    parser.add_argument(
        "--download",
        action="store_true",
        help=f"Download from {DEFAULT_URL}",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--timestamp-json",
        type=Path,
        help="Optional nflverse timestamp.json for upstream_last_updated",
    )
    args = parser.parse_args(argv)

    parquet = args.parquet
    if args.download:
        parquet = Path("/tmp/nfl_depth_charts_2026.parquet")
        parquet.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {DEFAULT_URL} -> {parquet}", file=sys.stderr)
        urllib.request.urlretrieve(DEFAULT_URL, parquet)
    if parquet is None or not parquet.is_file():
        raise SystemExit("Provide --parquet PATH or --download")

    upstream_last_updated = ""
    if args.timestamp_json and args.timestamp_json.is_file():
        try:
            upstream_last_updated = str(
                json.loads(args.timestamp_json.read_text(encoding="utf-8")).get(
                    "last_updated"
                )
                or ""
            )
        except json.JSONDecodeError:
            upstream_last_updated = ""

    package(
        parquet_path=parquet,
        out_path=args.out,
        upstream_last_updated=upstream_last_updated,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
