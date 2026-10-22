"""K-4: route-(b) import-time closure pin for IMV pure-diff.

The closure is the 33 ``nfl_season_engine`` modules. This listing is
documentation, not a gate. Regenerated from on-disk bytes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ENGINE_DIR = (
    Path(__file__).resolve().parents[1] / "nfl_season_engine"
)
SERVICES_DIR = Path(__file__).resolve().parents[1]
CLOSURE_LISTING = (
    Path(__file__).resolve().parents[5]
    / "docs"
    / "research"
    / "NFL_ROUTE_B_IMPORT_CLOSURE_SHA256.md"
)
SIBLING_ENGINE_FILES = (
    "nfl_simulator.py",
    "nfl_handicapping_framework.py",
    "nfl_tendency_pricing.py",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def listed_rows() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for path in sorted(ENGINE_DIR.glob("*.py")):
        rel = f"services/model-service/src/services/nfl_season_engine/{path.name}"
        rows.append((rel, sha256_file(path)))
    return rows


def render_listing() -> str:
    rows = listed_rows()
    lines = [
        "# Route-(b) import-time closure (33 modules)",
        "",
        "K-4 pin for IMV pure-diff. Package: `src.services.nfl_season_engine`.",
        "Hashes are SHA-256 of on-disk bytes. Not a gate. Not W8 RA acceptance.",
        "",
        "This head also changed sibling engine modules treated as in-closure:",
        "`nfl_simulator.py`, `nfl_handicapping_framework.py`, `nfl_tendency_pricing.py`.",
        "",
        "| path | sha256 |",
        "| --- | --- |",
    ]
    for rel, digest in rows:
        lines.append(f"| `{rel}` | `{digest}` |")
    lines.append("")
    lines.append(f"module_count: {len(rows)}")
    lines.append("")
    lines.append("## Sibling engine modules changed on this head")
    lines.append("")
    lines.append("| path | sha256 |")
    lines.append("| --- | --- |")
    for name in SIBLING_ENGINE_FILES:
        path = SERVICES_DIR / name
        rel = f"services/model-service/src/services/{name}"
        lines.append(f"| `{rel}` | `{sha256_file(path)}` |")
    lines.append("")
    return "\n".join(lines)


def write_listing() -> Path:
    CLOSURE_LISTING.parent.mkdir(parents=True, exist_ok=True)
    CLOSURE_LISTING.write_text(render_listing(), encoding="utf-8")
    return CLOSURE_LISTING
