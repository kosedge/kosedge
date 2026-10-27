"""Explicit AC-8 / AC-10 carve-outs for Ryan / IMV. Not silent stubs.

These items are out of this draft on purpose. The PR body must surface them.
Do not invent Filing-E baselines or a performer-side grader.
"""

from __future__ import annotations

from typing import Any

AC8_FILING_E_BASELINES: dict[str, Any] = {
    "id": "AC-8",
    "status": "EXPLICIT_CARVE_OUT",
    "title": "Filing-E baselines",
    "reason": (
        "Filing-E baselines are not adopted in this W8 prospective-capture draft. "
        "No baseline numbers are invented."
    ),
    "authority": "Ryan t4455u / IMV RETURN sealing-controls (sha8 e5c84d60) item 6",
}

AC10_BLIND_GRADING: dict[str, Any] = {
    "id": "AC-10",
    "status": "EXPLICIT_CARVE_OUT",
    "title": "Blind grading",
    "reason": (
        "Performers do not grade. P-evidence restore stays eval=not_run. "
        "Blind grading is IMV / custodian after first sealed capture verify."
    ),
    "authority": "Ryan t4455u / IMV RETURN sealing-controls (sha8 e5c84d60) item 6",
}

EXPLICIT_CARVE_OUTS = (AC8_FILING_E_BASELINES, AC10_BLIND_GRADING)


def explicit_carve_outs() -> list[dict[str, Any]]:
    return [dict(item) for item in EXPLICIT_CARVE_OUTS]


def require_explicit_carve_out(ac_id: str) -> dict[str, Any]:
    for item in EXPLICIT_CARVE_OUTS:
        if item["id"] == ac_id:
            if item["status"] != "EXPLICIT_CARVE_OUT":
                raise RuntimeError(f"{ac_id} is not an explicit carve-out")
            return dict(item)
    raise KeyError(ac_id)
