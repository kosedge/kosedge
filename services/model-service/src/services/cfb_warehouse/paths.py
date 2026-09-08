"""HD vs repo placement for the CFB historical warehouse.

Bulk history lives on ``/Volumes/KosEdgeData`` when mounted. Repo fallback is
gitignored under ``data/cfb/warehouse/``. Production model-service must not
live-query 20 years of history per request.
"""

from __future__ import annotations

from pathlib import Path

HD_ROOT = Path("/Volumes/KosEdgeData")
HD_RAW = HD_ROOT / "raw" / "cfb" / "historical"
HD_CLEAN = HD_ROOT / "clean" / "cfb" / "historical"
HD_RAW_PBP = HD_ROOT / "raw" / "cfb" / "pbp"
HD_ODDS_CFB = HD_ROOT / "clean" / "odds" / "cfb"

def _resolve_repo_root() -> Path:
    """Monorepo root locally; service root (/app) on Railway path-as-root."""
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
REPO_RAW = REPO_ROOT / "data" / "cfb" / "warehouse" / "raw"
REPO_CLEAN = REPO_ROOT / "data" / "cfb" / "warehouse" / "clean"
REPO_RAW_PBP = REPO_RAW / "pbp"
REPO_ODDS_CFB = REPO_CLEAN / "odds_cfb"


def hd_mounted() -> bool:
    return HD_ROOT.is_dir()


def raw_dir(*, prefer_hd: bool = True) -> Path:
    if prefer_hd and hd_mounted():
        return HD_RAW
    return REPO_RAW


def clean_dir(*, prefer_hd: bool = True) -> Path:
    if prefer_hd and hd_mounted():
        return HD_CLEAN
    return REPO_CLEAN


def pbp_raw_dir(*, prefer_hd: bool = True) -> Path:
    if prefer_hd and hd_mounted():
        return HD_RAW_PBP
    return REPO_RAW_PBP


def odds_lake_dir(*, prefer_hd: bool = True) -> Path:
    if prefer_hd and hd_mounted():
        return HD_ODDS_CFB
    return REPO_ODDS_CFB


def predictions_dir(*, prefer_hd: bool = True, root: Path | None = None) -> Path:
    """Immutable research-fair snapshots (JSON / JSONL / parquet)."""
    if root is not None:
        return Path(root) / "predictions"
    return clean_dir(prefer_hd=prefer_hd) / "predictions"


def ensure_dirs(*, prefer_hd: bool = True) -> tuple[Path, Path]:
    raw = raw_dir(prefer_hd=prefer_hd)
    clean = clean_dir(prefer_hd=prefer_hd)
    raw.mkdir(parents=True, exist_ok=True)
    clean.mkdir(parents=True, exist_ok=True)
    (clean / "pbp").mkdir(parents=True, exist_ok=True)
    predictions_dir(prefer_hd=prefer_hd).mkdir(parents=True, exist_ok=True)
    pbp_raw_dir(prefer_hd=prefer_hd).mkdir(parents=True, exist_ok=True)
    odds_lake_dir(prefer_hd=prefer_hd).mkdir(parents=True, exist_ok=True)
    return raw, clean
