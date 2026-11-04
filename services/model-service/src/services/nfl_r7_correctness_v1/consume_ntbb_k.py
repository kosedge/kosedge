"""A-side NTBB-K consume via producer→capability/gate. CERT=0.

Cos ACCEPT 12c41587 integrated once (RETURN 58427 + ADDITIVE 80649).
a807af22 SUPERSEDED. d0bb6bef refused. Does not rewrite the kernel.
Not a real R7 model arm. Package not closed from B alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.services.nfl_r7_correctness_v1.ntbbk_gate import run_ntbbk_integrate_gate


def consume_ntbb_k(*, root: Path | None = None) -> dict[str, Any]:
    return run_ntbbk_integrate_gate(root=root)
