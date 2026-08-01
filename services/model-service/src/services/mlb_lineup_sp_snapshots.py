"""As-of lineup + SP snapshots keyed by game_id / hours_to_first_pitch.

Densify historically stamps at −3h and cannot grade live nowcast CLV.
This lake persists (or reconstructs) snapshot cards so late-info slices
(≤3h / ≤6h to pitch) can be graded independently of the full densify set.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

_DEFAULT_LAKE = Path(__file__).resolve().parents[2] / "data" / "mlb" / "lineup_sp_snapshots"
LAKE_DIR = Path(os.getenv("MLB_LINEUP_SP_SNAPSHOT_DIR") or _DEFAULT_LAKE)

# Canonical densify stamp tiers (hours before first pitch).
SNAPSHOT_HOURS_TIERS: tuple[float, ...] = (12.0, 6.0, 3.0, 1.0)


@dataclass
class LineupSpSnapshot:
    game_id: str
    observed_at: str  # ISO UTC
    hours_to_first_pitch: float
    lineup_hash: str
    lineup_confirmed: bool
    known_home: int
    known_away: int
    sp_home: Optional[str] = None
    sp_away: Optional[str] = None
    sp_home_id: Optional[int] = None
    sp_away_id: Optional[int] = None
    lineup_confidence_home: float = 0.85
    lineup_confidence_away: float = 0.85
    source: str = "context"
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "LineupSpSnapshot":
        return cls(
            game_id=str(payload.get("game_id") or ""),
            observed_at=str(payload.get("observed_at") or ""),
            hours_to_first_pitch=float(payload.get("hours_to_first_pitch") or 0.0),
            lineup_hash=str(payload.get("lineup_hash") or ""),
            lineup_confirmed=bool(payload.get("lineup_confirmed")),
            known_home=int(payload.get("known_home") or 0),
            known_away=int(payload.get("known_away") or 0),
            sp_home=payload.get("sp_home"),
            sp_away=payload.get("sp_away"),
            sp_home_id=int(payload["sp_home_id"]) if payload.get("sp_home_id") is not None else None,
            sp_away_id=int(payload["sp_away_id"]) if payload.get("sp_away_id") is not None else None,
            lineup_confidence_home=float(payload.get("lineup_confidence_home") or 0.85),
            lineup_confidence_away=float(payload.get("lineup_confidence_away") or 0.85),
            source=str(payload.get("source") or "context"),
            extras=dict(payload.get("extras") or {}),
        )


def lineup_hash_from_card(
    *,
    known_home: int,
    known_away: int,
    sp_home: Optional[str],
    sp_away: Optional[str],
    lineup_confirmed: bool,
) -> str:
    raw = "|".join(
        [
            str(int(known_home)),
            str(int(known_away)),
            str(sp_home or ""),
            str(sp_away or ""),
            "1" if lineup_confirmed else "0",
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def nearest_hours_tier(hours_to_first_pitch: float) -> float:
    h = max(0.0, float(hours_to_first_pitch))
    return min(SNAPSHOT_HOURS_TIERS, key=lambda t: abs(t - h))


def is_late_info_snapshot(
    snap: LineupSpSnapshot,
    *,
    max_hours: float = 3.0,
    require_confirmed: bool = True,
) -> bool:
    if float(snap.hours_to_first_pitch) > float(max_hours) + 1e-9:
        return False
    if require_confirmed and not bool(snap.lineup_confirmed):
        # Soft late-info: both SP named + ≥6 known per side counts as late card.
        if int(snap.known_home) < 6 or int(snap.known_away) < 6:
            return False
        if not snap.sp_home or not snap.sp_away:
            return False
    return True


def build_snapshot(
    *,
    game_id: str,
    hours_to_first_pitch: float,
    known_home: int,
    known_away: int,
    sp_home: Optional[str],
    sp_away: Optional[str],
    lineup_confirmed: bool,
    lineup_confidence_home: float = 0.85,
    lineup_confidence_away: float = 0.85,
    observed_at: Optional[datetime] = None,
    source: str = "context",
    sp_home_id: Optional[int] = None,
    sp_away_id: Optional[int] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> LineupSpSnapshot:
    obs = observed_at or datetime.now(timezone.utc)
    if obs.tzinfo is None:
        obs = obs.replace(tzinfo=timezone.utc)
    return LineupSpSnapshot(
        game_id=str(game_id),
        observed_at=obs.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        hours_to_first_pitch=round(float(hours_to_first_pitch), 3),
        lineup_hash=lineup_hash_from_card(
            known_home=known_home,
            known_away=known_away,
            sp_home=sp_home,
            sp_away=sp_away,
            lineup_confirmed=lineup_confirmed,
        ),
        lineup_confirmed=bool(lineup_confirmed),
        known_home=int(known_home),
        known_away=int(known_away),
        sp_home=sp_home,
        sp_away=sp_away,
        sp_home_id=sp_home_id,
        sp_away_id=sp_away_id,
        lineup_confidence_home=float(lineup_confidence_home),
        lineup_confidence_away=float(lineup_confidence_away),
        source=source,
        extras=dict(extras or {}),
    )


def _game_path(game_id: str) -> Path:
    LAKE_DIR.mkdir(parents=True, exist_ok=True)
    safe = str(game_id).replace("/", "_")
    return LAKE_DIR / f"{safe}.jsonl"


def persist_snapshot(snap: LineupSpSnapshot) -> Path:
    path = _game_path(snap.game_id)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snap.to_dict(), separators=(",", ":")) + "\n")
    return path


def load_snapshots(game_id: str) -> List[LineupSpSnapshot]:
    path = _game_path(game_id)
    if not path.exists():
        return []
    out: List[LineupSpSnapshot] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(LineupSpSnapshot.from_dict(json.loads(line)))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return out


def latest_snapshot_at_or_before(
    game_id: str,
    *,
    hours_to_first_pitch: float,
) -> Optional[LineupSpSnapshot]:
    """Most informative snapshot with hours_to_pitch >= target (earlier or equal)."""
    snaps = load_snapshots(game_id)
    if not snaps:
        return None
    target = float(hours_to_first_pitch)
    # Prefer snapshots taken at/after the target horizon (smaller hours = later).
    candidates = [s for s in snaps if float(s.hours_to_first_pitch) <= target + 0.25]
    if not candidates:
        # Fall back to earliest available (largest hours).
        return max(snaps, key=lambda s: float(s.hours_to_first_pitch))
    return min(candidates, key=lambda s: float(s.hours_to_first_pitch))


def reconstruct_densify_snapshot(
    *,
    game_id: str,
    hours_to_first_pitch: float,
    known_home: int,
    known_away: int,
    sp_home: Optional[str],
    sp_away: Optional[str],
    lineup_confirmed: bool,
    lineup_confidence_home: float = 0.85,
    lineup_confidence_away: float = 0.85,
    start_time: Optional[datetime] = None,
    persist: bool = True,
) -> LineupSpSnapshot:
    """Build densify-time snapshot from context card (no live ladder).

    When lineup is confirmed on densify cards, treat as available at the stamp
    horizon (historical Stats API does not expose the true confirm clock).
    """
    h = float(hours_to_first_pitch)
    # Soften unconfirmed cards at early stamps — known_players stay, flag false.
    confirmed = bool(lineup_confirmed)
    if h > 6.0 and not confirmed:
        known_home = min(int(known_home), 3)
        known_away = min(int(known_away), 3)
    elif h > 3.0 and not confirmed:
        known_home = min(int(known_home), 6)
        known_away = min(int(known_away), 6)

    obs = None
    if start_time is not None:
        st = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        from datetime import timedelta

        obs = st - timedelta(hours=h)

    snap = build_snapshot(
        game_id=game_id,
        hours_to_first_pitch=h,
        known_home=known_home,
        known_away=known_away,
        sp_home=sp_home,
        sp_away=sp_away,
        lineup_confirmed=confirmed and h <= 6.0,
        lineup_confidence_home=lineup_confidence_home,
        lineup_confidence_away=lineup_confidence_away,
        observed_at=obs,
        source="densify_reconstruct",
        extras={"tier": nearest_hours_tier(h)},
    )
    if persist:
        persist_snapshot(snap)
    return snap


def late_info_game_ids(
    snapshots_by_game: Dict[str, Sequence[LineupSpSnapshot]],
    *,
    max_hours: float = 3.0,
) -> List[str]:
    out: List[str] = []
    for gid, snaps in snapshots_by_game.items():
        if any(is_late_info_snapshot(s, max_hours=max_hours) for s in snaps):
            out.append(str(gid))
    return sorted(out)


def summarize_late_info_slice(
    game_ids: Iterable[str],
    *,
    max_hours: float,
    as_of_date: Optional[date] = None,
) -> Dict[str, Any]:
    ids = sorted({str(g) for g in game_ids})
    late: List[str] = []
    for gid in ids:
        snaps = load_snapshots(gid)
        if any(is_late_info_snapshot(s, max_hours=max_hours) for s in snaps):
            late.append(gid)
    return {
        "max_hours": float(max_hours),
        "universe_n": len(ids),
        "late_info_n": len(late),
        "late_info_game_ids": late,
        "as_of_date": as_of_date.isoformat() if as_of_date else None,
        "lake_dir": str(LAKE_DIR),
    }


def inventory_snapshot_lake(*, max_hours: float = 3.0) -> Dict[str, Any]:
    """Scan on-disk lake for live confirms (excludes densify_reconstruct)."""
    LAKE_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(LAKE_DIR.glob("*.jsonl"))
    live_games = 0
    late_live: List[str] = []
    densify_only = 0
    total_snaps = 0
    for path in files:
        snaps = load_snapshots(path.stem)
        if not snaps:
            continue
        total_snaps += len(snaps)
        live = [s for s in snaps if str(s.source) != "densify_reconstruct"]
        if not live:
            densify_only += 1
            continue
        live_games += 1
        if any(is_late_info_snapshot(s, max_hours=max_hours) for s in live):
            late_live.append(path.stem)
    return {
        "lake_dir": str(LAKE_DIR),
        "jsonl_files": len(files),
        "total_snapshots": total_snaps,
        "live_source_games": live_games,
        "densify_reconstruct_only_games": densify_only,
        "late_info_live_n": len(late_live),
        "late_info_live_game_ids": sorted(late_live),
        "max_hours": float(max_hours),
        "note": (
            "Live ≤3h CLV requires nowcast-persisted confirms. Densify reconstruct "
            "cannot invent confirm clocks; n=0 means needs live accumulation."
        ),
    }
