"""Internal auth contract for The Book ops — mirrors DepthSot gate."""

from __future__ import annotations

from pathlib import Path


BOOK_ROUTES = Path(__file__).resolve().parents[1] / "src" / "routes" / "book.py"
OPS_AUTH = Path(__file__).resolve().parents[1] / "src" / "ops_auth.py"


def test_ops_auth_helper_contract() -> None:
    text = OPS_AUTH.read_text(encoding="utf-8")
    assert "def require_kosedge_internal" in text
    assert 'os.environ.get("INTERNAL_API_SECRET")' in text
    assert 'headers.get("x-kosedge-secret")' in text
    assert 'status_code=503' in text
    assert 'status_code=401' in text


def test_book_ops_routes_require_internal_secret() -> None:
    text = BOOK_ROUTES.read_text(encoding="utf-8")
    assert "require_kosedge_internal(request)" in text
    for path in (
        '/ops/book/ping',
        '/ops/book/status',
        '/ops/book/rows',
        '/ops/book/snapshot',
        '/ops/book/cfb/snapshot',
        '/ops/book/metrics',
    ):
        assert path in text
    # Every handler must gate.
    for fn in (
        "def book_ping",
        "def book_status",
        "def book_rows",
        "def book_snapshot",
        "def book_cfb_snapshot",
        "def book_close",
        "def book_settle",
        "def book_metrics",
    ):
        block = text.split(fn)[1].split("def ")[0]
        assert "require_kosedge_internal(request)" in block
