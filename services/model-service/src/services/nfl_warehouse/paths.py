"""HD vs repo placement for the NFL odds warehouse lake.

Bulk history lives on ``/Volumes/KosEdgeData``. Repo fallback is gitignored
under ``data/nfl/warehouse/``. Model-service request paths must not live-query
the 13GB SQLite file.
"""

from __future__ import annotations

from pathlib import Path

HD_ROOT = Path("/Volumes/KosEdgeData")
HD_SQLITE = HD_ROOT / "clean" / "odds" / "gapfill" / "odds_gapfill.sqlite"
HD_LAKE = HD_ROOT / "clean" / "odds" / "nfl" / "lake"
HD_PROPS = HD_ROOT / "clean" / "odds" / "americanfootball_nfl" / "props"
HD_OC_CSV = HD_ROOT / "clean" / "odds" / "americanfootball_nfl" / "open_close" / "lines.csv"
HD_SB_CSV = (
    HD_ROOT / "clean" / "odds" / "americanfootball_nfl_super_bowl_winner" / "open_close" / "lines.csv"
)

def _resolve_repo_root() -> Path:
    """Monorepo root locally; service root (/app) on Railway path-as-root.

    ``parents[5]`` is correct for ``services/model-service/src/services/...``
    but IndexErrors when the service is deployed with ``--path-as-root``
    (``/app/src/services/...`` only has four parents).
    """
    here = Path(__file__).resolve()
    parents = list(here.parents)
    for parent in parents:
        if (parent / "services" / "model-service").is_dir() and (parent / "data").is_dir():
            return parent
    for parent in parents:
        if (parent / "Dockerfile").is_file() and (parent / "src").is_dir():
            return parent
    return parents[min(3, len(parents) - 1)]


REPO_ROOT = _resolve_repo_root()
REPO_LAKE = REPO_ROOT / "data" / "nfl" / "warehouse" / "odds_lake"
REPO_SQLITE = REPO_ROOT / "data" / "nfl" / "warehouse" / "odds_gapfill.sqlite"


def hd_mounted() -> bool:
    return HD_ROOT.is_dir()


def sqlite_path(*, prefer_hd: bool = True) -> Path:
    if prefer_hd and HD_SQLITE.is_file():
        return HD_SQLITE
    return REPO_SQLITE


def odds_lake_dir(*, prefer_hd: bool = True) -> Path:
    if prefer_hd and hd_mounted():
        return HD_LAKE
    return REPO_LAKE


def ensure_lake_dir(*, prefer_hd: bool = True) -> Path:
    out = odds_lake_dir(prefer_hd=prefer_hd)
    out.mkdir(parents=True, exist_ok=True)
    return out
