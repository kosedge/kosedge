"""Versioned, provenance-checked local inputs (t4141u).

Reads only pre-staged, sha-pinned files. Freshness and completeness are
explicit. Missing values are flagged — never silently defaulted to 7.0 / 0.0 / 1.0.

This module does not fetch, does not talk to Railway / Odds / prod DB, and
does not invent scores or fairs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

SCHEMA = "nfl-local-inputs/v1"

# Roles required for a W4–W6 RETROSPECTIVE or W8 file-backed build.
REQUIRED_ROLES_SCORES = ("schedule_games_csv",)
REQUIRED_ROLES_FEATURES = ("schedule_games_csv", "pbp_2025", "pbp_2026")

# Soft SLO hours (same spirit as data-platform source_matrix). Exceeded ⇒ stale flag, not a silent fill.
FRESHNESS_HOURS = {
    "schedule_games_csv": 36,
    "schedule_games_parquet": 36,
    "pbp_2025": 48,
    "pbp_2026": 48,
    "injuries_2026": 24,
    "w6_finals": 36,
}

FORBIDDEN_SILENT_DEFAULTS = {
    "rest_days": 7.0,
    "injury_impact": 0.0,
    "offense_index": 1.0,
    "defense_index": 1.0,
}


class LocalInputError(ValueError):
    """Fail-closed input problem. Do not catch-and-fill."""


@dataclass
class InputRecord:
    role: str
    path: str
    sha256: str
    expected_sha256: str
    as_of: Optional[str]
    retrieval_utc: Optional[str] = None
    data_cutoff_utc: Optional[str] = None
    source_url: Optional[str] = None
    release_tag: Optional[str] = None
    status: str = "OK"
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest_line(raw: str) -> Optional[Dict[str, str]]:
    s = raw.strip()
    if not s or s.startswith("#"):
        return None
    parts = s.split("\t")
    if len(parts) < 4:
        raise LocalInputError(
            f"manifest line needs sha256\\tpath\\trole\\tas_of, got {raw!r}"
        )
    rec = {
        "expected_sha256": parts[0].strip(),
        "path": parts[1].strip(),
        "role": parts[2].strip(),
        "as_of": parts[3].strip(),
    }
    if len(parts) >= 5:
        rec["source_url"] = parts[4].strip()
    if len(parts) >= 6:
        rec["release_tag"] = parts[5].strip()
    if len(parts) >= 7:
        rec["data_cutoff_utc"] = parts[6].strip()
    if len(parts) >= 8:
        rec["retrieval_utc"] = parts[7].strip()
    return rec


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hours_since(then: Optional[datetime], now: datetime) -> Optional[float]:
    if then is None:
        return None
    return (now - then).total_seconds() / 3600.0


def load_manifest(
    manifest_path: Path,
    *,
    now: Optional[datetime] = None,
    required_roles: Sequence[str] = REQUIRED_ROLES_SCORES,
) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if not manifest_path.is_file():
        raise LocalInputError(f"manifest missing: {manifest_path}")

    records: List[InputRecord] = []
    flags: List[str] = []
    by_role: Dict[str, List[InputRecord]] = {}
    base = manifest_path.parent

    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        spec = parse_manifest_line(raw)
        if spec is None:
            continue
        path = Path(spec["path"])
        if not path.is_absolute():
            path = (base / path).resolve()
        rec = InputRecord(
            role=spec["role"],
            path=str(path),
            sha256="",
            expected_sha256=spec["expected_sha256"],
            as_of=spec.get("as_of") or None,
            retrieval_utc=spec.get("retrieval_utc"),
            data_cutoff_utc=spec.get("data_cutoff_utc"),
            source_url=spec.get("source_url"),
            release_tag=spec.get("release_tag"),
        )
        exp = spec["expected_sha256"].strip().lower()
        if (not exp) or "placeholder" in exp or set(exp) <= set("0"):
            rec.status = "PLACEHOLDER"
            rec.flags.append("PLACEHOLDER_SHA_FORBIDDEN")
            flags.append(f"placeholder sha for role={rec.role}")
        elif not path.is_file():
            rec.status = "MISSING"
            rec.flags.append("FILE_MISSING")
            flags.append(f"missing file {path} role={rec.role}")
        else:
            got = sha256_file(path)
            rec.sha256 = got
            if got != exp:
                rec.status = "SHA_MISMATCH"
                rec.flags.append("SHA_MISMATCH")
                flags.append(f"sha mismatch {path}")
            else:
                rec.status = "OK"
            cutoff = _parse_iso(rec.data_cutoff_utc) or _parse_iso(rec.as_of)
            age = _hours_since(cutoff, now)
            limit = FRESHNESS_HOURS.get(rec.role)
            if age is None:
                rec.flags.append("FRESHNESS_UNKNOWN")
            elif limit is not None and age > limit:
                rec.flags.append("STALE")
                rec.flags.append(f"age_hours={age:.1f}>max={limit}")
        records.append(rec)
        by_role.setdefault(rec.role, []).append(rec)

    missing_roles = [
        role
        for role in required_roles
        if not any(r.status == "OK" for r in by_role.get(role, []))
    ]
    if missing_roles:
        flags.append("INCOMPLETE_ROLES:" + ",".join(missing_roles))

    status = "READY" if not flags and not missing_roles else "BLOCKED"
    return {
        "schema": SCHEMA,
        "status": status,
        "manifest": str(manifest_path),
        "as_of_check_utc": now.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "records": [r.to_dict() for r in records],
        "missing_roles": missing_roles,
        "flags": flags,
        "forbidden_silent_defaults": dict(FORBIDDEN_SILENT_DEFAULTS),
        "never_silent_default": True,
    }


def refuse_silent_default(name: str, value: Any, *, source: Optional[str] = None) -> None:
    """Raise if a caller is about to apply a known silent default."""
    if name in FORBIDDEN_SILENT_DEFAULTS and value == FORBIDDEN_SILENT_DEFAULTS[name]:
        if source != "explicit_named_value":
            raise LocalInputError(
                f"refusing silent default {name}={value!r}; flag missing instead"
            )


def require_numeric(mapping: Mapping[str, Any], key: str) -> float:
    raw = mapping.get(key)
    if raw is None or raw == "":
        raise LocalInputError(f"missing numeric {key}; not defaulting")
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise LocalInputError(f"non-numeric {key}={raw!r}") from exc


def summarize_flags(reports: Iterable[Mapping[str, Any]]) -> List[str]:
    out: List[str] = []
    for report in reports:
        out.extend(str(f) for f in (report.get("flags") or []))
    return out
