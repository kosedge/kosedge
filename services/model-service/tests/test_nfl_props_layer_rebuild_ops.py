"""Ops contracts for features/box/props layer rebuild (baseline upsert=0 fix)."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

# App import pulls src.db which requires DATABASE_URL at module load.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from fastapi.testclient import TestClient

from src.main import app
import src.routes.nfl as nfl_routes


def test_props_celery_task_names_include_features_box_rebuild() -> None:
    tasks_path = Path(__file__).resolve().parents[1] / "src" / "tasks.py"
    text = tasks_path.read_text(encoding="utf-8")
    assert '@celery_app.task(name="src.tasks.materialize_nfl_player_projection_features")' in text
    assert '@celery_app.task(name="src.tasks.run_nfl_props_layer_rebuild")' in text
    assert '@celery_app.task(name="src.tasks.materialize_nfl_player_box_score_sims")' in text
    assert "props-under-bias-20260731c-baselines-box-rebuild" in text


def test_ingest_module_lazy_loads_nflreadpy() -> None:
    ingest_path = Path(__file__).resolve().parents[1] / "data_platform_nfl" / "ingest.py"
    text = ingest_path.read_text(encoding="utf-8")
    assert "import nflreadpy as nfl" not in text.split("def _nflreadpy")[0]
    assert "def _nflreadpy()" in text
    assert "nfl = _nflreadpy()" in text

def test_vendor_sync_script_preserves_existing_package() -> None:
    script = Path(__file__).resolve().parents[3] / "scripts" / "nfl" / "sync-model-service-vendor.sh"
    text = script.read_text(encoding="utf-8")
    assert "rm -rf \"$DST\"" not in text
    assert "rm -rf $DST" not in text
    assert "Preserved existing" in text


def test_ops_rebuild_and_coverage_endpoints(monkeypatch) -> None:
    sent: list[tuple[str, dict]] = []

    class _AsyncResult:
        id = "task-rebuild-1"

    def _send(name, kwargs=None, **_kw):
        sent.append((name, kwargs or {}))
        return _AsyncResult()

    class _Session:
        def execute(self, statement, params=None):
            sql = str(statement)
            if "COUNT(*)" in sql and "by_week" not in sql.lower() and "UNION" not in sql:
                return SimpleNamespace(scalar_one=lambda: 0)

            class _Result:
                def mappings(self):
                    return self

                def all(self):
                    return [
                        {
                            "week": 17,
                            "usage_rows": 400,
                            "feature_rows": 0,
                            "baseline_rows": 324,
                            "box_rows": 0,
                            "prop_edge_rows": 1620,
                        }
                    ]

            if "UNION" in sql:
                return _Result()
            return SimpleNamespace(scalar_one=lambda: 0)

        def close(self) -> None:
            return None

    monkeypatch.setattr(nfl_routes, "celery_app", SimpleNamespace(send_task=_send))
    monkeypatch.setattr(nfl_routes, "SessionLocal", lambda: _Session())
    client = TestClient(app)

    coverage = client.get("/nfl/ops/player-layer-coverage", params={"season": 2025, "week": 17})
    assert coverage.status_code == 200
    body = coverage.json()
    assert body["totals"]["feature_rows"] == 0
    assert body["by_week"][0]["usage_rows"] == 400
    assert body["diagnosis"] == "features_empty_baselines_will_upsert_zero"

    rebuild = client.post(
        "/nfl/ops/rebuild-props-layers",
        params={"season": 2025, "weeks": "14,16,17", "replace_features": True},
    )
    assert rebuild.status_code == 200
    assert rebuild.json()["task_name"] == "src.tasks.run_nfl_props_layer_rebuild"
    assert rebuild.json()["weeks"] == [14, 16, 17]
    assert sent[-1][0] == "src.tasks.run_nfl_props_layer_rebuild"
    assert sent[-1][1]["weeks"] == [14, 16, 17]
    assert sent[-1][1]["week"] is None

    season_only = client.post("/nfl/ops/rebuild-props-layers", params={"season": 2025})
    assert season_only.status_code == 200
    assert season_only.json()["weeks"] == list(range(1, 19))

    bare_baselines = client.post(
        "/nfl/ops/materialize-player-baselines",
        params={"season": 2025},
    )
    assert bare_baselines.status_code == 400

    features = client.post(
        "/nfl/ops/materialize-player-features",
        params={"season": 2025, "week": 17},
    )
    assert features.status_code == 200
    assert features.json()["task_name"] == "src.tasks.materialize_nfl_player_projection_features"

    box = client.post(
        "/nfl/ops/materialize-player-box-sims",
        params={"season": 2025, "week": 17},
    )
    assert box.status_code == 200
    assert box.json()["task_name"] == "src.tasks.materialize_nfl_player_box_score_sims"
