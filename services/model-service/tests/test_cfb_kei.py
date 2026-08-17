from src.services.cfb_season_engine.cfb_kei import (
    KEI_VERSION,
    apply_bias_guard,
    apply_cfb_kei,
    diagnostic_short_fav_sample,
    tag_from_edge,
)


def test_model_not_mutated() -> None:
    proj = {
        "week": 0,
        "spread_home": -3.5,
        "expected_total": 52.0,
        "home_win_prob": 0.61,
        "margin_sd": 16.0,
        "drivers": {"primary_signals": {}, "matchup": {"hfa": 1.7, "neutral_site": False}},
    }
    out = apply_cfb_kei(proj)
    assert out["model_spread_home"] == -3.5
    assert out["model_used_in_spread"] is False
    assert out["used_in_spread"] is True
    assert out["kei_spread_home"] != out["model_spread_home"]
    assert out["kei_version"] == KEI_VERSION
    assert proj["spread_home"] == -3.5


def test_bias_guard_preserves_favorite_sign() -> None:
    kei, entries = apply_bias_guard(-3.5, week=1)
    assert kei < 0
    assert any(e.get("applied") for e in entries)


def test_early_play_threshold_pass_default() -> None:
    assert tag_from_edge(3.9, week=0, fbs_vs_fbs=True) == "LEAN"
    assert tag_from_edge(4.0, week=0, fbs_vs_fbs=True) == "PLAY"
    assert tag_from_edge(1.0, week=0, fbs_vs_fbs=True) == "PASS"
    assert tag_from_edge(9.0, week=0, fbs_vs_fbs=False) == "PASS"


def test_market_disagreement_does_not_move_kei() -> None:
    proj = {"week": 0, "spread_home": -3.0, "expected_total": 50.0, "home_win_prob": 0.58, "margin_sd": 16.0}
    out = apply_cfb_kei(proj, market_spread_home=-12.0)
    assert out["investigate"] is True
    assert out["kei_spread_home"] != -12.0
    assert any("INVESTIGATE" in (d.get("reason") or "") for d in out["drivers"])


def test_short_fav_diagnostic_improves() -> None:
    diag = diagnostic_short_fav_sample()
    assert diag["improved"] is True
    assert diag["signs_preserved"] is True
    assert diag["kei_play_vs_3pt_book"] < diag["raw_play_vs_3pt_book"]
