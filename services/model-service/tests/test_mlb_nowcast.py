import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.tasks import _lineup_nowcast_confidence


def test_lineup_nowcast_confidence_increases_when_closer_to_first_pitch() -> None:
    early = _lineup_nowcast_confidence(
        hours_to_first_pitch=18.0,
        lineup_confirmed=False,
        probable_pitcher_home=None,
        probable_pitcher_away=None,
        freshness_score=1.0,
    )
    near = _lineup_nowcast_confidence(
        hours_to_first_pitch=2.0,
        lineup_confirmed=False,
        probable_pitcher_home=None,
        probable_pitcher_away=None,
        freshness_score=1.0,
    )
    assert near["home"] > early["home"]
    assert near["away"] > early["away"]


def test_lineup_nowcast_confidence_boosted_by_confirmed_lineups_and_pitchers() -> None:
    unconfirmed = _lineup_nowcast_confidence(
        hours_to_first_pitch=2.0,
        lineup_confirmed=False,
        probable_pitcher_home=None,
        probable_pitcher_away=None,
        freshness_score=1.0,
    )
    confirmed = _lineup_nowcast_confidence(
        hours_to_first_pitch=2.0,
        lineup_confirmed=True,
        probable_pitcher_home="Pitcher A",
        probable_pitcher_away="Pitcher B",
        freshness_score=1.0,
    )
    assert confirmed["home"] > unconfirmed["home"]
    assert confirmed["away"] > unconfirmed["away"]
