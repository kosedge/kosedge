from src.services.mlb_odds_firewall import (
    densify_bookmakers_csv,
    filter_spread_rows_for_firewall,
    is_canonical_mlb_run_line,
    is_standard_run_line,
    select_preferred_book_row,
)


def test_dk_first_preferred_book() -> None:
    rows = [
        {"book_code": "fanduel", "spread_home": -1.5},
        {"book_code": "draftkings", "spread_home": -1.5},
        {"book_code": "betmgm", "spread_home": -1.5},
    ]
    chosen = select_preferred_book_row(rows, preferred_book="draftkings")
    assert chosen is not None
    assert chosen["book_code"] == "draftkings"


def test_densify_books_put_dk_first() -> None:
    assert densify_bookmakers_csv("fanduel,draftkings").startswith("draftkings")


def test_alternate_run_lines_filtered_when_standard_present() -> None:
    rows = [
        {"book_code": "draftkings", "spread_home": -1.5},
        {"book_code": "fanduel", "spread_home": -2.5},
        {"book_code": "betmgm", "spread_home": -3.5},
    ]
    kept = filter_spread_rows_for_firewall(rows)
    assert len(kept) == 1
    assert kept[0]["spread_home"] == -1.5


def test_canonical_helpers() -> None:
    assert is_standard_run_line(-1.5)
    assert is_canonical_mlb_run_line(-2.5)
    assert not is_canonical_mlb_run_line(-4.5)
