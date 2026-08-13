"""SportsDataverse fetch — download once, cache locally. Not a live request path."""

from __future__ import annotations

import csv
import gzip
import io
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

SDV_BASE = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
)
USER_AGENT = "kosedge-cfb-historical-warehouse/1.0"


def http_get(url: str, *, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_sdv_file(
    tag: str,
    filename: str,
    *,
    cache_dir: Path,
    timeout: int = 300,
) -> Path:
    """Download-once binary asset (parquet) into cache_dir. Not a live request path."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / filename
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    url = f"{SDV_BASE}/{tag}/{filename}"
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)
    return dest


def fetch_sdv_csv(
    tag: str,
    filename: str,
    *,
    cache_dir: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """Fetch a SportsDataverse release CSV (plain or .gz), with optional cache."""
    cache_path: Optional[Path] = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / filename.replace(".gz", "")
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as fh:
                return list(csv.DictReader(fh))

    url = f"{SDV_BASE}/{tag}/{filename}"
    raw = http_get(url)
    if filename.endswith(".gz"):
        text = gzip.decompress(raw).decode("utf-8", "replace")
    else:
        text = raw.decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if cache_path is not None:
        with cache_path.open("w", encoding="utf-8", newline="") as fh:
            if rows:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
    return rows
