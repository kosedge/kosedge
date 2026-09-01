#!/usr/bin/env python3
"""WNBA grading harness — freeze desk publications, grade after tip.

Infrastructure only. Does not rewrite KEI, projections, props packs, or tags.
Same shape as scripts/nba/grade_harness.py (basketball row contract).

Usage:
  python3 scripts/wnba/grade_harness.py seed
  python3 scripts/wnba/grade_harness.py summary
  python3 scripts/wnba/grade_harness.py status
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "wnba_grades_2026.jsonl"
SCHEMA = ROOT / "docs" / "WNBA_GRADE_SCHEMA.md"
SUMMARY_MD = ROOT / "data" / "ops" / "wnba-grades-summary-2026.md"
SUMMARY_JSON = ROOT / "data" / "ops" / "wnba-grades-summary-2026.json"

# Packs that must stay untouched (read-only fingerprint targets for tests).
KEI_PACK = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "wnba_season_engine"
    / "data"
    / "wnba_kei_lines_ch4.json"
)
PROJ_PACK = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "wnba_season_engine"
    / "data"
    / "wnba_player_projection_2026.json"
)
PROPS_MODULE = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "wnba_season_engine"
    / "wnba_props.py"
)

SEASON = 2026
STAMP_FROZEN = "v0.1 · Ch2–Ch7"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_rows(path: Path = STORE) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _append_rows(rows: Iterable[Dict[str, Any]], path: Path = STORE) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


def _row_key(r: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        r.get("season"),
        r.get("date"),
        r.get("game_id"),
        r.get("player_id"),
        r.get("market"),
    )


def _base_row(**kwargs: Any) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "season": SEASON,
        "date": None,
        "game_id": None,
        "player_id": None,
        "market": None,
        "kei": None,
        "proj": None,
        "open": None,
        "best_kick": None,
        "book": None,
        "trusted": None,
        "tag": None,
        "size_note": None,
        "close": None,
        "final": None,
        "ats_vs_kei": None,
        "ats_vs_tag": None,
        "clv": None,
        "signed_error": None,
        "source": None,
        "recorded_at": _utc_now(),
    }
    row.update(kwargs)
    return row


def build_schema_example_rows() -> List[Dict[str, Any]]:
    """Illustrative rows only — not a real slate. close/final stay null."""
    # Deterministic recorded_at so seed is stable under --force.
    stamped = "2026-09-01T00:00:00Z"
    common = dict(
        season=SEASON,
        date="2026-09-20",
        game_id="schema-ex-con-atl-20260920",
        source="schema_example",
        recorded_at=stamped,
        close=None,
        final=None,
        ats_vs_kei=None,
        ats_vs_tag=None,
        clv=None,
        signed_error=None,
        size_note=None,
    )

    # Team rows shaped like Ch4 CON@ATL (home-signed); illustrative only.
    spread = _base_row(
        **common,
        player_id=None,
        market="spread",
        kei=-8.5,
        proj=None,
        open=-8.5,
        best_kick=-8.5,
        book="FanDuel",
        trusted=True,
        tag="PASS",
    )
    total = _base_row(
        **common,
        player_id=None,
        market="total",
        kei=162.5,
        proj=None,
        open=162.5,
        best_kick=163.0,
        book="DraftKings",
        trusted=True,
        tag="PASS",
    )
    # Props: Ch5 proj + Ch6 Best; Odds-backed only; tag stays n/a (no tag PR).
    prop_pts = _base_row(
        **common,
        player_id="schema-ex-player-001",
        market="pts",
        kei=None,
        proj=19.5,
        open=18.5,
        best_kick=18.5,
        book="FanDuel",
        trusted=True,
        tag="n/a",
    )
    prop_threes = _base_row(
        **common,
        player_id="schema-ex-player-001",
        market="threes",
        kei=None,
        proj=1.6,
        open=1.5,
        best_kick=1.5,
        book="DraftKings",
        trusted=True,
        tag="n/a",
    )
    return [spread, total, prop_pts, prop_threes]


def cmd_seed(*, force: bool = False) -> int:
    if not SCHEMA.exists():
        print(f"missing schema: {SCHEMA}", file=sys.stderr)
        return 2
    if STORE.exists() and STORE.stat().st_size > 0 and not force:
        print(f"store already seeded: {STORE} ({STORE.stat().st_size} bytes)")
        print(
            "re-run with --force to wipe and reseed "
            "(append-only contract: prefer not to)"
        )
        return 0

    if force and STORE.exists():
        STORE.unlink()

    # Checklist step 1: empty store.
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text("", encoding="utf-8")

    examples = build_schema_example_rows()
    n = _append_rows(examples)
    rows = _read_rows()
    print("=== WNBA grade harness seed ===")
    print(f"stamp:   {STAMP_FROZEN}")
    print(f"schema:  {SCHEMA}")
    print(f"store:   {STORE}")
    print(f"example rows: {n} (spread + total + pts + threes)")
    print(f"total:   {len(rows)}")
    assert all(r.get("close") is None and r.get("final") is None for r in rows)
    assert all(
        r.get("source") == "schema_example" for r in rows
    ), "first fill is schema examples only"
    props = [r for r in rows if r.get("player_id")]
    assert props and all(r.get("tag") == "n/a" for r in props)
    assert all(r.get("kei") is None and r.get("proj") is not None for r in props)
    teams = [r for r in rows if r.get("player_id") is None]
    assert all(r.get("proj") is None and r.get("kei") is not None for r in teams)
    print("close/final empty on purpose. KEI/proj/props packs untouched.")
    return 0


def cmd_summary() -> int:
    rows = _read_rows()
    errors = [
        float(r["signed_error"])
        for r in rows
        if r.get("signed_error") is not None
    ]
    graded = [r for r in rows if r.get("final") is not None]
    by_market = Counter(r.get("market") for r in rows)
    by_source = Counter(r.get("source") for r in rows)
    by_tag = Counter(r.get("tag") for r in rows)

    summary = {
        "as_of": _utc_now(),
        "stamp_frozen": STAMP_FROZEN,
        "store": str(STORE.relative_to(ROOT)),
        "n_rows": len(rows),
        "n_graded_final": len(graded),
        "n_signed_error": len(errors),
        "mean_signed_error": (sum(errors) / len(errors)) if errors else None,
        "by_market": dict(by_market),
        "by_source": dict(by_source),
        "by_tag": dict(by_tag),
        "note": (
            "Schema example seed only. Regular-season/playoff close/final empty until tip. "
            "mean_signed_error stays null until games are graded. Props tags stay n/a."
        ),
    }

    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    mean = summary["mean_signed_error"]
    mean_s = "null (empty until games)" if mean is None else f"{mean}"
    lines = [
        "# WNBA grades summary (read-only)",
        "",
        f"**as_of:** `{summary['as_of']}`  ",
        f"**stamp frozen:** `{summary['stamp_frozen']}`  ",
        f"**store:** `{summary['store']}`  ",
        f"**n_rows:** {summary['n_rows']}  ",
        f"**n_graded_final:** {summary['n_graded_final']}  ",
        f"**mean_signed_error:** {mean_s} (n={summary['n_signed_error']})",
        "",
        "## Counts",
        "",
        f"- by market: `{summary['by_market']}`",
        f"- by source: `{summary['by_source']}`",
        f"- by tag: `{summary['by_tag']}`",
        "",
        summary["note"],
        "",
        "Ch4/Ch5/Ch6 packs unchanged. Fantasy Ch5-only. No publisher. No props PLAY.",
        "",
    ]
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(SUMMARY_MD.read_text(encoding="utf-8"))
    print(f"wrote {SUMMARY_MD}")
    print(f"wrote {SUMMARY_JSON}")
    return 0


def cmd_status() -> int:
    rows = _read_rows()
    print(f"store: {STORE} exists={STORE.exists()} rows={len(rows)}")
    print(f"schema: {SCHEMA} exists={SCHEMA.exists()}")
    print(f"stamp_frozen: {STAMP_FROZEN}")
    print(f"kei_pack: {KEI_PACK} exists={KEI_PACK.exists()}")
    print(f"proj_pack: {PROJ_PACK} exists={PROJ_PACK.exists()}")
    print(f"props_module: {PROPS_MODULE} exists={PROPS_MODULE.exists()}")
    if rows:
        print("markets", Counter(r.get("market") for r in rows))
        print("sources", Counter(r.get("source") for r in rows))
        pending = sum(1 for r in rows if r.get("final") is None)
        print(f"rows pending final fill: {pending}")
        props_tagged = [
            r
            for r in rows
            if r.get("player_id") and r.get("tag") not in {None, "n/a"}
        ]
        print(f"prop rows with non-n/a tag (should be 0): {len(props_tagged)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="WNBA grading harness")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser(
        "seed", help="Schema checklist: empty store + schema example rows"
    )
    p_seed.add_argument(
        "--force",
        action="store_true",
        help="Wipe store and reseed (prefer append-only; use only for rebuild)",
    )
    sub.add_parser("summary", help="Read-only summary (n, mean error)")
    sub.add_parser("status", help="Store status")

    args = ap.parse_args()
    if args.cmd == "seed":
        return cmd_seed(force=bool(args.force))
    if args.cmd == "summary":
        return cmd_summary()
    if args.cmd == "status":
        return cmd_status()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
