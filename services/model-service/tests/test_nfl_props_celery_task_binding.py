"""Guard: Celery must decorate materialize_nfl_player_props_edges, not helpers."""

from pathlib import Path


def test_props_edges_celery_decorator_sits_on_materializer() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "tasks.py"
    text = src.read_text(encoding="utf-8")
    needle = '@celery_app.task(name="src.tasks.materialize_nfl_player_props_edges")'
    idx = text.find(needle)
    assert idx >= 0, "missing celery task registration for props edges"
    window = text[idx : idx + 240]
    assert "def materialize_nfl_player_props_edges(" in window
    assert "def _box_dist_moments(" not in window
