from src.services.mlb_market_consensus import weighted_consensus


def test_weighted_consensus_handles_book_weights() -> None:
    value = weighted_consensus(
        [
            ("pinnacle", -130.0),
            ("draftkings", -120.0),
            ("fanduel", -121.0),
            ("random_book", -118.0),
        ]
    )
    assert value is not None
    assert value < -120.0


def test_weighted_consensus_trims_extreme_outlier() -> None:
    value = weighted_consensus(
        [
            ("pinnacle", 8.0),
            ("draftkings", 8.5),
            ("fanduel", 8.0),
            ("caesars", 8.5),
            ("softbook", 15.0),  # outlier should be trimmed by default
            ("softbook2", 2.0),  # outlier should be trimmed by default
        ]
    )
    assert value is not None
    assert 7.8 <= value <= 8.7
