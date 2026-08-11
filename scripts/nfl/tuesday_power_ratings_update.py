#!/usr/bin/env python3
"""Tuesday NFL Power Ratings publish — shrinkage + audit trail.

When
----
Tuesday after the prior week's games are final (US/Eastern). Documented cutoff
is Tuesday 06:00 ET (slide if MNF/TNF makeup).

What it does
------------
1. Load Layer-1 strengths from packaged real universe (same path as wins/True PR).
2. Derive PR_data via Method B (expected margin vs league average, zero-centered).
3. If prior snapshot exists and week >= 1: Bayesian shrink toward prior.
4. Apply Ryan Adj (default 0 from ryan_adj.json — never invent non-zero).
5. Write latest desk JSON + Tuesday audit trail under data/ops/nfl-power-ratings-desk/.

Preseason / week 0
------------------
No-ops shrinkage (publishes initial Model PR snapshot only). Safe to run now.

Usage
-----
  python scripts/nfl/tuesday_power_ratings_update.py
  python scripts/nfl/tuesday_power_ratings_update.py --week 1
  python scripts/nfl/tuesday_power_ratings_update.py --week 0 --phase preseason
  SEASON=2026 WEEK=2 python scripts/nfl/tuesday_power_ratings_update.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[2]
MS_SRC = REPO / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))

from src.services.nfl_season_engine import (  # noqa: E402
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_real_universe,
)
from src.services.nfl_season_engine.loaders import universe_schedule_meta  # noqa: E402
from src.services.nfl_season_engine.power_ratings_desk import (  # noqa: E402
    RyanAdj,
    build_desk_rows,
    build_tuesday_audit,
    default_ryan_adjs,
    derive_raw_model_prs,
    product_team_id,
    serialize_power_ratings_desk,
    shrink_model_prs,
    zero_center,
)

DESK_DIR = REPO / "data" / "ops" / "nfl-power-ratings-desk"
LATEST_PATH = DESK_DIR / "latest.json"
RYAN_ADJ_PATH = DESK_DIR / "ryan_adj.json"
POINTER_PATH = REPO / "data" / "ops" / "nfl-web-launch-bundle.json"


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _active_run_id() -> Optional[str]:
    ptr = _load_json(POINTER_PATH)
    if not ptr:
        return None
    return ptr.get("active_run_id") or ptr.get("bundle_id")


def _load_ryan_adjs(teams: list[str]) -> Dict[str, RyanAdj]:
    base = default_ryan_adjs(teams)
    raw = _load_json(RYAN_ADJ_PATH) or {}
    entries = raw.get("teams") if isinstance(raw.get("teams"), dict) else raw
    if not isinstance(entries, dict):
        return base
    for team, payload in entries.items():
        code = product_team_id(team)
        if isinstance(payload, (int, float)):
            base[code] = RyanAdj(team=code, adj=float(payload), reason="")
            continue
        if not isinstance(payload, dict):
            continue
        adj = float(payload.get("adj", 0.0) or 0.0)
        reason = str(payload.get("reason") or "")
        if abs(adj) > 1.0 and not reason.strip():
            raise SystemExit(
                f"Ryan Adj for {code} is {adj} but reason is empty "
                "(>1.0 requires written reason)."
            )
        base[code] = RyanAdj(
            team=code,
            adj=adj,
            reason=reason,
            updated_at_utc=str(payload.get("updated_at_utc") or ""),
        )
    return base


def _prior_model_map(latest: Optional[Dict[str, Any]]) -> Dict[str, float]:
    if not latest or not isinstance(latest.get("teams"), list):
        return {}
    out: Dict[str, float] = {}
    for row in latest["teams"]:
        if not isinstance(row, dict):
            continue
        team = product_team_id(str(row.get("team") or ""))
        if not team:
            continue
        try:
            out[team] = float(row.get("model_pr"))
        except (TypeError, ValueError):
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument(
        "--week",
        type=int,
        default=None,
        help="Completed week number (0 = preseason snapshot / no-op shrink)",
    )
    ap.add_argument(
        "--phase",
        default=None,
        help="preseason | inseason (default: preseason if week<=0 else inseason)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing files",
    )
    args = ap.parse_args()

    week = args.week
    if week is None:
        import os

        week = int(os.environ.get("WEEK", "0") or 0)
    week = int(week)
    phase = args.phase or ("preseason" if week <= 0 else "inseason")

    DESK_DIR.mkdir(parents=True, exist_ok=True)

    universe = build_packaged_real_universe(season=args.season)
    try:
        schedule_meta = universe_schedule_meta(universe) or {}
    except Exception:
        schedule_meta = {"strength_source": "packaged_efficiency_backbone"}

    strengths = universe.strengths
    teams = [product_team_id(t) for t in strengths.keys()]
    ryan = _load_ryan_adjs(teams)
    run_id = _active_run_id()
    latest = _load_json(LATEST_PATH)
    prior = _prior_model_map(latest)

    # PR_data from current strength book (Method B → zero-center).
    data = zero_center(derive_raw_model_prs(strengths, use_full_strength=True))

    alphas: Dict[str, float] = {}
    if week <= 0 or not prior:
        # Preseason / first publish: no shrinkage.
        published = data
        for t in published:
            alphas[t] = 0.0
        note = "preseason_snapshot" if week <= 0 else "initial_publish_no_prior"
    else:
        published, alphas = shrink_model_prs(prior, data, week=week)
        note = "tuesday_shrink"

    rows = build_desk_rows(
        strengths,
        as_of_week=week,
        ryan_adjs=ryan,
        prev_week_model_prs=prior or None,
        published_model_prs=published,
    )
    desk = serialize_power_ratings_desk(
        universe,
        season=args.season,
        as_of_week=week,
        phase=phase,
        active_run_id=run_id,
        engine_version=DEFAULT_SEASON_ENGINE_VERSION,
        ryan_adjs=ryan,
        prev_week_model_prs=prior or None,
        published_model_prs=published,
        schedule_meta=schedule_meta,
    )
    desk["publish_note"] = note

    audit = build_tuesday_audit(
        week=week,
        prior=prior or {t: 0.0 for t in published},
        data=data,
        published=published,
        alphas=alphas,
        desk_rows=rows,
        active_run_id=run_id,
        engine_version=DEFAULT_SEASON_ENGINE_VERSION,
    )
    audit["publish_note"] = note

    # Ensure ryan_adj.json exists with zeros (never invent non-zero).
    if not RYAN_ADJ_PATH.is_file():
        ryan_payload = {
            "policy": {
                "routine": 0.25,
                "meaningful": 0.5,
                "major": 1.0,
                "requires_written_reason_above": 1.0,
            },
            "note": "All adjs default 0. Non-zero requires reason + timestamp.",
            "teams": {
                t: {"adj": 0.0, "reason": "", "updated_at_utc": ""}
                for t in sorted(set(teams))
            },
        }
    else:
        ryan_payload = _load_json(RYAN_ADJ_PATH) or {}

    stamp = desk["generated_at_utc"].replace(":", "").replace("-", "")
    audit_path = DESK_DIR / f"tuesday-audit-week{week}-{stamp}.json"
    snapshot_path = DESK_DIR / f"snapshot-week{week}-{stamp}.json"

    summary = {
        "week": week,
        "phase": phase,
        "note": note,
        "team_count": desk["team_count"],
        "mean_model_pr": desk["mean_model_pr"],
        "active_run_id": run_id,
        "method": desk["method"],
        "latest": str(LATEST_PATH),
        "audit": str(audit_path),
    }
    print(json.dumps(summary, indent=2))

    if args.dry_run:
        return 0

    LATEST_PATH.write_text(json.dumps(desk, indent=2) + "\n")
    snapshot_path.write_text(json.dumps(desk, indent=2) + "\n")
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    if not RYAN_ADJ_PATH.is_file():
        RYAN_ADJ_PATH.write_text(json.dumps(ryan_payload, indent=2) + "\n")

    # Pointer for web loader.
    pointer = {
        "latest": "latest.json",
        "ryan_adj": "ryan_adj.json",
        "active_run_id": run_id,
        "as_of_week": week,
        "phase": phase,
        "method": "B",
        "updated_at_utc": desk["generated_at_utc"],
    }
    (DESK_DIR / "pointer.json").write_text(json.dumps(pointer, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
