"""Canonical SHA-256 for typed packets. No empty/default substitutions."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def require_sha256_hex(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} is not a full sha256 hex ({value!r})")
    lowered = value.lower()
    if any(ch not in "0123456789abcdef" for ch in lowered):
        raise ValueError(f"{name} is not sha256 hex")
    if lowered == "0" * 64:
        raise ValueError(f"{name} is an empty/default zero hash")
    return lowered


def sha256_file(path: Any) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
