#!/usr/bin/env python3
"""NFL injury → KEI reprice job (midweek / Friday / gameday inactives).

Windows (ET, configurable in data/ops/nfl-injury-kei-cadence/config.json)
------------------------------------------------------------------------
- midweek          Thu 16:00 ET — affected games
- friday_final     Fri 16:00 ET — full slate reprice
- gameday_inactives ~90 min before kickoff — final KEI stamp / lock for CLV
- post_game         no KEI change; Tuesday PR path only

Doctrine: Model research fair + Model PR stay stable. SoT + Active PR + KEI
update. Tags = KEI vs Current only.

Usage
-----
  # Dry-run Friday window with built-in QB1 fixture
  python scripts/nfl/injury_kei_reprice.py --window friday_final --fixture --dry-run

  # Midweek dry-run (heartbeat / no-diff when no SoT payload)
  python scripts/nfl/injury_kei_reprice.py --window midweek --dry-run

  # Gameday inactives
  python scripts/nfl/injury_kei_reprice.py --window gameday_inactives --fixture --dry-run

  SEASON=2026 WEEK=1 python scripts/nfl/injury_kei_reprice.py --window friday_final --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[2]
MS_SRC = REPO / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))

from src.services.nfl_camp_sot_queue import (  # noqa: E402
    KeiPublishBlocked,
    assert_kei_publish_allowed,
    overdue_t1_blocking_kei_publish,
    scan_camp_sot_flags,
    t1_past_kei_publish,
)
from src.services.nfl_injury_kei_cadence import (  # noqa: E402
    CONFIG_RELATIVE,
    WindowId,
    describe_friday_1600_et,
    fixture_qb1_out_then_restore,
    load_cadence_config,
    run_injury_kei_window,
    window_config,
)
from src.services.nfl_injury_report_scan import scan_injury_report  # noqa: E402
from src.services.nfl_txn_sot_scan import (  # noqa: E402
    ingest_txn_events,
    scan_txn_flags,
)

OPS_DIR = REPO / "data" / "ops" / "nfl-injury-kei-cadence"
LATEST_LOG = OPS_DIR / "latest-run.json"


def _desk_os_open_t1_flags():
    """Camp + injury-report + txn open tickets for the KEI publish hard-block."""
    camp = scan_camp_sot_flags(latest_desk_only=True)
    report_items, _, _ = scan_injury_report()
    try:
        txn_events = ingest_txn_events()
        txn_flags = scan_txn_flags(events=txn_events)
    except Exception as exc:  # noqa: BLE001 — feed down must not skip the camp/report gate
        print(f"kei-publish-gate: txn scan unavailable ({exc}); camp+report only", file=sys.stderr)
        txn_flags = []
    return list(camp) + list(report_items) + list(txn_flags)


def _enforce_kei_publish_gate(*, dry_run: bool) -> int:
    """Refuse live KEI publish when overdue T1 lacks accept/no_change/reject.

    Dry-run still prints blockers but does not fail (desk can inspect).
    Returns non-zero only when a live publish is refused.
    """
    flags = _desk_os_open_t1_flags()
    blockers = overdue_t1_blocking_kei_publish(flags)
    if not blockers:
        return 0
    ids = [f.work_item_id for f in blockers]
    teams = [f.team for f in blockers]
    msg = (
        "KEI publish refused: overdue T1 with no accept/no_change/reject — "
        f"count={len(blockers)} teams={','.join(teams) or 'none'} "
        f"ids={','.join(ids) or 'none'}"
    )
    print(msg, file=sys.stderr)
    for flag in blockers:
        why = flag.overdue_reason or "overdue_or_past_kei_publish"
        print(
            f"  BLOCK {flag.team} {flag.work_item_id} status={flag.status} why={why}",
            file=sys.stderr,
        )
    if dry_run:
        print("dry_run: publish gate would refuse; no files written", file=sys.stderr)
        return 0
    try:
        assert_kei_publish_allowed(flags)
    except KeiPublishBlocked as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 1


def _load_json(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--window",
        choices=["midweek", "friday_final", "gameday_inactives", "post_game"],
        default=None,
        help="Report window to run (required unless --explain-friday / --fixture)",
    )
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute + log without claiming a live DB write",
    )
    ap.add_argument(
        "--fixture",
        action="store_true",
        help="Run built-in QB1 Out → restore fixture (preseason readiness)",
    )
    ap.add_argument(
        "--sot-before",
        type=Path,
        default=None,
        help="JSON list of prior SoT injury rows",
    )
    ap.add_argument(
        "--sot-after",
        type=Path,
        default=None,
        help="JSON list of current SoT injury rows",
    )
    ap.add_argument(
        "--games",
        type=Path,
        default=None,
        help="JSON list of games with kei/model/market spreads",
    )
    ap.add_argument(
        "--explain-friday",
        action="store_true",
        help="Print Friday 16:00 ET operator answer and exit",
    )
    args = ap.parse_args()

    if args.explain_friday:
        print(describe_friday_1600_et())
        print(f"config: {CONFIG_RELATIVE}")
        return 0

    season = args.season
    if season is None:
        season = int(os.environ.get("SEASON", "2026"))
    week = args.week
    if week is None:
        week = int(os.environ.get("WEEK", "1"))

    cfg = load_cadence_config(reload=True)

    # Desk OS item B — hard-block live KEI publish on overdue open T1s.
    gate_rc = _enforce_kei_publish_gate(dry_run=bool(args.dry_run))
    if gate_rc != 0:
        return gate_rc

    if args.fixture:
        window: WindowId = (args.window or "friday_final")  # type: ignore[assignment]
        payload = fixture_qb1_out_then_restore(week=week)
        out_run = payload["out"]
        restore = payload["restore"]
        print(f"window={window} season={season} week={week}")
        print(f"config={CONFIG_RELATIVE}")
        if cfg.get("manual_sot_until_feed_live"):
            print("note: manual SoT until official injury feed live")
        print("--- QB1 Out ---")
        print(out_run["ops_line"])
        if out_run.get("kei_moves"):
            m = out_run["kei_moves"][0]
            print(
                f"  KEI {m['kei_spread_before']} → {m['kei_spread_after']} "
                f"(Model {m['model_spread_before']} → {m['model_spread_after']}, "
                f"unchanged={m['model_unchanged']})"
            )
        if out_run.get("tag_moves"):
            t = out_run["tag_moves"][0]
            print(
                f"  tag {t['before']['action_label']} → {t['after']['action_label']} "
                f"(point {t['before']['point_grade']} → {t['after']['point_grade']})"
            )
        print("--- QB1 restore ---")
        print(restore["ops_line"])
        if restore.get("kei_moves"):
            m = restore["kei_moves"][0]
            print(
                f"  KEI {m['kei_spread_before']} → {m['kei_spread_after']} "
                f"(Model unchanged={m['model_unchanged']})"
            )
        print("--- Friday 16:00 ET ---")
        print(payload["friday_answer"])

        if not args.dry_run:
            OPS_DIR.mkdir(parents=True, exist_ok=True)
            _write_json(LATEST_LOG, {"mode": "fixture", **payload})
            print(f"wrote {LATEST_LOG.relative_to(REPO)}")
        else:
            print("dry_run: fixture computed; no files written")
        return 0

    if not args.window:
        print("--window is required unless --explain-friday or --fixture", file=sys.stderr)
        return 2

    window = args.window  # type: ignore[assignment]
    wcfg = window_config(window)

    print(f"window={window} season={season} week={week}")
    print(f"config={CONFIG_RELATIVE}")
    print(f"action={wcfg.get('action')} scope={wcfg.get('scope')}")
    if cfg.get("manual_sot_until_feed_live"):
        print("note: manual SoT until official injury feed live")

    previous = _load_json(args.sot_before) if args.sot_before else []
    current = _load_json(args.sot_after) if args.sot_after else []
    games = _load_json(args.games) if args.games else []
    if not isinstance(previous, list):
        previous = []
    if not isinstance(current, list):
        current = []
    if not isinstance(games, list):
        games = []

    # Optional Active PR freeze inputs from desk latest.json
    desk = _load_json(REPO / "data" / "ops" / "nfl-power-ratings-desk" / "latest.json")
    published: Dict[str, float] = {}
    active_before: Dict[str, float] = {}
    if isinstance(desk, dict) and isinstance(desk.get("teams"), list):
        for row in desk["teams"]:
            if not isinstance(row, dict):
                continue
            team = str(row.get("team") or "")
            if not team:
                continue
            try:
                published[team] = float(row.get("model_pr"))
                active_before[team] = float(row.get("active_pr", row.get("model_pr")))
            except (TypeError, ValueError):
                continue

    result = run_injury_kei_window(
        window=window,
        season=season,
        week=week,
        previous_sot=previous,
        current_sot=current,
        games=games,
        published_model_prs=published or None,
        active_prs_before=active_before or None,
        dry_run=bool(args.dry_run),
    )
    print(result.ops_line)
    print(json.dumps(result.to_dict(), indent=2))

    if not args.dry_run:
        OPS_DIR.mkdir(parents=True, exist_ok=True)
        _write_json(
            LATEST_LOG,
            {
                "mode": "window",
                "window": window,
                "season": season,
                "week": week,
                "result": result.to_dict(),
            },
        )
        print(f"wrote {LATEST_LOG.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
