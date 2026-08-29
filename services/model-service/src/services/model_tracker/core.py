"""Core pick ledger: log, close, grade, summary, export."""

from __future__ import annotations

import csv
import io
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.model_tracker.grading import (
    DEFAULT_ODDS_AMERICAN,
    VALID_GRADES,
    VALID_MARKETS,
    VALID_TAGS,
    compute_clv,
    grade_market,
    grade_to_units,
    units_for_tag,
)
from src.services.model_tracker.lake import (
    TrackerLakeError,
    default_lake_dir,
    get_lake,
    resolve_backend_name,
)

log = logging.getLogger("kosedge.model_tracker")

TRACKER_VERSION = "model-tracker-v1-20260829"

SUPPORTED_SPORTS: Dict[str, Dict[str, Any]] = {
    "cfb": {
        "status": "live",
        "label": "College Football",
        "adapters": ["manual", "kei_board"],
        "notes": "Week 0–1 2026 desk path live",
    },
    "nfl": {
        "status": "stub",
        "label": "NFL",
        "adapters": ["manual"],
        "notes": (
            "Same ledger; do not auto-publish props PLAY chrome. "
            "Log desk picks only when approved."
        ),
        "feature_flag": "MODEL_TRACKER_NFL",
    },
    "nba": {
        "status": "stub",
        "label": "NBA",
        "adapters": ["manual"],
        "feature_flag": "MODEL_TRACKER_NBA",
    },
    "mlb": {
        "status": "stub",
        "label": "MLB",
        "adapters": ["manual"],
        "feature_flag": "MODEL_TRACKER_MLB",
    },
    "wnba": {
        "status": "stub",
        "label": "WNBA",
        "adapters": ["manual"],
        "feature_flag": "MODEL_TRACKER_WNBA",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _opt_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _opt_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _opt_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _deploy_git_sha() -> Optional[str]:
    raw = (
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("GITHUB_SHA")
        or os.getenv("GIT_SHA")
        or ""
    ).strip()
    return raw[:12] if raw else None


def game_key(*, season: int, week: int, home_team: str, away_team: str) -> str:
    home = str(home_team).strip().upper()
    away = str(away_team).strip().upper()
    return f"{int(season)}-W{int(week):02d}-{away}@{home}"


def documentation() -> Dict[str, Any]:
    backend = resolve_backend_name()
    return {
        "tracker_version": TRACKER_VERSION,
        "backend": backend,
        "lake_dir": str(default_lake_dir()),
        "table": "model_pick_ledger" if backend != "jsonl" else None,
        "unit_rules": {
            "PLAY": 1.0,
            "LEAN": 0.0,
            "default_odds_american": DEFAULT_ODDS_AMERICAN,
            "note": "LEAN logged for hit-rate; unit PnL only on PLAY",
        },
        "ops_doc": "data/ops/model-performance-tracker-v1-20260829.md",
        "proof_lake": "proof_projections / GET /proof/performance (complementary)",
        "public_props_play_chrome": False,
    }


def status_payload(*, lake_dir: Optional[Path] = None) -> Dict[str, Any]:
    lake = get_lake(lake_dir)
    try:
        recent = lake.list(limit=500)
    except TrackerLakeError as exc:
        return {
            "ok": False,
            "healthy": False,
            "error": str(exc),
            **documentation(),
        }
    pending = sum(1 for r in recent if str(r.get("grade")) == "pending")
    plays = sum(1 for r in recent if str(r.get("tag")) == "PLAY")
    leans = sum(1 for r in recent if str(r.get("tag")) == "LEAN")
    return {
        "ok": True,
        "healthy": True,
        "n_picks": len(recent),
        "n_pending": pending,
        "n_plays": plays,
        "n_leans": leans,
        "sports": sports_status(),
        **documentation(),
    }


def sports_status() -> Dict[str, Any]:
    out = {}
    for code, meta in SUPPORTED_SPORTS.items():
        enabled = True
        flag = meta.get("feature_flag")
        if flag and meta.get("status") == "stub":
            enabled = os.getenv(flag, "").strip().lower() in {"1", "true", "yes"}
        if meta.get("status") == "live":
            enabled = True
        out[code] = {**meta, "enabled": enabled or meta.get("status") == "live"}
    return out


def log_pick(
    payload: Mapping[str, Any],
    *,
    lake_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    sport = str(payload.get("sport") or "").strip().lower()
    if sport not in SUPPORTED_SPORTS:
        raise ValueError(f"unsupported sport: {sport}")
    tag = str(payload.get("tag") or "").strip().upper()
    if tag not in VALID_TAGS:
        raise ValueError("tag must be PLAY or LEAN")
    market_type = str(payload.get("market_type") or "spread").strip().lower()
    if market_type not in VALID_MARKETS:
        raise ValueError(f"market_type must be one of {sorted(VALID_MARKETS)}")
    side = str(payload.get("side") or "").strip().lower()
    if not side:
        raise ValueError("side is required")

    home = str(payload.get("home_team") or "").strip().upper()
    away = str(payload.get("away_team") or "").strip().upper()
    if not home or not away:
        raise ValueError("home_team and away_team are required")

    season = int(payload.get("season") or 2026)
    week = int(payload.get("week") if payload.get("week") is not None else 0)
    explicit_units = _opt_float(payload.get("units"))
    units = units_for_tag(tag, explicit_units=explicit_units if tag == "PLAY" else None)
    odds = int(payload.get("odds_american") or DEFAULT_ODDS_AMERICAN)
    now = _utc_now()
    unit_fields = grade_to_units(tag=tag, grade="pending", odds_american=odds, units=units)

    gkey = _opt_str(payload.get("game_key")) or game_key(
        season=season, week=week, home_team=home, away_team=away
    )

    record: Dict[str, Any] = {
        "id": str(payload.get("id") or uuid.uuid4()),
        "sport": sport,
        "season": season,
        "week": week,
        "slate_id": _opt_str(payload.get("slate_id")),
        "game_id": _opt_str(payload.get("game_id")),
        "game_key": gkey,
        "home_team": home,
        "away_team": away,
        "market_type": market_type,
        "side": side,
        "line_at_publish": _opt_float(payload.get("line_at_publish")),
        "odds_american": odds,
        "tag": tag,
        "units": units,
        "engine_version": _opt_str(payload.get("engine_version")),
        "artifact_as_of": _opt_str(payload.get("artifact_as_of")),
        "deploy_git_sha": _opt_str(payload.get("deploy_git_sha")) or _deploy_git_sha(),
        "kei_version": _opt_str(payload.get("kei_version")),
        "fair_line": _opt_float(payload.get("fair_line")),
        "kei_line": _opt_float(payload.get("kei_line")),
        "edge_pts": _opt_float(payload.get("edge_pts")),
        "confidence": _opt_str(payload.get("confidence")),
        "variance": _opt_float(payload.get("variance")),
        "confirmation": _opt_str(payload.get("confirmation")),
        "info_overlap": _opt_str(payload.get("info_overlap")),
        "line_at_close": None,
        "close_captured_at": None,
        "close_source": None,
        "clv": None,
        "open_to_close_move": None,
        "home_score": None,
        "away_score": None,
        "result_detail": {},
        "grade": "pending",
        "graded_at": None,
        **unit_fields,
        "proof_projection_id": _opt_str(payload.get("proof_projection_id")),
        "created_by": _opt_str(payload.get("created_by")) or "desk",
        "source": _opt_str(payload.get("source")) or "manual",
        "notes": _opt_str(payload.get("notes")),
        "payload": dict(payload.get("payload") or {}),
        "published_at": _opt_str(payload.get("published_at")) or now,
        "created_at": now,
        "updated_at": now,
        "tracker_version": TRACKER_VERSION,
    }
    if record["created_by"] not in {"desk", "system"}:
        record["created_by"] = "desk"
    if record["source"] not in {"manual", "kei_board", "auto"}:
        record["source"] = "manual"

    return get_lake(lake_dir).upsert(record)


def get_pick(pick_id: str, *, lake_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    return get_lake(lake_dir).get(pick_id)


def list_picks(
    *,
    sport: Optional[str] = None,
    season: Optional[int] = None,
    week: Optional[int] = None,
    tag: Optional[str] = None,
    grade: Optional[str] = None,
    engine_version: Optional[str] = None,
    limit: int = 200,
    lake_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    return get_lake(lake_dir).list(
        sport=sport,
        season=season,
        week=week,
        tag=tag,
        grade=grade,
        engine_version=engine_version,
        limit=limit,
    )


def close_pick(
    pick_id: str,
    *,
    line_at_close: float,
    source: str = "manual",
    lake_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    rec = get_pick(pick_id, lake_dir=lake_dir)
    if rec is None:
        return None
    close_f = float(line_at_close)
    pub = _opt_float(rec.get("line_at_publish"))
    rec["line_at_close"] = close_f
    rec["close_captured_at"] = _utc_now()
    rec["close_source"] = source or "manual"
    rec["clv"] = compute_clv(
        market_type=str(rec.get("market_type") or "spread"),
        side=str(rec.get("side") or ""),
        line_at_publish=pub,
        line_at_close=close_f,
    )
    if pub is not None:
        rec["open_to_close_move"] = round(close_f - pub, 4)
    rec["updated_at"] = _utc_now()
    return get_lake(lake_dir).upsert(rec)


def grade_pick(
    pick_id: str,
    *,
    home_score: Optional[int] = None,
    away_score: Optional[int] = None,
    grade: Optional[str] = None,
    source: str = "manual",
    lake_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    rec = get_pick(pick_id, lake_dir=lake_dir)
    if rec is None:
        return None

    explicit = _opt_str(grade)
    if explicit:
        g = explicit.lower()
        if g not in VALID_GRADES or g == "pending":
            raise ValueError(f"invalid grade: {grade}")
        detail = {"source": source, "explicit": True}
    else:
        if home_score is None or away_score is None:
            raise ValueError("home_score and away_score required unless grade is set")
        line = _opt_float(rec.get("line_at_close"))
        if line is None:
            line = _opt_float(rec.get("line_at_publish"))
        g, detail = grade_market(
            market_type=str(rec.get("market_type") or "spread"),
            side=str(rec.get("side") or ""),
            line=line,
            home_score=int(home_score),
            away_score=int(away_score),
            odds_american=int(rec.get("odds_american") or DEFAULT_ODDS_AMERICAN),
        )
        detail["source"] = source
        rec["home_score"] = int(home_score)
        rec["away_score"] = int(away_score)

    unit_fields = grade_to_units(
        tag=str(rec.get("tag") or "PLAY"),
        grade=g,
        odds_american=int(rec.get("odds_american") or DEFAULT_ODDS_AMERICAN),
        units=_opt_float(rec.get("units")),
    )
    rec["grade"] = g
    rec["graded_at"] = _utc_now()
    rec["result_detail"] = detail
    rec.update(unit_fields)
    # pending risked amount for open plays: keep units on the row for PLAY
    if g == "pending":
        pass
    elif str(rec.get("tag")) == "PLAY" and g in {"win", "loss", "push"}:
        rec["units_risked"] = float(rec.get("units") or 1.0) if g != "void" else 0.0
        if g == "push":
            rec["units_risked"] = float(rec.get("units") or 1.0)
            rec["units_pnl"] = 0.0
    rec["updated_at"] = _utc_now()
    return get_lake(lake_dir).upsert(rec)


def _record_bucket(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    w = l = p = v = 0
    for r in records:
        g = str(r.get("grade") or "").lower()
        if g == "win":
            w += 1
        elif g == "loss":
            l += 1
        elif g == "push":
            p += 1
        elif g == "void":
            v += 1
    decided = w + l
    hit = round(w / decided, 4) if decided else None
    return {
        "n": len(records),
        "wins": w,
        "losses": l,
        "pushes": p,
        "voids": v,
        "record": f"{w}-{l}-{p}",
        "hit_rate": hit,
    }


def _units_bucket(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    plays = [r for r in records if str(r.get("tag")) == "PLAY"]
    graded_plays = [
        r for r in plays if str(r.get("grade")) in {"win", "loss", "push", "void"}
    ]
    risked = sum(float(r.get("units") or 0) for r in graded_plays if str(r.get("grade")) != "void")
    # For pending plays, count potential risk separately
    pending_risk = sum(
        float(r.get("units") or 0)
        for r in plays
        if str(r.get("grade")) == "pending"
    )
    won = sum(float(r.get("units_won") or 0) for r in graded_plays)
    lost = sum(float(r.get("units_lost") or 0) for r in graded_plays)
    pnl = sum(float(r.get("units_pnl") or 0) for r in graded_plays)
    roi = round(pnl / risked, 4) if risked else None
    return {
        "n_plays": len(plays),
        "n_graded_plays": len(graded_plays),
        "units_risked": round(risked, 4),
        "units_pending": round(pending_risk, 4),
        "units_won": round(won, 4),
        "units_lost": round(lost, 4),
        "units_net": round(pnl, 4),
        "roi": roi,
    }


def _unit_curve(records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    plays = [
        r
        for r in records
        if str(r.get("tag")) == "PLAY"
        and str(r.get("grade")) in {"win", "loss", "push", "void"}
    ]

    def sort_key(r: Mapping[str, Any]) -> str:
        return str(r.get("graded_at") or r.get("published_at") or "")

    plays_sorted = sorted(plays, key=sort_key)
    curve: List[Dict[str, Any]] = []
    running = 0.0
    for r in plays_sorted:
        running += float(r.get("units_pnl") or 0)
        curve.append(
            {
                "id": r.get("id"),
                "game_key": r.get("game_key"),
                "graded_at": r.get("graded_at"),
                "grade": r.get("grade"),
                "units_pnl": float(r.get("units_pnl") or 0),
                "cumulative_units": round(running, 4),
            }
        )
    return curve


def summary(
    *,
    sport: Optional[str] = None,
    season: Optional[int] = None,
    week: Optional[int] = None,
    engine_version: Optional[str] = None,
    limit: int = 1000,
    lake_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    rows = list_picks(
        sport=sport,
        season=season,
        week=week,
        engine_version=engine_version,
        limit=limit,
        lake_dir=lake_dir,
    )
    plays = [r for r in rows if str(r.get("tag")) == "PLAY"]
    leans = [r for r in rows if str(r.get("tag")) == "LEAN"]

    by_engine: Dict[str, List[Mapping[str, Any]]] = {}
    by_week: Dict[str, List[Mapping[str, Any]]] = {}
    by_sport: Dict[str, List[Mapping[str, Any]]] = {}
    for r in rows:
        ev = str(r.get("engine_version") or "unknown")
        by_engine.setdefault(ev, []).append(r)
        wk = f"{r.get('sport')}-{r.get('season')}-W{int(r.get('week') or 0):02d}"
        by_week.setdefault(wk, []).append(r)
        by_sport.setdefault(str(r.get("sport") or "unknown"), []).append(r)

    clvs = [float(r["clv"]) for r in rows if r.get("clv") is not None]
    avg_clv = round(sum(clvs) / len(clvs), 4) if clvs else None

    return {
        "ok": True,
        "tracker_version": TRACKER_VERSION,
        "filters": {
            "sport": sport,
            "season": season,
            "week": week,
            "engine_version": engine_version,
            "limit": limit,
        },
        "n": len(rows),
        "plays": {
            **_record_bucket(plays),
            **_units_bucket(plays),
        },
        "leans": _record_bucket(leans),
        "combined_hit_rate": _record_bucket(rows),
        "units": _units_bucket(rows),
        "unit_curve": _unit_curve(rows),
        "clv": {
            "n": len(clvs),
            "avg_clv": avg_clv,
            "positive_rate": (
                round(sum(1 for c in clvs if c > 0) / len(clvs), 4) if clvs else None
            ),
        },
        "by_engine": {
            k: {**_record_bucket(v), **_units_bucket(v)} for k, v in sorted(by_engine.items())
        },
        "by_week": {
            k: {**_record_bucket(v), **_units_bucket(v)} for k, v in sorted(by_week.items())
        },
        "by_sport": {
            k: {**_record_bucket(v), **_units_bucket(v)} for k, v in sorted(by_sport.items())
        },
        "recent": rows[:25],
        "tracking": documentation(),
    }


def export_picks(
    *,
    sport: Optional[str] = None,
    season: Optional[int] = None,
    week: Optional[int] = None,
    fmt: str = "json",
    limit: int = 5000,
    lake_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    rows = list_picks(
        sport=sport,
        season=season,
        week=week,
        limit=limit,
        lake_dir=lake_dir,
    )
    if fmt == "csv":
        if not rows:
            return {"ok": True, "format": "csv", "csv": "", "n": 0}
        fieldnames = sorted({key for row in rows for key in row.keys()})
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = {}
            for k, v in row.items():
                if isinstance(v, (dict, list)):
                    flat[k] = str(v)
                else:
                    flat[k] = v
            writer.writerow(flat)
        return {"ok": True, "format": "csv", "csv": buf.getvalue(), "n": len(rows)}
    return {"ok": True, "format": "json", "picks": rows, "n": len(rows)}
