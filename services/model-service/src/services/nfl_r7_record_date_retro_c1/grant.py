"""Future REAL authorization-document loader. CERT=0.

Load/validate a grant file without fabricating GO. REAL stays HOLD until
Root posts the exact approved digest and matching context.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.services.nfl_r7_record_date_retro_c1.refuse import RetroHold, RetroRefuse

# No Root-approved digest has been posted. Do not invent one.
ROOT_APPROVED_AUTH_DIGEST: str | None = None

REQUIRED_GRANT_KEYS = (
    "schema_id",
    "channel",
    "claim_id",
    "context_hash",
    "authorized_now",
)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_authorization_document(path: Path) -> dict[str, Any]:
    if not Path(path).is_file():
        raise RetroRefuse(f"authorization document missing {path}")
    raw = Path(path).read_bytes()
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RetroRefuse("authorization document is not JSON") from exc
    if not isinstance(body, dict):
        raise RetroRefuse("authorization document must be an object")
    missing = [key for key in REQUIRED_GRANT_KEYS if key not in body]
    if missing:
        raise RetroRefuse(f"authorization document missing {missing}")
    digest = sha256_bytes(raw)
    approved = ROOT_APPROVED_AUTH_DIGEST is not None and digest == ROOT_APPROVED_AUTH_DIGEST
    return {
        "path": str(path),
        "digest": digest,
        "root_approved_digest": ROOT_APPROVED_AUTH_DIGEST,
        "digest_matches_root": approved,
        "authorized_now": False,
        "document": body,
        "load_ok": True,
        "grant": False,
    }


def refuse_real_without_root_grant(*, grant: dict[str, Any] | None = None) -> None:
    if grant is None or not grant.get("digest_matches_root"):
        raise RetroHold(
            "REAL mode DENIED — absent Root-approved exact authorization-document "
            "digest + matching context (no fabricated GO)"
        )
    raise RetroHold("REAL mode DENIED — digest loaded but GO not granted this machine")
