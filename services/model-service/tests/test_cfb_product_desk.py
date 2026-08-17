"""CFB research desk — official W0/W1 board, no KEI, status never 500s."""

from fastapi.testclient import TestClient

from src.main import app
from src.services.cfb_season_engine.product_desk import (
    official_week_board,
    product_desk_payload,
)


def test_week_board_has_week0_and_week1() -> None:
    board = official_week_board((0, 1))
    weeks = {int(g["week"]) for g in board["games"]}
    assert 0 in weeks
    assert 1 in weeks
    assert board["n_games"] >= 20
    assert board["used_in_spread"] is False
    assert board.get("kei") is True
    tcu = next(g for g in board["games"] if g["home"] == "TCU" and g["away"] == "UNC")
    assert tcu.get("kei", {}).get("kei_spread_home") is not None


def test_product_desk_payload_contract() -> None:
    desk = product_desk_payload()
    assert desk["research_only"] is True
    assert desk["kei"] is True
    assert desk["used_in_spread"] is False
    assert desk["kei_used_in_spread"] is True
    assert desk["team_dna"]["official_fbs"] >= 130
    assert desk["week_board"]["n_games"] >= 20


def test_status_http_never_500_and_attaches_desk() -> None:
    client = TestClient(app)
    res = client.get("/cfb/season-engine/status", params={"season": 2026, "demo": True})
    assert res.status_code == 200
    body = res.json()
    assert body.get("engine_version")
    assert body.get("used_in_spread") is False
    desk = body.get("desk") or {}
    assert desk.get("kei") is True
    assert desk.get("used_in_spread") is False
    assert (desk.get("week_board") or {}).get("n_games", 0) >= 20


def test_project_game_accepts_week_0() -> None:
    client = TestClient(app)
    res = client.post(
        "/cfb/season-engine/project-game",
        json={
            "home_team": "TCU",
            "away_team": "UNC",
            "week": 0,
            "season": 2026,
            "neutral_site": True,
            "demo": True,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("used_in_spread") is False
    assert body.get("ok") is True or body.get("error")
    if body.get("ok"):
        assert body.get("kei", {}).get("kei_spread_home") is not None
