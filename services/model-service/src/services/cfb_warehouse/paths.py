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
# Canonical Aug 13 lake (2014–2025). Do not write current-season files here.
HD_RAW_PBP = HD_ROOT / "raw" / "cfb" / "pbp"
# Versioned current-season PBP: raw/cfb/pbp_current/as_of_YYYYMMDD/
HD_RAW_PBP_CURRENT = HD_ROOT / "raw" / "cfb" / "pbp_current"
HD_ODDS_CFB = HD_ROOT / "clean" / "odds" / "cfb"

def _resolve_repo_root() -> Path:
    """Monorepo root locally; service root (/app) on Railway path-as-root.

    Require ``apps/web`` for the monorepo match. ``model-service`` itself can
    contain a nested ``data/`` tree, which used to steal the first match and
    drop current-season parquet under the service instead of repo research.
    """
    here = Path(__file__).resolve()
    parents = list(here.parents)
    for parent in parents:
        if (parent / "apps" / "web").is_dir() and (
            parent / "services" / "model-service"
        ).is_dir():
            return parent
    for parent in parents:
        if (parent / "Dockerfile").is_file() and (parent / "src").is_dir():
            return parent
    return parents[min(3, len(parents) - 1)]


REPO_ROOT = _resolve_repo_root()
REPO_RAW = REPO_ROOT / "data" / "cfb" / "warehouse" / "raw"
REPO_CLEAN = REPO_ROOT / "data" / "cfb" / "warehouse" / "clean"
REPO_RAW_PBP = REPO_RAW / "pbp"
# Gitignored research restore for current-season (mirrors HD pbp_current).
REPO_RESEARCH_PBP_CURRENT = REPO_ROOT / "data" / "cfb" / "research" / "pbp_current"
# Versioned historical *research* restore. Never the Aug 13 HD lake.
REPO_RESEARCH_PBP_HIST = REPO_ROOT / "data" / "cfb" / "research" / "pbp_hist"
HD_RESEARCH_PBP_HIST = HD_ROOT / "raw" / "cfb" / "pbp_research"
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


def pbp_current_as_of_dir(as_of: str, *, prefer_hd: bool = True) -> Path:
    """Versioned 2026+ current-season dir. Never the 2014–2025 historical lake."""
    stamp = _as_of_stamp(as_of)
    if prefer_hd and hd_mounted():
        return HD_RAW_PBP_CURRENT / f"as_of_{stamp}"
    return REPO_RESEARCH_PBP_CURRENT / f"as_of_{stamp}"


def hd_pbp_current_target(as_of: str) -> Path:
    """Documented Mac HD landing path even when this VM cannot mount the disk."""
    return HD_RAW_PBP_CURRENT / f"as_of_{_as_of_stamp(as_of)}"


def pbp_hist_research_dir(as_of: str, *, prefer_hd: bool = False) -> Path:
    """Versioned historical research restore. Never writes the Aug 13 lake."""
    stamp = _as_of_stamp(as_of)
    if prefer_hd and hd_mounted():
        return HD_RESEARCH_PBP_HIST / f"as_of_{stamp}"
    return REPO_RESEARCH_PBP_HIST / f"as_of_{stamp}"


def hd_pbp_hist_research_target(as_of: str) -> Path:
    """Documented Mac HD mirror for historical research restores."""
    return HD_RESEARCH_PBP_HIST / f"as_of_{_as_of_stamp(as_of)}"


def _as_of_stamp(as_of: str) -> str:
    digits = "".join(ch for ch in str(as_of) if ch.isdigit())
    if len(digits) < 8:
        raise ValueError(f"as_of must contain YYYYMMDD, got {as_of!r}")
    return digits[:8]


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
