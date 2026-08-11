"""Railway --path-as-root must not IndexError on lineage pointer load."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.routes import nfl as nfl_routes
from src.routes.nfl import (
    _load_nfl_web_active_run,
    _nfl_web_launch_bundle_candidates,
)


def test_candidates_skip_missing_parents_on_shallow_path() -> None:
    # Mimic /app/src/routes/nfl.py under Railway path-as-root (absolute).
    fake = Path("/app/src/routes/nfl.py")
    assert len(fake.parents) == 4  # indices 0..3 only; parents[4] would IndexError
    candidates = _nfl_web_launch_bundle_candidates(fake)
    assert candidates
    assert all(p.name == "nfl-web-launch-bundle.json" for p in candidates)
    # Must not include a parents[4]-derived path when it does not exist.
    assert not any(str(p).startswith("//") for p in candidates)


def test_candidates_include_repo_root_when_deep_enough() -> None:
    deep = Path("/Users/example/kosedge/services/model-service/src/routes/nfl.py")
    candidates = _nfl_web_launch_bundle_candidates(deep)
    assert any(
        str(p).endswith("kosedge/data/ops/nfl-web-launch-bundle.json") for p in candidates
    )


def test_load_returns_empty_when_no_candidates_exist(monkeypatch) -> None:
    monkeypatch.setattr(
        nfl_routes,
        "_nfl_web_launch_bundle_candidates",
        lambda here=None: (Path("/nonexistent/data/ops/nfl-web-launch-bundle.json"),),
    )
    assert _load_nfl_web_active_run() == {}


def test_load_reads_bundle_from_candidate(tmp_path: Path, monkeypatch) -> None:
    bundle = tmp_path / "nfl-web-launch-bundle.json"
    payload = {
        "active_run_id": "test-run-1",
        "bundle_id": "test-run-1",
        "kind": "Model",
        "engine_version": "nfl-test-v0",
        "generated_at_utc": "2026-08-11T00:00:00Z",
    }
    bundle.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        nfl_routes,
        "_nfl_web_launch_bundle_candidates",
        lambda here=None: (bundle,),
    )
    loaded = _load_nfl_web_active_run()
    assert loaded.get("active_run_id") == "test-run-1"
    assert loaded.get("engine_version") == "nfl-test-v0"
