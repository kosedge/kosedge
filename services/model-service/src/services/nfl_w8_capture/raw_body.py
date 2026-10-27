"""Persist exact Odds HTTP body bytes for NEW prospective seal dests.

IMV_ACCEPT_DESIGN 91ead2d8 section A (t4540u N5 / req 6). Hash with the
same function as fetch.raw_body_sha256, write EXACT body_bytes via
BundleStore.write_new_file to raw/odds/<game_id>.body, then regenerate
SHA256SUMS. Fail closed on write failure or rehash mismatch.

First-seal dest w8_first_seal_b_t4525u_a896cfd0 is IMMUTABLE — this
module refuses that slug. No secrets in the sidecar meta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from src.services.nfl_w8_capture.evidence import SUMS_FILENAME
from src.services.nfl_w8_capture.fetch import raw_body_sha256
from src.services.nfl_w8_capture.redact import redact_secrets
from src.services.nfl_w8_capture.store import BundleStore

# N2/N3 first-seal dest. Do not backfill. Hash 2ac59ba5… stays provenance-only.
FIRST_SEAL_DEST_SLUG = "w8_first_seal_b_t4525u_a896cfd0"
RAW_ODDS_DIR = "raw/odds"


class RawBodyRetentionError(RuntimeError):
    """Raw body write failed or H != sha256 of written file. Fail closed."""


def safe_game_token(game_id: str) -> str:
    token = "".join(
        ch if ch.isalnum() or ch in "-_@" else "_" for ch in str(game_id or "").strip()
    )
    return token or "slate"


def raw_odds_body_relpath(game_id: str) -> str:
    return f"{RAW_ODDS_DIR}/{safe_game_token(game_id)}.body"


def raw_odds_meta_relpath(game_id: str) -> str:
    return f"{RAW_ODDS_DIR}/{safe_game_token(game_id)}.body.meta.json"


def refuse_first_seal_dest(store: BundleStore) -> None:
    """Refuse any write into the immutable first-seal CAR@GB dest."""
    root = store.root.resolve()
    parts = set(root.parts)
    if FIRST_SEAL_DEST_SLUG in parts or FIRST_SEAL_DEST_SLUG in str(root):
        raise RawBodyRetentionError(
            f"refuse write into first-seal dest {FIRST_SEAL_DEST_SLUG} "
            "(immutable 555; raw body NOT RETAINED gap stands)"
        )


def assert_written_body_matches(path: Path, expected_h: str) -> str:
    """Rehash written file bytes with fetch.raw_body_sha256. Fail closed."""
    if not path.is_file():
        raise RawBodyRetentionError(f"raw body missing after write: {path}")
    got = raw_body_sha256(path.read_bytes())
    if got != expected_h:
        raise RawBodyRetentionError(
            "raw body sha256 mismatch vs written file; no seal; no raw-retention claim"
        )
    return got


def sha256sums_membership(store: BundleStore) -> dict[str, str]:
    """Parse SHA256SUMS as {relpath: sha256}. Empty if the file is missing."""
    path = store.root / SUMS_FILENAME
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        if name.startswith("*"):
            name = name[1:]
        out[name.strip()] = digest.strip()
    return out


def assert_sha256sums_lists(store: BundleStore, relpath: str, expected_h: str) -> None:
    listed = sha256sums_membership(store)
    got = listed.get(relpath)
    if got != expected_h:
        raise RawBodyRetentionError(
            f"SHA256SUMS missing or mismatch for {relpath}; no raw-retention claim"
        )


def persist_raw_odds_body(
    store: BundleStore,
    *,
    game_id: str,
    body_bytes: bytes,
    expected_h: str,
    response_headers: Optional[Mapping[str, Any]] = None,
    request_params: Optional[Mapping[str, Any]] = None,
    endpoint: str = "",
    provider_server_ts: Optional[str] = None,
    client_received_at: Optional[str] = None,
    tip_sha: str = "",
    capture_receipt_id: str = "",
    actor: str = "nfl_w8_capture",
) -> dict[str, Any]:
    """Write exact body bytes + sidecar meta. SHA256SUMS last. Fail closed."""
    refuse_first_seal_dest(store)
    data = bytes(body_bytes)
    hashed = raw_body_sha256(data)
    if hashed != expected_h:
        raise RawBodyRetentionError(
            "caller H does not match raw_body_sha256(body_bytes); refuse persist"
        )

    relpath = raw_odds_body_relpath(game_id)
    try:
        written = store.write_new_file(
            relpath,
            data,
            actor=actor,
            note=f"raw-odds-body:{game_id or 'slate'}",
            extra={"raw_body_sha256": hashed, "kind": "raw_odds_body"},
        )
    except RawBodyRetentionError:
        raise
    except Exception as exc:  # noqa: BLE001 — fail closed; never leak secrets
        raise RawBodyRetentionError(f"raw body write failed: {type(exc).__name__}") from exc

    assert_written_body_matches(store.root / relpath, hashed)
    if str(written.get("artifact_sha") or "") != hashed:
        raise RawBodyRetentionError("write_new_file artifact_sha != H")
    assert_sha256sums_lists(store, relpath, hashed)

    headers = {
        str(key).strip().lower(): str(value) for key, value in dict(response_headers or {}).items()
    }
    params = redact_secrets(dict(request_params or {}))
    length_hdr = str(headers.get("content-length") or "").strip()
    try:
        content_length = int(length_hdr) if length_hdr else len(data)
    except ValueError:
        content_length = len(data)

    meta = redact_secrets(
        {
            "raw_body_sha256": hashed,
            "content_encoding": headers.get("content-encoding") or "",
            "content_length": content_length,
            "provider_server_ts": provider_server_ts,
            "client_received_at": client_received_at,
            "endpoint": endpoint,
            "bookmakers": params.get("bookmakers"),
            "markets": params.get("markets"),
            "regions": params.get("regions"),
            "tip_sha": str(tip_sha or ""),
            "capture_receipt_id": str(capture_receipt_id or ""),
            "relpath": relpath,
            "game_id": game_id or "slate",
        }
    )
    meta_relpath = raw_odds_meta_relpath(game_id)
    try:
        meta_written = store.write_new_file(
            meta_relpath,
            meta,
            actor=actor,
            note=f"raw-odds-body-meta:{game_id or 'slate'}",
            extra={"raw_body_sha256": hashed, "kind": "raw_odds_body_meta"},
        )
    except RawBodyRetentionError:
        raise
    except Exception as exc:  # noqa: BLE001 — fail closed; never leak secrets
        raise RawBodyRetentionError(f"raw body meta write failed: {type(exc).__name__}") from exc

    # Body must still be listed after the sidecar refresh.
    assert_sha256sums_lists(store, relpath, hashed)
    meta_sha = str(meta_written.get("artifact_sha") or "")
    if meta_sha:
        assert_sha256sums_lists(store, meta_relpath, meta_sha)

    return {
        "relpath": relpath,
        "meta_relpath": meta_relpath,
        "raw_body_sha256": hashed,
        "artifact_sha": written["artifact_sha"],
        "meta_artifact_sha": meta_sha,
        "bytes": len(data),
    }
