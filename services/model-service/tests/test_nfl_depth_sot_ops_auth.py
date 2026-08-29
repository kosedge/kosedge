"""Internal auth contract for DepthSot ops — no public accept UI.

Avoids booting full FastAPI app (heavy deps). Locks the source contract.
"""

from __future__ import annotations

from pathlib import Path

from src.services.nfl_camp_sot_queue import _resolve_repo_root


NFL_ROUTES = Path(__file__).resolve().parents[1] / "src" / "routes" / "nfl.py"


def test_resolve_repo_root_path_as_root_no_indexerror() -> None:
    """Railway /app/src/services only has parents[0..2] — must not IndexError."""
    shallow = Path("/app/src/services")
    assert len(shallow.parents) == 3  # indices 0..2; parents[3] would IndexError
    root = _resolve_repo_root(shallow)
    assert root in {Path("/app"), Path("/"), Path.cwd()}


def test_depth_sot_ops_routes_require_internal_secret() -> None:
    text = NFL_ROUTES.read_text(encoding="utf-8")
    assert "def _require_kosedge_internal" in text
    # Single env name + header; strip both sides; empty env → 503, mismatch → 401.
    gate = text.split("def _require_kosedge_internal")[1].split("class DepthSotDispositionBody")[0]
    assert 'os.environ.get("INTERNAL_API_SECRET")' in gate
    assert 'headers.get("x-kosedge-secret")' in gate
    assert ".strip()" in gate
    assert 'status_code=503' in gate and "INTERNAL_API_SECRET not configured" in gate
    assert 'status_code=401' in gate and "internal auth required" in gate
    assert "got != expected" in gate
    assert '@router.get("/ops/depth-sot/status")' in text
    assert '@router.get("/ops/depth-sot/ping")' in text
    assert '@router.post("/ops/depth-sot/accept")' in text
    assert '@router.post("/ops/depth-sot/queue")' in text
    assert '@router.post("/ops/depth-sot/reject")' in text
    assert '@router.post("/ops/depth-sot/no-change")' in text
    assert '"public_accept_ui": False' in text
    # Accept path must call the secret gate + live remat hook (not receipt-only default).
    accept_block = text.split("def nfl_depth_sot_accept")[1].split("def nfl_depth_sot_queue")[0]
    assert "_require_kosedge_internal(request)" in accept_block
    assert "live_remat_fn" in accept_block
