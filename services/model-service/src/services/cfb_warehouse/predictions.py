"""Immutable CFB research-fair snapshots.

Writes JSON / JSONL / parquet under the clean warehouse ``predictions/`` dir.
Identity is ``(model_version, as_of, game_id)``. Same key must not be mutated
or overwritten. Injury or new information = a new ``as_of`` (KEI later, not here).

Requires ``model_version`` and ``as_of`` to write. Not a KEI publish path.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from src.services.cfb_warehouse.leakage import (
    LEAKAGE_RULE,
    assert_available_before_kickoff,
    era_tag,
)
from src.services.cfb_warehouse.paths import predictions_dir

ALLOWED_FORMATS = ("json", "jsonl", "parquet")


class ImmutablePredictionError(ValueError):
    """Raised when a write would overwrite an existing research snapshot."""


class MissingPredictionIdentityError(ValueError):
    """Raised when model_version / as_of / game_id is missing."""


def _as_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def normalize_as_of(value: Any) -> str:
    dt = _as_datetime(value)
    if dt is None:
        raise MissingPredictionIdentityError(
            "as_of is required and must be an ISO timestamp"
        )
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_token(raw: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(raw).strip())
    return text.strip("._") or "unknown"


def prediction_key(
    *,
    model_version: Any,
    as_of: Any,
    game_id: Any,
) -> tuple[str, str, str]:
    version = str(model_version or "").strip()
    gid = str(game_id or "").strip()
    as_of_iso = normalize_as_of(as_of)
    if not version or not gid:
        raise MissingPredictionIdentityError(
            "model_version, as_of, and game_id are required to write a snapshot"
        )
    return version, as_of_iso, gid


def _json_path(base: Path, version: str, as_of_iso: str, game_id: str) -> Path:
    return (
        base
        / _safe_token(version)
        / _safe_token(as_of_iso)
        / f"{_safe_token(game_id)}.json"
    )


def _jsonl_path(base: Path, version: str, as_of_iso: str) -> Path:
    return base / _safe_token(version) / f"{_safe_token(as_of_iso)}.jsonl"


def _parquet_path(base: Path, version: str, as_of_iso: str) -> Path:
    return base / _safe_token(version) / f"{_safe_token(as_of_iso)}.parquet"


def _jsonl_has_key(path: Path, version: str, as_of_iso: str, game_id: str) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            str(row.get("model_version")) == version
            and str(row.get("as_of")) == as_of_iso
            and str(row.get("game_id")) == game_id
        ):
            return True
    return False


def _parquet_has_key(path: Path, version: str, as_of_iso: str, game_id: str) -> bool:
    if not path.is_file():
        return False
    import pandas as pd

    frame = pd.read_parquet(path)
    if frame.empty:
        return False
    hit = frame[
        (frame["model_version"].astype(str) == version)
        & (frame["as_of"].astype(str) == as_of_iso)
        & (frame["game_id"].astype(str) == game_id)
    ]
    return not hit.empty


def snapshot_exists(
    *,
    model_version: Any,
    as_of: Any,
    game_id: Any,
    root: Optional[Path] = None,
    prefer_hd: bool = True,
) -> bool:
    version, as_of_iso, gid = prediction_key(
        model_version=model_version, as_of=as_of, game_id=game_id
    )
    base = predictions_dir(prefer_hd=prefer_hd, root=root)
    if _json_path(base, version, as_of_iso, gid).is_file():
        return True
    if _jsonl_has_key(_jsonl_path(base, version, as_of_iso), version, as_of_iso, gid):
        return True
    if _parquet_has_key(_parquet_path(base, version, as_of_iso), version, as_of_iso, gid):
        return True
    return False


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    version, as_of_iso, gid = prediction_key(
        model_version=row.get("model_version"),
        as_of=row.get("as_of"),
        game_id=row.get("game_id"),
    )
    season = row.get("season")
    kickoff = row.get("kickoff") or row.get("game_date")
    available_at = row.get("available_at")
    if available_at is not None:
        assert_available_before_kickoff(
            available_at=available_at,
            kickoff=kickoff,
            game_date=row.get("game_date"),
            feature_week=row.get("feature_week"),
            game_week=row.get("week"),
            feature_name="model_prediction",
        )
    out = {
        "model_version": version,
        "as_of": as_of_iso,
        "game_id": gid,
        "season": int(season) if season not in (None, "") else None,
        "week": int(row["week"]) if row.get("week") not in (None, "") else None,
        "home_team_id": row.get("home_team_id"),
        "away_team_id": row.get("away_team_id"),
        "fair_spread": row.get("fair_spread", row.get("model_spread_home")),
        "fair_total": row.get("fair_total", row.get("model_total")),
        "wp": row.get("wp", row.get("home_win_prob")),
        "uncertainty": row.get("uncertainty"),
        "available_at": (
            normalize_as_of(available_at) if available_at is not None else None
        ),
        "era_tag": row.get("era_tag")
        or (era_tag(int(season)) if season not in (None, "") else None),
        "week_band": row.get("week_band"),
        "leakage_rule": row.get("leakage_rule") or LEAKAGE_RULE,
        "source": row.get("source") or "cfb_warehouse_research",
        "notes": dict(row.get("notes") or {}),
        "kei": False,
    }
    return out


def write_prediction(
    row: Mapping[str, Any],
    *,
    root: Optional[Path] = None,
    prefer_hd: bool = True,
    formats: Sequence[str] = ("json",),
) -> dict[str, Any]:
    """Write one immutable snapshot. Rejects overwrite of the same key."""
    wanted = tuple(str(f).lower() for f in formats) or ("json",)
    unknown = [f for f in wanted if f not in ALLOWED_FORMATS]
    if unknown:
        raise ValueError(f"unsupported prediction formats: {unknown}")

    payload = _normalize_row(row)
    version = payload["model_version"]
    as_of_iso = payload["as_of"]
    gid = payload["game_id"]
    base = predictions_dir(prefer_hd=prefer_hd, root=root)
    base.mkdir(parents=True, exist_ok=True)

    if snapshot_exists(
        model_version=version,
        as_of=as_of_iso,
        game_id=gid,
        root=root,
        prefer_hd=prefer_hd,
    ):
        raise ImmutablePredictionError(
            f"refuse overwrite of research snapshot "
            f"(model_version={version!r}, as_of={as_of_iso!r}, game_id={gid!r}); "
            "insert a new as_of instead (injury = new row / KEI later)"
        )

    written: dict[str, str] = {}
    if "json" in wanted:
        path = _json_path(base, version, as_of_iso, gid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=str) + "\n")
        written["json"] = str(path)
    if "jsonl" in wanted:
        path = _jsonl_path(base, version, as_of_iso)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")
        written["jsonl"] = str(path)
    if "parquet" in wanted:
        import pandas as pd

        path = _parquet_path(base, version, as_of_iso)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame([payload])
        if path.is_file():
            existing = pd.read_parquet(path)
            frame = pd.concat([existing, frame], ignore_index=True)
        frame.to_parquet(path, index=False)
        written["parquet"] = str(path)

    payload["_written"] = written
    return payload


def write_predictions(
    rows: Iterable[Mapping[str, Any]],
    *,
    root: Optional[Path] = None,
    prefer_hd: bool = True,
    formats: Sequence[str] = ("json",),
) -> list[dict[str, Any]]:
    return [
        write_prediction(row, root=root, prefer_hd=prefer_hd, formats=formats)
        for row in rows
    ]
