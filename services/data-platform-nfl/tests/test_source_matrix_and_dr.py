from data_platform_nfl.dr_backup import parse_database_url
from data_platform_nfl.source_matrix import SOURCE_FALLBACK_MATRIX, source_matrix_payload


def test_source_matrix_has_core_domains() -> None:
    domains = {row["domain"] for row in SOURCE_FALLBACK_MATRIX}
    assert "play_by_play" in domains
    assert "injuries" in domains
    assert "vegas_player_props" in domains
    assert "snap_counts" in domains
    payload = source_matrix_payload()
    assert payload["version"].startswith("nfl-source-matrix")
    assert payload["licensed_feed_evaluation"]["status"] == "planned_not_integrated"


def test_parse_database_url_sqlalchemy_prefix() -> None:
    info = parse_database_url("postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")
    assert info["user"] == "ryankos"
    assert info["password"] == "postgres"
    assert info["host"] == "127.0.0.1"
    assert info["port"] == "5432"
    assert info["dbname"] == "kosedge"
