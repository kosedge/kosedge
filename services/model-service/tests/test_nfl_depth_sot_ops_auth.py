"""Internal auth contract for DepthSot ops — no public accept UI.

Avoids booting full FastAPI app (heavy deps). Locks the source contract.
"""

from __future__ import annotations

from pathlib import Path


NFL_ROUTES = Path(__file__).resolve().parents[1] / "src" / "routes" / "nfl.py"


def test_depth_sot_ops_routes_require_internal_secret() -> None:
    text = NFL_ROUTES.read_text(encoding="utf-8")
    assert "def _require_kosedge_internal" in text
    assert 'headers.get("x-kosedge-secret")' in text
    assert 'raise HTTPException(status_code=401' in text
    assert '@router.get("/ops/depth-sot/status")' in text
    assert '@router.post("/ops/depth-sot/accept")' in text
    assert '@router.post("/ops/depth-sot/reject")' in text
    assert '@router.post("/ops/depth-sot/no-change")' in text
    assert '"public_accept_ui": False' in text
    # Accept path must call the secret gate.
    accept_block = text.split("def nfl_depth_sot_accept")[1].split("def nfl_depth_sot_reject")[0]
    assert "_require_kosedge_internal(request)" in accept_block
