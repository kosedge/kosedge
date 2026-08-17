from src.services.cfb_season_engine.cfb_futures import (
    CFP_FIELD,
    select_cfp_field,
    simulate_playoff,
)
import random


def test_cfp_field_is_twelve_with_auto_bids() -> None:
    teams = [f"T{i:02d}" for i in range(20)]
    wins = {t: float(20 - i) for i, t in enumerate(teams)}
    conf_wins = {t: float(10 - (i % 8)) for i, t in enumerate(teams)}
    conferences = {t: ["SEC", "Big Ten", "ACC", "Big 12", "AAC"][i % 5] for i, t in enumerate(teams)}
    power = {t: 1.5 - i * 0.02 for i, t in enumerate(teams)}
    field = select_cfp_field(
        teams=teams,
        wins=wins,
        conf_wins=conf_wins,
        conferences=conferences,
        power=power,
    )
    assert len(field) == CFP_FIELD
    assert len(set(field)) == CFP_FIELD


def test_playoff_returns_a_seed() -> None:
    seeds = [f"S{i}" for i in range(12)]
    power = {s: 1.4 - i * 0.03 for i, s in enumerate(seeds)}
    champ = simulate_playoff(seeds, rng=random.Random(1), power=power)
    assert champ in seeds
