from __future__ import annotations

from data_platform_nfl.usage_hydration_shared import compute_hydration_games_denominator


def test_full_time_starter_denominator_is_unchanged() -> None:
    # A starter who played (nearly) every real team game -- their own
    # active-week count already ~= their team's season length, so the fix
    # should not materially change their per-game rate.
    assert compute_hydration_games_denominator(games_active=17.0, team_season_games=17.0) == 17.0


def test_backup_qb_spot_starts_get_diluted_by_real_team_season_length() -> None:
    # Real bug: a backup QB with 4 emergency spot starts (out of a 17-game
    # team season) was having his per-game rate computed as
    # SUM(usage) / 4 -- making his "when I play" rate look like a starter's,
    # instead of being diluted by the 13 real team-weeks he did NOT play at
    # all. The correct denominator is the team's season length, not the
    # player's own active-week count.
    denominator = compute_hydration_games_denominator(games_active=4.0, team_season_games=17.0)
    assert denominator == 17.0


def test_never_divides_by_less_than_the_players_own_active_weeks() -> None:
    # Guards the "only ever dilutes down, never inflates up" property: even
    # if team_season_games data were ever missing/degenerate (e.g. 0), this
    # must not divide by less than the player's own real active-week count.
    assert compute_hydration_games_denominator(games_active=12.0, team_season_games=0.0) == 12.0
    assert compute_hydration_games_denominator(games_active=12.0, team_season_games=5.0) == 12.0


def test_backup_qb_rate_is_a_small_fraction_of_naive_starter_style_rate() -> None:
    # End-to-end sanity on the exact production numbers that surfaced this
    # bug: a backup QB with 4 spot starts totaling 93 involvement plays
    # (23.25/game "when active") should end up with a real per-team-week
    # rate closer to a true backup's (~5.5 plays/game), not a starter's.
    games_active = 4.0
    team_season_games = 17.0
    total_involvement_plays = 93.0
    naive_rate = total_involvement_plays / games_active
    fixed_rate = total_involvement_plays / compute_hydration_games_denominator(games_active, team_season_games)
    assert fixed_rate < naive_rate * 0.3
    assert abs(fixed_rate - (93.0 / 17.0)) < 1e-9
