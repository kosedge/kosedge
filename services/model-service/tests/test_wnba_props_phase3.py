from src.services.wnba_player_prop_projection import project_player_markets
from src.services.wnba_prop_edge_policy import evaluate_wnba_prop_edge


def test_project_player_markets_40_min_cap() -> None:
    rows = project_player_markets(
        player_id="p1",
        player_name="A'ja Wilson",
        team_key="LAS",
        minutes=36.0,
        usage_proxy=22.0,
        pts_per_min=0.7,
        reb_per_min=0.3,
        ast_per_min=0.1,
        threes_per_min=0.04,
        sample_games=8,
        team_pace=82.0,
        team_ortg=108.0,
    )
    assert len(rows) == 4
    assert all(r.minutes <= 40.0 for r in rows)
    pts = next(r for r in rows if r.market_key == "pts")
    assert pts.model_mean > 20.0


def test_role_collapse_under_refusal() -> None:
    edge = evaluate_wnba_prop_edge(
        market_key="pts",
        model_mean=6.0,
        model_std=3.0,
        line=18.5,
        over_price=-110,
        under_price=-110,
        sample_games=8,
    )
    assert edge["tag"] == "PASS"
    assert edge["reason"] == "model_role_collapse"
    assert edge["stake_eligible"] is False


def test_thin_sample_pass() -> None:
    edge = evaluate_wnba_prop_edge(
        market_key="reb",
        model_mean=8.0,
        model_std=2.0,
        line=7.5,
        over_price=-110,
        under_price=-110,
        sample_games=1,
    )
    assert edge["tag"] == "PASS"
    assert edge["reason"] == "thin_sample"
