from src.services.nba_publish_policy import board_publish_posture, publish_tag


def test_publish_tag_defaults_research_only() -> None:
    out = publish_tag(
        "spread",
        model_line=-6.5,
        market_line=-3.0,
        force_research_only=True,
    )
    assert out["tag"] == "PASS"
    assert "research_only" in out["reason"]


def test_board_publish_posture_stays_research_until_evidence() -> None:
    posture = board_publish_posture(n_with_close_lines=0, ats=None)
    assert posture["mainlines"] == "research_only"
    assert posture["props"] == "research_only"
    cleared = board_publish_posture(n_with_close_lines=80, ats=0.55)
    assert cleared["mainlines"] == "calibrating"
