"""Independently supplied verification context for DIRECT evidence gates.

Hashes, revision, command, exit, and output/log bytes are computed from
actual runtime / files — not copied from the manifest. CERT=0.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.services.nfl_hhl1_capture.identity import canonical_json, sha256_hex
from src.services.nfl_ops_v1_evidence.constants import (
    BASE_DEPLOY_VERCEL,
    CERT,
    CODE_FILES,
    DATA_LABEL,
    EXPECTED_COMMAND,
    EXPECTED_COMMAND_JOINT,
    GIT_COMMIT_SHA_LEN,
    JOINT_CODE_FILES,
    LINEAGE_706_TIP,
    LINEAGE_707_TIP,
    PACKAGE,
    PINNED_CHAIN_DIGEST,
    PROFILE,
    PROFILE_JOINT,
    UTILITY_700_TIP,
    UTILITY_701_TIP,
)
from src.services.nfl_ops_v1_evidence.hashes import hash_file_list
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.schema import history_none_binding


def is_git_commit_sha(value: Any) -> bool:
    if type(value) is not str or len(value) != GIT_COMMIT_SHA_LEN:
        return False
    return all(ch in "0123456789abcdef" for ch in value)


def git_tip(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "UNKNOWN"
    return (proc.stdout or "").strip()


def config_binding(
    *,
    profile: str = PROFILE,
    expected_command: str = EXPECTED_COMMAND,
) -> dict[str, Any]:
    return {
        "profile": profile,
        "package": PACKAGE,
        "pinned_chain_digest": PINNED_CHAIN_DIGEST,
        "lineage_707": LINEAGE_707_TIP,
        "lineage_706": LINEAGE_706_TIP,
        "utility_700": UTILITY_700_TIP,
        "utility_701": UTILITY_701_TIP,
        "cert": CERT,
        "data_label": DATA_LABEL,
        "expected_command": expected_command,
    }


def code_paths(root: Path, rels: Sequence[str] | None = None) -> list[Path]:
    files = rels or CODE_FILES
    return [root / rel for rel in files if (root / rel).is_file()]


def profile_verify_kwargs(manifest: Mapping[str, Any]) -> dict[str, Any]:
    profile = manifest.get("profile") or PROFILE
    if profile == PROFILE_JOINT:
        return {
            "profile": PROFILE_JOINT,
            "expected_command": EXPECTED_COMMAND_JOINT,
            "code_file_rels": JOINT_CODE_FILES,
        }
    return {
        "profile": PROFILE,
        "expected_command": EXPECTED_COMMAND,
        "code_file_rels": CODE_FILES,
    }


def hash_input_payload(payload: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json(dict(payload)).encode("utf-8"))


def hash_history_binding() -> str:
    return sha256_hex(canonical_json(history_none_binding()).encode("utf-8"))


def hash_config_binding(
    *,
    profile: str = PROFILE,
    expected_command: str = EXPECTED_COMMAND,
) -> str:
    return sha256_hex(
        canonical_json(
            config_binding(profile=profile, expected_command=expected_command)
        ).encode("utf-8")
    )


def hash_code_files(root: Path, rels: Sequence[str] | None = None) -> dict[str, Any]:
    return hash_file_list(root, code_paths(root, rels))


@dataclass(frozen=True)
class VerificationContext:
    """Actual runtime/file facts. Never populated from the manifest."""

    git_head: str
    git_base: str
    source_revision: str
    actual_input_hash: str
    actual_history_hash: str
    actual_config_hash: str
    actual_code_hash: str
    actual_command: str
    actual_cwd: str
    actual_exit: Optional[int] = None
    output_bytes: Optional[Mapping[str, bytes]] = None
    log_bytes: Optional[bytes] = None


def build_verification_context(
    *,
    root: Path,
    payload: Mapping[str, Any],
    command: str,
    cwd: str,
    exit_code: Optional[int] = None,
    output_paths: Optional[Sequence[Path | str]] = None,
    log_text: Optional[str] = None,
    profile: str = PROFILE,
    expected_command: str = EXPECTED_COMMAND,
    code_file_rels: Sequence[str] | None = None,
) -> VerificationContext:
    """Compute bind targets from live git + on-disk files + supplied payload/bytes."""
    repo = Path(root)
    head = git_tip(repo)
    if not is_git_commit_sha(head):
        raise EvidenceGateRefuse(
            f"actual git HEAD {head!r} is not a 40-hex commit",
            refuse_class=RefuseClass.TYPE,
        )
    output_map: Optional[dict[str, bytes]] = None
    if output_paths is not None:
        output_map = {}
        for raw in output_paths:
            path = Path(raw)
            if not path.is_file():
                raise EvidenceGateRefuse(
                    f"actual output file missing: {path}",
                    refuse_class=RefuseClass.MISSING_CONTEXT,
                )
            output_map[path.as_posix()] = path.read_bytes()
    log_bytes = None if log_text is None else log_text.encode("utf-8")
    return VerificationContext(
        git_head=head,
        git_base=BASE_DEPLOY_VERCEL,
        source_revision=head,
        actual_input_hash=hash_input_payload(payload),
        actual_history_hash=hash_history_binding(),
        actual_config_hash=hash_config_binding(
            profile=profile, expected_command=expected_command
        ),
        actual_code_hash=hash_code_files(repo, code_file_rels)["sha256"],
        actual_command=command,
        actual_cwd=str(cwd),
        actual_exit=exit_code,
        output_bytes=output_map,
        log_bytes=log_bytes,
    )
