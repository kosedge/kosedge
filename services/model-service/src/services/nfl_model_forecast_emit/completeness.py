"""Input completeness for a current NFL week slate.

Fail-closed. Does not invent depth, injury, zeros, or placeholders.
A W8 run that would silently use W1 camp depth or empty injury_paths
as "healthy" is a blocker, not a forecast.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from src.services.nfl_model_forecast_emit.emit import (
    ForecastIncompleteError,
    format_utc,
    parse_utc,
    sha256_hex,
)
from src.services.nfl_model_forecast_emit.schema import CERT_CANDIDATE, LABEL
from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.data_integrity import pack_sha256
from src.services.nfl_season_engine.loaders import (
    _PACKAGE_DATA_DIR,
    _PACKAGED_DEPTH_FILES,
    load_packaged_regular_schedule,
)

CANONICAL_SCHEDULE = _PACKAGE_DATA_DIR / "nfl-canonical-schedule-2026.json"
EPA_PRIORS = _PACKAGE_DATA_DIR / "nfl_team_epa_priors_2026.json"
BACKBONE = _PACKAGE_DATA_DIR / "nfl_team_efficiency_backbone_2026.json"


def _check(
    name: str,
    *,
    ok: bool,
    evidence: Mapping[str, Any],
    blocker: str = "",
) -> Dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "blocker": blocker if not ok else "",
        "evidence": dict(evidence),
    }


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def week_games_from_canonical(season: int, week: int) -> List[Dict[str, Any]]:
    if not CANONICAL_SCHEDULE.is_file():
        raise ForecastIncompleteError(
            f"canonical schedule missing: {CANONICAL_SCHEDULE}",
            gap="G1",
            reason="schedule_missing",
        )
    payload = _load_json(CANONICAL_SCHEDULE)
    games_in = payload.get("games") or payload.get("slate") or payload
    if isinstance(payload, Mapping) and isinstance(payload.get("weeks"), list):
        games_in = []
        for block in payload["weeks"]:
            games_in.extend(block.get("games") or [])
    if isinstance(payload, Mapping) and isinstance(payload.get("games"), list):
        games_in = payload["games"]
    out: List[Dict[str, Any]] = []
    if isinstance(games_in, list):
        for raw in games_in:
            if not isinstance(raw, Mapping):
                continue
            if int(raw.get("season") or 0) != int(season):
                continue
            if int(raw.get("week") or 0) != int(week):
                continue
            gid = str(raw.get("game_id") or raw.get("engine_game_id") or "").strip()
            kickoff = raw.get("kickoff_utc")
            home = str(raw.get("home_team_id") or raw.get("home_team") or "").upper()
            away = str(raw.get("away_team_id") or raw.get("away_team") or "").upper()
            out.append(
                {
                    "game_id": gid,
                    "home_team": home,
                    "away_team": away,
                    "kickoff_utc": kickoff,
                    "season": season,
                    "week": week,
                }
            )
    return out


def audit_week_inputs(
    *,
    season: int = 2026,
    week: int = 8,
    now_utc: Any = None,
) -> Dict[str, Any]:
    """Verify current inputs for a week slate. Does not run the engine."""
    now = parse_utc(now_utc) or datetime.now(timezone.utc).replace(microsecond=0)
    checks: List[Dict[str, Any]] = []

    depth_path = _PACKAGED_DEPTH_FILES.get(int(season))
    depth_ok = bool(depth_path and Path(depth_path).is_file())
    depth_payload: Dict[str, Any] = {}
    depth_sha = ""
    if depth_ok:
        depth_payload = _load_json(Path(depth_path))
        depth_sha = pack_sha256(Path(depth_path))
    depth_week = int(depth_payload.get("week") or 0) if depth_ok else None
    depth_as_of = str(depth_payload.get("as_of") or "")
    intel_as_of = str(depth_payload.get("daily_intel_as_of") or "")
    injury_paths = list(depth_payload.get("injury_paths") or []) if depth_ok else []
    week_match = depth_ok and depth_week == int(week)
    checks.append(
        _check(
            "depth_sot_week",
            ok=week_match,
            blocker=(
                f"packaged depth is week={depth_week} as_of={depth_as_of} "
                f"({Path(depth_path).name if depth_path else 'missing'}); "
                f"requested week={week}. Running the engine would silently "
                f"use stale camp depth as current W{week} volume SoT."
            ),
            evidence={
                "path": str(depth_path) if depth_path else "",
                "week": depth_week,
                "as_of": depth_as_of,
                "as_of_timestamp": depth_payload.get("as_of_timestamp"),
                "snapshot_id": depth_payload.get("snapshot_id"),
                "pack_sha256": depth_sha,
                "row_count": depth_payload.get("row_count"),
                "requested_week": week,
            },
        )
    )

    injury_ok = bool(injury_paths)
    checks.append(
        _check(
            "injury_paths_current",
            ok=injury_ok,
            blocker=(
                "injury_paths is empty. A slate run would treat every player "
                "as healthy (silent zero injury). t4559u forbids invented "
                "injury and silent healthy fills."
            ),
            evidence={
                "injury_path_count": len(injury_paths),
                "daily_intel_as_of": intel_as_of,
                "note": depth_payload.get("notes", [None])[-1] if depth_ok else "",
            },
        )
    )

    db_url = (os.environ.get("DATABASE_URL") or "").strip()
    checks.append(
        _check(
            "current_weekly_depth_db",
            ok=False,
            blocker=(
                "DATABASE_URL unset on this VM. Cannot load "
                "nfl_dp_depth_chart_weekly / injury nowcast for week "
                f"{week}. Will not invent a current book from W1 pack."
            )
            if not db_url
            else "DATABASE_URL present but weekly W8 SoT pull is not authorized on this DRAFT (NFL NO-GO / no remat).",
            evidence={"database_url_present": bool(db_url)},
        )
    )

    schedule, sched_meta = load_packaged_regular_schedule(season)
    week_sched = [g for g in schedule if int(g.week) == int(week)]
    canon = week_games_from_canonical(season, week)
    kickoff_ok = bool(canon) and all(parse_utc(g.get("kickoff_utc")) for g in canon)
    checks.append(
        _check(
            "week_schedule_kickoffs",
            ok=kickoff_ok,
            blocker="canonical schedule missing kickoff_utc for one or more games",
            evidence={
                "packaged_week_games": len(week_sched),
                "canonical_week_games": len(canon),
                "schedule_as_of": sched_meta.get("schedule_as_of")
                if isinstance(sched_meta, Mapping)
                else "",
                "game_ids": [g["game_id"] for g in canon],
            },
        )
    )

    epa_ok = EPA_PRIORS.is_file() and BACKBONE.is_file()
    epa = _load_json(EPA_PRIORS) if EPA_PRIORS.is_file() else {}
    backbone = _load_json(BACKBONE) if BACKBONE.is_file() else {}
    epa_as_of = str(epa.get("as_of") or backbone.get("as_of") or "")
    # Priors are prior-season by design; they are NOT current W8 in-season EPA.
    checks.append(
        _check(
            "inseason_efficiency_current",
            ok=False,
            blocker=(
                f"packaged efficiency/EPA is a {epa.get('prior_season')} prior "
                f"(as_of={epa_as_of}). No current W{week} in-season backbone "
                "on this VM. Using it as a W8 'current' strength book would "
                "be a placeholder prior, not a verified current input."
            ),
            evidence={
                "epa_path": str(EPA_PRIORS),
                "backbone_path": str(BACKBONE),
                "epa_as_of": epa_as_of,
                "prior_season": epa.get("prior_season"),
                "files_present": epa_ok,
            },
        )
    )

    failing = [c for c in checks if not c["ok"]]
    passing = [c for c in checks if c["ok"]]
    completeness = {
        "schema_version": "nfl-week-input-completeness-v1",
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "purpose": "research_eng_only",
        "audited_at_utc": format_utc(now),
        "season": int(season),
        "week": int(week),
        "engine_version": ENGINE_VERSION,
        "ok": not failing,
        "failing_components": [c["name"] for c in failing],
        "checks": checks,
        "slate_game_ids": [g["game_id"] for g in canon],
        "note": (
            "t4559u: do not run the engine or emit forecasts while any "
            "current-input check fails. No invented numbers, no silent "
            "zero injury, no W1-as-W8 depth."
        ),
    }
    completeness["input_completeness_sha256"] = sha256_hex(
        json.dumps(
            {k: completeness[k] for k in ("season", "week", "failing_components", "checks") if k in completeness},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    )
    completeness["passed"] = [c["name"] for c in passing]
    return completeness


def assert_week_inputs_complete(**kwargs: Any) -> Dict[str, Any]:
    report = audit_week_inputs(**kwargs)
    if not report["ok"]:
        names = ", ".join(report["failing_components"])
        raise ForecastIncompleteError(
            f"week inputs incomplete: {names}",
            gap="G8",
            reason="week_inputs_incomplete",
        )
    return report
