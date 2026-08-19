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

REPO_ROOT = Path(__file__).resolve().parents[5]
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
