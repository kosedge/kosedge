"""803ceb4e local input path (prep bytes).

Feature builder reads only ``features/`` + ``schedule/``. Grading inputs
(finals, closes) must live in a physically separate tree and are refused if
present under the feature root (LC-6 / 803ceb4e L-3).

No database, no network, no Odds API, no nflverse fetch.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


FORBIDDEN_FEATURE_TREE_NAMES = frozenset(
    {
        "grading",
        "outcomes",
        "finals",
        "closes",
        "labels",
        "results",
        "outcomes.jsonl",
        "finals.jsonl",
        "closes.jsonl",
        "grading.jsonl",
    }
)

REQUIRED_DIRS = ("features", "schedule")


class LocalPathError(ValueError):
    """Local input path contract violation."""


@dataclass(frozen=True)
class LocalInputPath:
    root: Path
    manifest: dict[str, Any]
    feature_rows: tuple[dict[str, Any], ...]
    schedule_rows: tuple[dict[str, Any], ...]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        raise LocalPathError(f"missing jsonl: {path.name}")
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LocalPathError(f"{path.name}:{line_no} is not JSON") from exc
        if not isinstance(obj, dict):
            raise LocalPathError(f"{path.name}:{line_no} is not an object")
        rows.append(obj)
    return rows


def assert_feature_tree_has_no_grading(root: Path) -> None:
    for child in root.rglob("*"):
        name = child.name.lower()
        rel = child.relative_to(root).as_posix().lower()
        if name in FORBIDDEN_FEATURE_TREE_NAMES or any(
            part in FORBIDDEN_FEATURE_TREE_NAMES for part in rel.split("/")
        ):
            raise LocalPathError(
                f"LC-6: grading/label artifact {rel} is readable from the feature tree"
            )


def load_local_input_path(root: Path | str) -> LocalInputPath:
    base = Path(root).resolve()
    if not base.is_dir():
        raise LocalPathError(f"local input root does not exist: {base}")
    assert_feature_tree_has_no_grading(base)
    for required in REQUIRED_DIRS:
        if not (base / required).is_dir():
            raise LocalPathError(f"missing required directory: {required}")
    manifest_path = base / "manifest.json"
    if not manifest_path.is_file():
        raise LocalPathError("missing manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise LocalPathError("manifest.json must be an object")
    if manifest.get("network") or manifest.get("database_url"):
        raise LocalPathError("manifest must not carry network or database_url")
    features = _read_jsonl(base / "features" / "rows.jsonl")
    schedule = _read_jsonl(base / "schedule" / "games.jsonl")
    return LocalInputPath(
        root=base,
        manifest=manifest,
        feature_rows=tuple(features),
        schedule_rows=tuple(schedule),
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_sha256sums(root: Path, paths: Iterable[Path]) -> Path:
    """Write SHA256SUMS last (803ceb4e R-6)."""
    lines: list[str] = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        digest = sha256_bytes(path.read_bytes())
        lines.append(f"{digest}  {rel}")
    out = root / "SHA256SUMS"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_local_input_path(
    root: Path | str,
    *,
    manifest: Mapping[str, Any],
    feature_rows: Sequence[Mapping[str, Any]],
    schedule_rows: Sequence[Mapping[str, Any]],
) -> LocalInputPath:
    """Write a sealed local tree. SHA256SUMS is written last."""
    base = Path(root)
    if "network" in manifest or "database_url" in manifest:
        raise LocalPathError("manifest must not carry network or database_url")
    (base / "features").mkdir(parents=True, exist_ok=True)
    (base / "schedule").mkdir(parents=True, exist_ok=True)
    manifest_path = base / "manifest.json"
    features_path = base / "features" / "rows.jsonl"
    schedule_path = base / "schedule" / "games.jsonl"
    manifest_path.write_text(json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    features_path.write_text(
        "".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in feature_rows),
        encoding="utf-8",
    )
    schedule_path.write_text(
        "".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in schedule_rows),
        encoding="utf-8",
    )
    write_sha256sums(base, (manifest_path, features_path, schedule_path))
    return load_local_input_path(base)
