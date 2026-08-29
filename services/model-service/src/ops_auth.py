"""Shared staff/ops gate — same contract as DepthSot.

Header: x-kosedge-secret
Env: INTERNAL_API_SECRET
Empty env → 503; mismatch → 401.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request


def require_kosedge_internal(request: Request) -> str:
    """Staff/ops only. Header: x-kosedge-secret."""
    expected = (os.environ.get("INTERNAL_API_SECRET") or "").strip()
    got = (request.headers.get("x-kosedge-secret") or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="INTERNAL_API_SECRET not configured")
    if not got or got != expected:
        raise HTTPException(status_code=401, detail="internal auth required")
    return "internal"
