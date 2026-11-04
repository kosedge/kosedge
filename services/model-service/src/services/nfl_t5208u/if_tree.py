"""HARD IF-tree preflight. Never fetch, worktree-add, or call ensure_if_tree."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from src.services.nfl_t5208u.pins import (
    DEFAULT_IF_TREES,
    FW_SHA256,
    IF_TIP,
    SIM_SHA256,
)


class IFTreeBlocker(RuntimeError):
    """Verified IF source tree is absent or pin-mismatched."""


class EnsureIfTreeForbidden(RuntimeError):
    """ensure_if_tree auto-mount is forbidden on t5208u."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def in_repo_if_tree() -> Path:
    """model-service root that already holds nfl_simulator.py / framework."""
    return Path(__file__).resolve().parents[3]


def default_if_trees_status() -> list[dict[str, Any]]:
    rows = []
    for raw in DEFAULT_IF_TREES:
        path = Path(raw)
        rows.append(
            {
                "path": raw,
                "exists": path.exists(),
                "sim_present": (path / "services/model-service/src/services/nfl_simulator.py").is_file()
                or (path / "src/services/nfl_simulator.py").is_file(),
            }
        )
    return rows


def _forbidden_ensure_if_tree(*_args: Any, **_kwargs: Any) -> Path:
    raise EnsureIfTreeForbidden(
        "t5208u forbids if_produce auto-mount of the IF tip "
        f"{IF_TIP} (no remote checkout, no worktree mount)"
    )


def disable_ensure_if_tree() -> None:
    from src.services.nfl_t5107u import if_produce

    if_produce.ensure_if_tree = _forbidden_ensure_if_tree  # type: ignore[assignment]


def preflight_if_tree() -> dict[str, Any]:
    """Require an already-present pin-matched IF source tree.

    DEFAULT_IF_TREES mounts are not used and are not created. The in-repo
    model-service tree is accepted only when simulator + framework content
    hashes match the frozen pins. T5108U_IF_TREE is a bypass and is refused.
    """
    if os.environ.get("T5108U_IF_TREE"):
        raise IFTreeBlocker(
            "T5108U_IF_TREE is set — ENV bypass refused. Unset it; "
            "t5208u does not auto-mount an IF tree."
        )
    disable_ensure_if_tree()
    defaults = default_if_trees_status()
    tree = in_repo_if_tree()
    sim = tree / "src" / "services" / "nfl_simulator.py"
    fw = tree / "src" / "services" / "nfl_handicapping_framework.py"
    if not sim.is_file() or not fw.is_file():
        raise IFTreeBlocker(
            "verified IF source tree missing. expected in-repo files "
            f"{sim} and {fw} matching SIM_SHA256={SIM_SHA256} "
            f"FW_SHA256={FW_SHA256}; DEFAULT_IF_TREES={defaults}"
        )
    sim_sha = sha256_file(sim)
    fw_sha = sha256_file(fw)
    if sim_sha != SIM_SHA256 or fw_sha != FW_SHA256:
        raise IFTreeBlocker(
            "IF source tree present but pin mismatch: "
            f"sim={sim_sha} expected {SIM_SHA256}; "
            f"fw={fw_sha} expected {FW_SHA256}; "
            f"DEFAULT_IF_TREES={defaults}"
        )
    return {
        "status": "PRESENT_PIN_MATCH",
        "if_tip": IF_TIP,
        "tree_path": str(tree),
        "simulator_path": str(sim),
        "framework_path": str(fw),
        "sim_sha256": sim_sha,
        "fw_sha256": fw_sha,
        "default_if_trees": defaults,
        "default_if_trees_used": False,
        "ensure_if_tree_called": False,
        "t5108u_if_tree_env": None,
    }
