"""AC-10: W8 capture must not import the historical rebuild package."""

from __future__ import annotations

import re
from pathlib import Path

_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+\S*nfl_eval_prep", re.MULTILINE)


def historical_rebuild_import_hits(root: Path | None = None) -> list[str]:
    base = Path(root) if root is not None else Path(__file__).resolve().parent
    hits: list[str] = []
    for path in base.rglob("*.py"):
        if path.name == "isolation.py":
            continue
        text = path.read_text(encoding="utf-8")
        if _IMPORT_RE.search(text):
            hits.append(path.name)
    return hits
