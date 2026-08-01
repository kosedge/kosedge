from src.services.wnba_publish_policy import board_publish_posture, publish_tag


def test_default_research_only() -> None:
    tag = publish_tag("spread", model_line=-3.5, market_line=-2.0)
    assert tag["tag"] == "PASS"
    assert "research_only" in tag["reason"]


def test_board_posture() -> None:
    p = board_publish_posture(n_with_close_lines=0, ats=None)
    assert p["mainlines"] == "research_only"
    assert p["props"] == "research_only"
