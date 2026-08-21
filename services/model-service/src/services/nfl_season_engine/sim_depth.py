"""Sim depth defaults, honesty thresholds, and process-local memo caches.

Doctrine: do not publish one-decimal certainty the engine did not earn.
Game Boxes HTTP default stays research-depth n (≥2k) + cache. Survivor
*planner page-load* uses interactive n=50 (web); research 2k–100k stays
CLI / explicit n_sims. Heavy publish bundles are unchanged.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Hashable, Optional, Tuple, TypeVar

# Honesty threshold — 1-decimal WP / stable tails require at least this n.
HONEST_PRECISION_MIN_N = 2000

# Interactive / desk defaults (env-overridable). 5k preferred when latency OK;
# cold Game Boxes ~65s@2k / ~186s@5k on demo → ship 2k + cache.
_DEFAULT_N_GAME_BOX = 2000
_DEFAULT_N_SURVIVOR = 2000

# Explicit thin/dev fallback (must be labeled in UI).
THIN_N_GAME_BOX = 50
THIN_N_SURVIVOR_PATHS = 120

# HTTP / interactive caps (research publish stays on CLI).
MAX_N_GAME_BOX = 10_000
MAX_N_SURVIVOR_PATHS = 20_000

T = TypeVar("T")


def _env_int(name: str, default: int, *, min_v: int = 1, max_v: int = 10_000_000) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return max(min_v, min(max_v, int(raw)))
    except (TypeError, ValueError):
        return default


def thin_depth_enabled() -> bool:
    """Dev/CI thin mode — lower n, must surface as low-depth estimate."""
    flag = (os.getenv("NFL_SEASON_ENGINE_THIN_DEPTH") or "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def default_n_game_box() -> int:
    if thin_depth_enabled():
        return _env_int(
            "NFL_SEASON_ENGINE_N_GAME_BOX",
            THIN_N_GAME_BOX,
            min_v=1,
            max_v=MAX_N_GAME_BOX,
        )
    return _env_int(
        "NFL_SEASON_ENGINE_N_GAME_BOX",
        _DEFAULT_N_GAME_BOX,
        min_v=1,
        max_v=MAX_N_GAME_BOX,
    )


def default_n_survivor_paths() -> int:
    if thin_depth_enabled():
        return _env_int(
            "NFL_SEASON_ENGINE_N_SURVIVOR_PATHS",
            THIN_N_SURVIVOR_PATHS,
            min_v=1,
            max_v=MAX_N_SURVIVOR_PATHS,
        )
    return _env_int(
        "NFL_SEASON_ENGINE_N_SURVIVOR_PATHS",
        _DEFAULT_N_SURVIVOR,
        min_v=1,
        max_v=MAX_N_SURVIVOR_PATHS,
    )


# Public knob aliases (brief naming).
n_game_box = default_n_game_box
n_survivor_paths = default_n_survivor_paths


def resolve_n_game_box(requested: Optional[int] = None) -> int:
    if requested is None:
        return default_n_game_box()
    try:
        n = int(requested)
    except (TypeError, ValueError):
        return default_n_game_box()
    return max(1, min(MAX_N_GAME_BOX, n))


def resolve_n_survivor_paths(requested: Optional[int] = None) -> int:
    if requested is None:
        return default_n_survivor_paths()
    try:
        n = int(requested)
    except (TypeError, ValueError):
        return default_n_survivor_paths()
    return max(1, min(MAX_N_SURVIVOR_PATHS, n))


def is_honest_precision(n: int) -> bool:
    return int(n) >= HONEST_PRECISION_MIN_N


def depth_label(n: int) -> str:
    if is_honest_precision(n):
        return "research depth"
    return "low-depth estimate"


def depth_meta(n: int, *, surface: str) -> Dict[str, Any]:
    n_i = int(n)
    return {
        "surface": surface,
        "n": n_i,
        "honest_precision": is_honest_precision(n_i),
        "depth_label": depth_label(n_i),
        "honest_precision_min_n": HONEST_PRECISION_MIN_N,
        "thin_depth": thin_depth_enabled() and not is_honest_precision(n_i),
    }


def universe_cache_fingerprint(universe: Any) -> str:
    """Stable cache identity: run/snapshot + roster as-of (never cross-serve games)."""
    notes = getattr(universe, "notes", None) or {}
    if not isinstance(notes, dict):
        notes = {}
    parts = {
        "season": int(getattr(universe, "season", 0) or 0),
        "run_id": str(
            notes.get("run_id")
            or notes.get("active_run_id")
            or notes.get("bundle_id")
            or ""
        ),
        "snapshot_id": str(notes.get("snapshot_id") or ""),
        "roster_as_of": str(notes.get("roster_as_of") or notes.get("depth_as_of") or ""),
        "roster_source": str(notes.get("roster_source") or notes.get("depth_source") or ""),
        "schedule_source": str(notes.get("schedule_source") or ""),
        "mode": str(notes.get("mode") or ""),
        "teams": tuple(getattr(universe, "teams", []) or []),
        "n_schedule": len(getattr(universe, "schedule", []) or []),
    }
    blob = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def scenario_hash(injury_paths: Any = None, **extra: Any) -> str:
    """Hash injury / scenario knobs for cache keys."""
    try:
        from src.services.nfl_season_engine.injury_paths import injury_paths_to_dicts

        paths = injury_paths_to_dicts(list(injury_paths or []))
    except Exception:
        paths = list(injury_paths or []) if injury_paths else []
    payload = {"injury_paths": paths, **extra}
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]


def prob_to_american(p: float) -> Optional[int]:
    """American odds for probability ``p`` in (0, 1)."""
    try:
        prob = float(p)
    except (TypeError, ValueError):
        return None
    if not (0.0 < prob < 1.0):
        return None
    if prob >= 0.5:
        return int(round(-100.0 * prob / (1.0 - prob)))
    return int(round(100.0 * (1.0 - prob) / prob))


class _TtlLruCache:
    """Small process-local TTL LRU (thread-safe)."""

    def __init__(self, maxsize: int = 64, ttl_s: float = 3600.0) -> None:
        self.maxsize = max(1, int(maxsize))
        self.ttl_s = float(ttl_s)
        self._data: "OrderedDict[Hashable, Tuple[float, Any]]" = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: Hashable) -> Any:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                self.misses += 1
                return None
            ts, value = item
            if self.ttl_s > 0 and (time.time() - ts) > self.ttl_s:
                del self._data[key]
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.time(), value)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "size": len(self._data),
                "hits": self.hits,
                "misses": self.misses,
                "maxsize": self.maxsize,
            }


_GAME_BOX_CACHE = _TtlLruCache(
    maxsize=_env_int("NFL_SEASON_ENGINE_GAME_BOX_CACHE_SIZE", 48, min_v=1, max_v=512),
    ttl_s=float(
        _env_int("NFL_SEASON_ENGINE_GAME_BOX_CACHE_TTL_S", 3600, min_v=30, max_v=86_400)
    ),
)

_SURVIVOR_POOL_CACHE = _TtlLruCache(
    maxsize=_env_int("NFL_SEASON_ENGINE_SURVIVOR_CACHE_SIZE", 16, min_v=1, max_v=128),
    ttl_s=float(
        _env_int("NFL_SEASON_ENGINE_SURVIVOR_CACHE_TTL_S", 3600, min_v=30, max_v=86_400)
    ),
)

# Empty already_used plan / week ranks (short TTL; busts with universe fingerprint).
_SURVIVOR_EMPTY_RESULT_CACHE = _TtlLruCache(
    maxsize=_env_int("NFL_SEASON_ENGINE_SURVIVOR_EMPTY_CACHE_SIZE", 24, min_v=1, max_v=128),
    ttl_s=float(
        _env_int("NFL_SEASON_ENGINE_SURVIVOR_EMPTY_CACHE_TTL_S", 600, min_v=30, max_v=86_400)
    ),
)


def game_box_cache_get(key: Hashable) -> Any:
    return _GAME_BOX_CACHE.get(key)


def game_box_cache_set(key: Hashable, value: Any) -> None:
    _GAME_BOX_CACHE.set(key, value)


def survivor_pool_cache_get(key: Hashable) -> Any:
    return _SURVIVOR_POOL_CACHE.get(key)


def survivor_pool_cache_set(key: Hashable, value: Any) -> None:
    _SURVIVOR_POOL_CACHE.set(key, value)


def survivor_empty_result_cache_get(key: Hashable) -> Any:
    return _SURVIVOR_EMPTY_RESULT_CACHE.get(key)


def survivor_empty_result_cache_set(key: Hashable, value: Any) -> None:
    _SURVIVOR_EMPTY_RESULT_CACHE.set(key, value)


def clear_sim_depth_caches() -> None:
    _GAME_BOX_CACHE.clear()
    _SURVIVOR_POOL_CACHE.clear()
    _SURVIVOR_EMPTY_RESULT_CACHE.clear()


def cache_stats() -> Dict[str, Any]:
    return {
        "game_boxes": _GAME_BOX_CACHE.stats(),
        "survivor_pools": _SURVIVOR_POOL_CACHE.stats(),
        "survivor_empty_results": _SURVIVOR_EMPTY_RESULT_CACHE.stats(),
    }


def memoized(cache: _TtlLruCache, key: Hashable, factory: Callable[[], T]) -> Tuple[T, bool]:
    hit = cache.get(key)
    if hit is not None:
        return hit, True
    value = factory()
    cache.set(key, value)
    return value, False
