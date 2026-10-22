"""K-4: route-(b) IMPORT-TIME closure pin for IMV pure-diff.

The closure is the 33 ``src.services*`` modules loaded when the frozen
scripts ``nfl_simulator`` and ``nfl_season_engine`` are imported in a
clean process. It is not an on-disk folder listing.

Lazy / not import-time (dropped unless a future import-time edge appears):
``adjusted_sos``, ``coaching_staff``, ``continuity_score``,
``historical_replay``, ``qb_premium``.

Reproduce::

    PYTHONPATH=services/model-service python -m src.services.nfl_eval_prep.route_b_closure

or ``python scripts/nfl/route_b_import_closure.py``.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
MODEL_SERVICE = Path(__file__).resolve().parents[3]
CLOSURE_LISTING = REPO_ROOT / "docs" / "research" / "NFL_ROUTE_B_IMPORT_CLOSURE_SHA256.md"

FROZEN_ENTRYPOINTS = (
    "src.services.nfl_simulator",
    "src.services.nfl_season_engine",
)

# On-disk engine files that must not appear unless they really load at import time.
LAZY_ENGINE_MODULES = frozenset(
    {
        "adjusted_sos.py",
        "coaching_staff.py",
        "continuity_score.py",
        "historical_replay.py",
        "qb_premium.py",
    }
)

REQUIRED_RELPATHS = (
    "services/model-service/src/services/__init__.py",
    "services/model-service/src/services/nfl_second_order_factors.py",
    "services/model-service/src/services/nfl_canonical_teams.py",
)

EXPECTED_MODULE_COUNT = 33

_PROBE = r"""
import importlib
import sys
from pathlib import Path

workspace = Path({workspace!r})
for name in {entries!r}:
    importlib.import_module(name)
paths = []
for mod in sys.modules.values():
    raw = getattr(mod, "__file__", None)
    if not raw:
        continue
    path = Path(raw).resolve()
    if path.suffix != ".py":
        continue
    try:
        rel = path.relative_to(workspace)
    except ValueError:
        continue
    if str(rel).startswith("services/model-service/src/services"):
        paths.append(str(rel).replace("\\\\", "/"))
for rel in sorted(set(paths)):
    print(rel)
"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_head_commit() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "UNKNOWN"
    return proc.stdout.strip()


def collect_import_time_relpaths() -> list[str]:
    """Import frozen scripts in a clean process; return workspace-relative paths."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(MODEL_SERVICE) + (os.pathsep + existing if existing else "")
    script = _PROBE.format(workspace=str(REPO_ROOT), entries=FROZEN_ENTRYPOINTS)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "K-4 import-time probe failed:\n"
            f"{proc.stderr or proc.stdout}"
        )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def listed_rows() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for rel in collect_import_time_relpaths():
        path = REPO_ROOT / rel
        rows.append((rel.replace("\\", "/"), sha256_file(path)))
    return rows


def render_listing(*, head_commit: str | None = None) -> str:
    rows = listed_rows()
    head = head_commit or current_head_commit()
    lines = [
        "# Route-(b) import-time closure (33 modules)",
        "",
        f"head: `{head}`",
        "",
        "K-4 pin for IMV pure-diff. IMPORT-TIME closure of the frozen scripts",
        "`src.services.nfl_simulator` and `src.services.nfl_season_engine`.",
        "Hashes are SHA-256 of on-disk bytes. Not a gate. Not W8 RA acceptance.",
        "Not an on-disk folder listing of `nfl_season_engine/`.",
        "",
        "Reproduce: `PYTHONPATH=services/model-service python -m "
        "src.services.nfl_eval_prep.route_b_closure`",
        "or `python scripts/nfl/route_b_import_closure.py`.",
        "",
        "Dropped unless they load at import time:",
        "`adjusted_sos`, `coaching_staff`, `continuity_score`,",
        "`historical_replay`, `qb_premium`.",
        "",
        "| path | sha256 |",
        "| --- | --- |",
    ]
    for rel, digest in rows:
        lines.append(f"| `{rel}` | `{digest}` |")
    lines.append("")
    lines.append(f"module_count: {len(rows)}")
    lines.append("")
    return "\n".join(lines)


def write_listing(*, head_commit: str | None = None) -> Path:
    CLOSURE_LISTING.parent.mkdir(parents=True, exist_ok=True)
    CLOSURE_LISTING.write_text(render_listing(head_commit=head_commit), encoding="utf-8")
    return CLOSURE_LISTING


def main(argv: list[str] | None = None) -> int:
    _ = argv
    path = write_listing()
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
