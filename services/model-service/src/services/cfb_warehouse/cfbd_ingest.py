"""CFBD research ingest + coverage audit. No scoring-model changes.

Raw CFBD payloads are written immutably to the warehouse lake. Point-in-time
team-week rows use only ``endWeek = game_week - 1``. Missing stays missing.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.team_features import (
    CFB_EDGE_BOARD_PUBLIC_ENABLED,
)
from src.services.cfb_warehouse.cfbd_client import (
    CfbdClient,
    key_present,
    redact,
    refuse_sealed_year,
)
from src.services.cfb_warehouse.frozen_140_scoring import (
    LEGAL_SEASONS,
    FrozenScoringError,
    assert_frozen_priors,
)
from src.services.cfb_warehouse.matchup_architecture_holdout import (
    FROZEN_BASELINE,
    PROTOCOL_SPLITS,
)
from src.services.cfb_warehouse.paths import cfbd_clean_dir, cfbd_raw_dir

FEATURE_MAP: Tuple[Dict[str, str], ...] = (
    {
        "need": "true_pace_plays",
        "endpoint": "/stats/season/advanced",
        "fields": "offense.plays, defense.plays, offense.drives",
        "class": "DIRECT",
        "pit": "endWeek=W-1 rolling snapshot. Week 1 is missing.",
    },
    {
        "need": "seconds_per_play",
        "endpoint": "/plays",
        "fields": "clock, wallclock",
        "class": "DERIVABLE_FROM_PBP",
        "pit": "One /plays call per year+week. Derive only from week < W.",
    },
    {
        "need": "off_def_ppa",
        "endpoint": "/stats/season/advanced + /ppa/games",
        "fields": "offense.ppa, defense.ppa, offense.totalPPA",
        "class": "DIRECT",
        "pit": "Prefer advanced endWeek=W-1. /ppa/teams is full-season — do not use mid-year.",
    },
    {
        "need": "success_rate",
        "endpoint": "/stats/season/advanced",
        "fields": "offense.successRate, defense.successRate",
        "class": "DIRECT",
        "pit": "endWeek=W-1",
    },
    {
        "need": "explosiveness",
        "endpoint": "/stats/season/advanced",
        "fields": "offense.explosiveness, defense.explosiveness",
        "class": "DIRECT",
        "pit": "CFBD explosiveness, not 50+0.15*(off-def).",
    },
    {
        "need": "pass_rush_explosiveness",
        "endpoint": "/stats/season/advanced",
        "fields": "offense.passingPlays.explosiveness, offense.rushingPlays.explosiveness",
        "class": "DIRECT",
        "pit": "endWeek=W-1",
    },
    {
        "need": "explosive_plays_created_allowed",
        "endpoint": "/plays",
        "fields": "ppa, yards_gained, play_type",
        "class": "DERIVABLE_FROM_PBP",
        "pit": "Define explosive from raw plays with week < W. Do not invent a proxy if PBP not pulled.",
    },
    {
        "need": "havoc",
        "endpoint": "/stats/season/advanced",
        "fields": "defense.havoc.total/frontSeven/db; offense.havoc is allowed",
        "class": "DIRECT",
        "pit": "endWeek=W-1",
    },
    {
        "need": "finishing_ppp",
        "endpoint": "/stats/season/advanced",
        "fields": "pointsPerOpportunity, totalOpportunies (CFBD spelling)",
        "class": "DIRECT",
        "pit": "endWeek=W-1. Off and def both present.",
    },
    {
        "need": "field_position",
        "endpoint": "/stats/season/advanced",
        "fields": "fieldPosition.averageStart, averagePredictedPoints",
        "class": "DIRECT",
        "pit": "endWeek=W-1",
    },
    {
        "need": "stuff_power_line_yards",
        "endpoint": "/stats/season/advanced",
        "fields": "stuffRate, powerSuccess, lineYards, secondLevelYards, openFieldYards",
        "class": "DIRECT",
        "pit": "endWeek=W-1",
    },
    {
        "need": "game_advanced",
        "endpoint": "/stats/game/advanced",
        "fields": "per-game advanced object",
        "class": "DIRECT",
        "pit": "Use only games with week < W when building a snapshot.",
    },
    {
        "need": "drives",
        "endpoint": "/drives",
        "fields": "drive result, start yard, scoring",
        "class": "DIRECT",
        "pit": "Year+week. Reconstruct finishing from week < W.",
    },
    {
        "need": "returning_production",
        "endpoint": "/player/returning",
        "fields": "percentPPA, usage, passing/rushing/receiving shares",
        "class": "DIRECT",
        "pit": "Season-Y preseason snapshot. Legal for all weeks of Y.",
    },
    {
        "need": "qb_player_success",
        "endpoint": "/ppa/players/season + /stats/player/season",
        "fields": "player PPA / passing category",
        "class": "DIRECT",
        "pit": "Player season endpoints may leak later weeks unless startWeek/endWeek used.",
    },
    {
        "need": "stats_player_success",
        "endpoint": "/stats/player/success",
        "fields": None,
        "class": "UNAVAILABLE",
        "pit": "Not in the current public swagger. Do not call blindly.",
    },
    {
        "need": "weather",
        "endpoint": "/games/weather",
        "fields": "kickoff-hour weather",
        "class": "UNAVAILABLE",
        "pit": "Swagger marks this Patreon-only. Free tier should treat as missing.",
    },
    {
        "need": "sp_plus",
        "endpoint": "/ratings/sp",
        "fields": "offense/defense pace, success, explosiveness, havoc, runRate",
        "class": "EXTERNAL_RATING",
        "pit": "Season-level, no throughWeek. Same-season SP+ leaks future games. Prior-year only, or diagnostic.",
    },
    {
        "need": "core_opponent_adjusted",
        "endpoint": "/ratings/core",
        "fields": "offense, defense, overall, throughWeek, modelVersion",
        "class": "POINT_IN_TIME_RISK",
        "pit": "throughWeek exists, but CFBD says historical CORE is retrospective methodology, not a live archive.",
    },
    {
        "need": "betting_lines",
        "endpoint": "/lines",
        "fields": "spreads/totals",
        "class": "POINT_IN_TIME_RISK",
        "pit": "Diagnostic only. Never a HIGH_ENV v2 predictor.",
    },
)

PROBE_CALLS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "adv_2022_endw3",
        "path": "/stats/season/advanced",
        "params": {"year": 2022, "endWeek": 3, "excludeGarbageTime": "true"},
    },
    {
        "id": "adv_2022_endw1",
        "path": "/stats/season/advanced",
        "params": {"year": 2022, "endWeek": 1, "excludeGarbageTime": "true"},
    },
    {
        "id": "plays_2022_w3",
        "path": "/plays",
        "params": {
            "year": 2022,
            "week": 3,
            "seasonType": "regular",
            "classification": "fbs",
        },
    },
    {
        "id": "returning_2022",
        "path": "/player/returning",
        "params": {"year": 2022},
    },
    {
        "id": "sp_2022",
        "path": "/ratings/sp",
        "params": {"year": 2022},
    },
    {
        "id": "core_2022_w3",
        "path": "/ratings/core",
        "params": {"year": 2022, "throughWeek": 3},
    },
    {
        "id": "games_2022",
        "path": "/games",
        "params": {"year": 2022, "seasonType": "regular", "division": "fbs"},
    },
    {
        "id": "drives_2022_w3",
        "path": "/drives",
        "params": {"year": 2022, "week": 3, "seasonType": "regular"},
    },
    {
        "id": "ppa_teams_2022",
        "path": "/ppa/teams",
        "params": {"year": 2022},
    },
    {
        "id": "game_adv_2022_w3",
        "path": "/stats/game/advanced",
        "params": {"year": 2022, "week": 3},
    },
    {
        "id": "weather_2022_w3",
        "path": "/games/weather",
        "params": {"year": 2022, "week": 3},
    },
    {
        "id": "lines_2022_w3",
        "path": "/lines",
        "params": {"year": 2022, "week": 3},
    },
)

RESEARCH_CALL_BUDGET = {
    "advanced_rolling_w1_14": 3 * 14,
    "games_schedule": 3,
    "returning_2021_2024": 4,
    "sp_plus_prior_year_only": 3,
    "core_optional_research": 3 * 14,
    "plays_deferred": 3 * 14,
    "first_pass_no_pbp_no_core": 3 * 14 + 3 + 4 + 3,
    "monthly_free_tier": 1000,
}


def through_week_for_game(game_week: int) -> Optional[int]:
    week = int(game_week)
    if week <= 1:
        return None
    return week - 1


def assert_point_in_time_safe(*, game_week: int, through_week: Optional[int]) -> None:
    if through_week is None:
        return
    if int(through_week) >= int(game_week):
        raise FrozenScoringError(
            f"PIT leak: through_week {through_week} is not < game week {game_week}"
        )


def _field_names(row: Any, *, prefix: str = "") -> List[str]:
    if not isinstance(row, dict):
        return []
    out: List[str] = []
    for key, val in row.items():
        path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        out.append(path)
        if isinstance(val, dict):
            out.extend(_field_names(val, prefix=path))
    return out


def persist_raw(
    *,
    endpoint: str,
    params: Mapping[str, Any],
    payload: Any,
    meta: Mapping[str, Any],
    prefer_hd: bool = True,
) -> Path:
    year = int(params.get("year") or params.get("season") or 0)
    refuse_sealed_year(year or None)
    slug = endpoint.strip("/").replace("/", "_")
    digest = hashlib.sha256(
        json.dumps(dict(params), sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]
    dest = cfbd_raw_dir(prefer_hd=prefer_hd) / slug / f"year={year}"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{slug}_{digest}.json"
    envelope = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endpoint": endpoint,
        "params": dict(params),
        "meta": {
            k: v
            for k, v in meta.items()
            if k not in {"url"} or "Authorization" not in str(v)
        },
        "payload": payload,
    }
    path.write_text(json.dumps(envelope, default=str) + "\n", encoding="utf-8")
    return path


def flatten_advanced_team(
    row: Mapping[str, Any],
    *,
    year: int,
    through_week: int,
) -> Dict[str, Any]:
    refuse_sealed_year(year)
    off = row.get("offense") or {}
    deff = row.get("defense") or {}

    def nest(block: Mapping[str, Any], key: str, field: str) -> Optional[float]:
        inner = block.get(key) or {}
        val = inner.get(field) if isinstance(inner, dict) else None
        return None if val in (None, "") else float(val)

    def num(block: Mapping[str, Any], field: str) -> Optional[float]:
        val = block.get(field)
        return None if val in (None, "") else float(val)

    return {
        "season": int(year),
        "through_week": int(through_week),
        "team": row.get("team"),
        "conference": row.get("conference"),
        "source": "cfbd_stats_season_advanced",
        "source_version": "cfbd_public_v1",
        "is_point_in_time_safe": True,
        "off_plays": num(off, "plays"),
        "def_plays": num(deff, "plays"),
        "off_drives": num(off, "drives"),
        "def_drives": num(deff, "drives"),
        "off_ppa": num(off, "ppa"),
        "def_ppa": num(deff, "ppa"),
        "off_success": num(off, "successRate"),
        "def_success": num(deff, "successRate"),
        "off_explosiveness": num(off, "explosiveness"),
        "def_explosiveness": num(deff, "explosiveness"),
        "off_pass_explosiveness": nest(off, "passingPlays", "explosiveness"),
        "off_rush_explosiveness": nest(off, "rushingPlays", "explosiveness"),
        "def_pass_explosiveness": nest(deff, "passingPlays", "explosiveness"),
        "def_rush_explosiveness": nest(deff, "rushingPlays", "explosiveness"),
        "off_havoc_allowed": nest(off, "havoc", "total"),
        "def_havoc": nest(deff, "havoc", "total"),
        "off_ppp": num(off, "pointsPerOpportunity"),
        "def_ppp": num(deff, "pointsPerOpportunity"),
        "off_opportunities": num(off, "totalOpportunies"),
        "def_opportunities": num(deff, "totalOpportunies"),
        "off_field_pos": nest(off, "fieldPosition", "averageStart"),
        "def_field_pos": nest(deff, "fieldPosition", "averageStart"),
        "off_stuff_rate": num(off, "stuffRate"),
        "def_stuff_rate": num(deff, "stuffRate"),
        "off_power_success": num(off, "powerSuccess"),
        "def_power_success": num(deff, "powerSuccess"),
    }


def write_team_week_table(
    rows: Sequence[Mapping[str, Any]],
    *,
    year: int,
    through_week: int,
    prefer_hd: bool = True,
) -> Path:
    refuse_sealed_year(year)
    dest = cfbd_clean_dir(prefer_hd=prefer_hd) / "team_week"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"team_week_{year}_through_{int(through_week):02d}.json"
    path.write_text(
        json.dumps(
            {
                "season": year,
                "through_week": through_week,
                "n": len(rows),
                "is_point_in_time_safe": True,
                "rows": list(rows),
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _contains_secret(payload: Any) -> bool:
    blob = json.dumps(payload, default=str)
    return redact(blob) != blob


def _audit_decision(has_key: bool, probes: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    statuses = [row.get("status") for row in probes]
    if not has_key:
        decision = "CFBD_KEY_MISSING_DO_NOT_INGEST"
        note = "CFBD_API_KEY is not set. Mapping is docs-only. Do not ingest."
    elif probes and statuses and all(status == 401 for status in statuses):
        decision = "CFBD_AUTH_FAILED_DO_NOT_INGEST"
        note = (
            "The stored server-side key was rejected (HTTP 401) on every probe. "
            "Do not guess the key. Put the exact generated value in the "
            "gitignored local env file. Do not paste it into chat. "
            "The feature map below is from official CFBD docs and remains the plan."
        )
    elif any(status == 200 for status in statuses):
        decision = "CFBD_COVERAGE_AUDIT_READY_FOR_REVIEW"
        note = "Audit only. No bulk ingest. No HIGH_ENV rerun. No architecture."
    else:
        decision = "CFBD_PROBE_INCOMPLETE_DO_NOT_INGEST"
        note = "Probes did not return usable 200s. Do not ingest."
    return {
        "decision": decision,
        "ship": False,
        "winner": None,
        "play": False,
        "note": note,
    }


def run_cfbd_coverage_audit(*, max_calls: int = 12, prefer_hd: bool = True) -> Dict[str, Any]:
    assert_frozen_priors()
    if CFB_EDGE_BOARD_PUBLIC_ENABLED:
        raise FrozenScoringError("public board kill switch must stay off")
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
        raise FrozenScoringError("production MATCHUP_RESPONSE drifted from 1.40")

    probes: List[Dict[str, Any]] = []
    client = None
    if key_present():
        client = CfbdClient(max_calls=max_calls)
        for spec in PROBE_CALLS[:max_calls]:
            payload, meta = client.get(spec["path"], spec["params"])
            raw_path = None
            fields: List[str] = []
            if meta.get("status") == 200 and payload is not None:
                raw_path = str(
                    persist_raw(
                        endpoint=spec["path"],
                        params=spec["params"],
                        payload=payload,
                        meta=meta,
                        prefer_hd=prefer_hd,
                    )
                )
                sample = payload[0] if isinstance(payload, list) and payload else payload
                fields = _field_names(sample)[:80]
                if spec["path"] == "/stats/season/advanced":
                    through = int(spec["params"]["endWeek"])
                    rows = [
                        flatten_advanced_team(row, year=2022, through_week=through)
                        for row in payload
                        if isinstance(row, dict)
                    ]
                    write_team_week_table(
                        rows, year=2022, through_week=through, prefer_hd=prefer_hd
                    )
            probes.append(
                {
                    "id": spec["id"],
                    "path": spec["path"],
                    "params": spec["params"],
                    "status": meta.get("status"),
                    "n_rows": meta.get("n_rows"),
                    "bytes": meta.get("bytes"),
                    "error": meta.get("error"),
                    "raw_path": raw_path,
                    "sample_fields": fields,
                }
            )
    payload = {
        "role": "cfbd_acquisition_audit",
        "scoring_equation_frozen": True,
        "do_not_tune": True,
        "kill_switch": "OFF",
        "merge_532": False,
        "used_2026_for_fitting": False,
        "opened_2025": False,
        "wrote_production_coefficient": False,
        "play": False,
        "bulk_ingest": False,
        "high_env_rerun": False,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "key_present": key_present(),
        "calls_used": 0 if client is None else client.calls,
        "call_budget_max": max_calls,
        "research_windows": {
            name: {"seasons": list(spec["seasons"]), "weeks": spec["weeks"]}
            for name, spec in PROTOCOL_SPLITS.items()
        },
        "legal_seasons": list(LEGAL_SEASONS),
        "feature_map": [dict(row) for row in FEATURE_MAP],
        "research_call_budget": RESEARCH_CALL_BUDGET,
        "probes": probes,
        "pit_rules": [
            "game week W uses only endWeek = W-1",
            "week 1 current-season advanced is missing",
            "no full-season aggregate for an in-season game",
            "no close as a predictor",
            "2025 never opened",
            "missing means missing",
        ],
        "decision": _audit_decision(key_present(), probes),
    }
    if _contains_secret(payload):
        raise FrozenScoringError("refusing to persist a payload that still contains the API key")
    return payload
