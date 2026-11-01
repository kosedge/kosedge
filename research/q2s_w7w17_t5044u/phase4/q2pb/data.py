"""Stream-load games.csv + score-only outcomes. Season firewalls are hard."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .constants import (
    EXPECTED_GAMES_SHA256_PREFIX,
    LABEL,
    SEALED_SEASONS,
)


class DataGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class Game:
    season: int
    week: int
    game_id: str
    home: str
    away: str
    kickoff_utc: datetime
    home_score: float | None
    away_score: float | None
    record_entering_home: str
    record_entering_away: str
    market_spread_home: float | None

    @property
    def margin(self) -> float | None:
        if self.home_score is None or self.away_score is None:
            return None
        return float(self.home_score) - float(self.away_score)

    @property
    def key(self) -> tuple[int, int, str, str]:
        return (self.season, self.week, self.home, self.away)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_games_pin(path: Path) -> str:
    digest = sha256_file(path)
    if not digest.startswith(EXPECTED_GAMES_SHA256_PREFIX):
        raise DataGuardError(
            f"games.csv sha256 {digest[:8]} != required prefix "
            f"{EXPECTED_GAMES_SHA256_PREFIX}; STOP (no new data acquisition)."
        )
    return digest


def _parse_kickoff(raw: str) -> datetime:
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _f(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    return float(raw)


def load_outcomes_score_only(
    path: Path,
    seasons: Sequence[int],
) -> dict[tuple[int, int, str, str], tuple[float, float]]:
    """Load ONLY identity + scores. Reject sealed seasons and extra columns."""
    allowed = set(seasons)
    if set(SEALED_SEASONS) & allowed:
        raise DataGuardError("refusing to load 2024–25 outcomes")
    out: dict[tuple[int, int, str, str], tuple[float, float]] = {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        cols = set(reader.fieldnames or [])
        required = {
            "season",
            "week",
            "home",
            "away",
            "home_score",
            "away_score",
        }
        if not required <= cols:
            raise DataGuardError(f"outcomes missing columns {required - cols}")
        banned = {
            c
            for c in cols
            if c.startswith("trailing_")
            or c.startswith("packaged_")
            or "epa" in c.lower()
            or c.endswith("_err")
        }
        if banned:
            raise DataGuardError(f"outcomes file contains banned columns {banned}")
        for row in reader:
            season = int(row["season"])
            if season in SEALED_SEASONS:
                raise DataGuardError(f"sealed season {season} present in outcomes")
            if season not in allowed:
                continue
            hs, aws = _f(row["home_score"]), _f(row["away_score"])
            if hs is None or aws is None:
                continue
            key = (season, int(row["week"]), row["home"].strip(), row["away"].strip())
            out[key] = (hs, aws)
    return out


def load_games(
    games_path: Path,
    outcomes: dict[tuple[int, int, str, str], tuple[float, float]],
    seasons: Sequence[int],
    *,
    phase: str,
) -> list[Game]:
    """Stream-filter by season so EVAL rows are never materialized in phase1."""
    allowed = set(seasons)
    if set(SEALED_SEASONS) & allowed:
        raise DataGuardError("refusing to load 2024–25 games")
    if phase == "phase1_dev" and any(s >= 2017 for s in allowed):
        raise DataGuardError("phase1_dev cannot include season >= 2017")
    games: list[Game] = []
    skipped_no_score = 0
    with games_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            season = int(row["season"])
            if season in SEALED_SEASONS:
                continue
            if season not in allowed:
                continue
            home = row["home"].strip()
            away = row["away"].strip()
            week = int(row["week"])
            key = (season, week, home, away)
            scores = outcomes.get(key)
            hs = aws = None
            if scores is not None:
                hs, aws = scores
            else:
                skipped_no_score += 1
            games.append(
                Game(
                    season=season,
                    week=week,
                    game_id=row.get("game_id", ""),
                    home=home,
                    away=away,
                    kickoff_utc=_parse_kickoff(row["kickoff_utc"]),
                    home_score=hs,
                    away_score=aws,
                    record_entering_home=row.get("record_entering_home", ""),
                    record_entering_away=row.get("record_entering_away", ""),
                    market_spread_home=_f(row.get("market_spread_home")),
                )
            )
    games.sort(key=lambda g: (g.kickoff_utc, g.game_id))
    if not games:
        raise DataGuardError(f"no games loaded for {phase} seasons={seasons}")
    return games


def scored(games: Iterable[Game]) -> list[Game]:
    return [g for g in games if g.margin is not None]


def window_rows(games: Iterable[Game], seasons: Sequence[int], weeks: Sequence[int]) -> list[Game]:
    sset, wset = set(seasons), set(weeks)
    rows = [g for g in games if g.season in sset and g.week in wset and g.margin is not None]
    return rows


def parse_record(raw: str) -> tuple[int, int, int]:
    parts = [p for p in (raw or "").strip().split("-") if p != ""]
    if len(parts) < 2:
        return 0, 0, 0
    w, l = int(parts[0]), int(parts[1])
    t = int(parts[2]) if len(parts) >= 3 else 0
    return w, l, t


def win_pct(w: int, l: int, t: int) -> float:
    n = w + l + t
    if n <= 0:
        return 0.5
    return (w + 0.5 * t) / n


def label() -> str:
    return LABEL
