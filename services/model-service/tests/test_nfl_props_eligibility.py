from src.services.nfl_props_eligibility import (
    filter_investable_rows,
    is_investable_prop,
)


def test_ol_anytime_td_is_not_investable() -> None:
    assert not is_investable_prop(
        market_key="anytime_td",
        position="G",
        model_mean=0.0,
        confidence=0.05,
    )
    assert not is_investable_prop(
        market_key="anytime_td",
        position="OL",
        model_mean=0.02,
        line=0.5,
    )


def test_kicker_anytime_td_excluded() -> None:
    assert not is_investable_prop(
        market_key="anytime_td",
        position="K",
        model_mean=0.15,
    )


def test_dl_rec_yds_excluded() -> None:
    assert not is_investable_prop(
        market_key="rec_yds",
        position="DE",
        model_mean=40.0,
        line=35.5,
        market_joined=True,
    )


def test_skill_rows_pass_floors() -> None:
    assert is_investable_prop(
        market_key="pass_yds",
        position="QB",
        model_mean=245.0,
        line=242.5,
        confidence=0.7,
    )
    assert is_investable_prop(
        market_key="rush_yds",
        position="RB",
        model_mean=68.0,
        line=64.5,
    )
    assert is_investable_prop(
        market_key="rec_yds",
        position="WR",
        model_mean=72.0,
        line=68.5,
        market_joined=True,
    )
    assert is_investable_prop(
        market_key="anytime_td",
        position="TE",
        model_mean=0.22,
    )


def test_zero_model_skill_row_dropped() -> None:
    assert not is_investable_prop(
        market_key="rec_yds",
        position="WR",
        model_mean=0.0,
        confidence=0.08,
    )


def test_qb_rush_needs_scramble_volume() -> None:
    assert not is_investable_prop(
        market_key="rush_yds",
        position="QB",
        model_mean=4.0,
    )
    assert is_investable_prop(
        market_key="rush_yds",
        position="QB",
        model_mean=22.0,
    )


def test_filter_drops_junk_keeps_desk_rows() -> None:
    kept, dropped = filter_investable_rows(
        [
            {
                "market_key": "anytime_td",
                "model_mean": 0.0,
                "line": 0.5,
                "confidence": 0.04,
                "diagnostics": {"position": "C"},
            },
            {
                "market_key": "rec_yds",
                "model_mean": 81.0,
                "line": 74.5,
                "market_over_price": -110,
                "diagnostics": {"position": "WR", "role_confidence": 0.88},
            },
        ]
    )
    assert dropped == 1
    assert len(kept) == 1
    assert kept[0]["diagnostics"]["position"] == "WR"
