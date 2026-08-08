"""True PR product surface — display serializer smell tests (no math changes)."""

from __future__ import annotations

from src.services.nfl_season_engine.loaders import build_packaged_real_universe
from src.services.nfl_season_engine.true_pr_product import (
    serialize_true_pr_product_surface,
)


def test_true_pr_product_surface_packaged_board() -> None:
    universe = build_packaged_real_universe(season=2026)
    payload = serialize_true_pr_product_surface(
        universe,
        season=2026,
        as_of_week=1,
        mode="real",
        engine_version="test",
        enrich_display_drivers=True,
    )
    assert payload["team_count"] == 32
    assert len(payload["teams"]) == 32
    assert payload["contract"]["projected_sos"].startswith("outlook only")

    # Ranked by intrinsic PR descending.
    prs = [float(r["intrinsic_pr"]) for r in payload["teams"]]
    assert prs == sorted(prs, reverse=True)

    sample = payload["teams"][0]
    drivers = sample["drivers"]
    assert "continuity" in drivers
    assert "qb_premium" in drivers
    assert "past_sos" in drivers
    assert "projected_sos_2026" in drivers
    assert "blend" in drivers

    # Preseason: blend is prior-heavy, never current-sample cosplay.
    blend = drivers["blend"]
    assert blend["available"] is True
    assert blend["preseason"] is True
    assert blend["state"] == "prior_heavy"
    assert blend["w_current"] == 0.0

    # Future SOS framing is explicit.
    proj = drivers["projected_sos_2026"]
    assert proj["intrinsic_pr_unchanged"] is True
    assert "does not change intrinsic PR" in (proj.get("framing") or "")


def test_low_continuity_staff_carousel_not_elite() -> None:
    universe = build_packaged_real_universe(season=2026)
    payload = serialize_true_pr_product_surface(
        universe, season=2026, enrich_display_drivers=True
    )
    by_team = {r["team"]: r for r in payload["teams"]}
    for team in ("ARI", "LV", "NYG", "CLE"):
        cont = by_team[team]["drivers"]["continuity"]
        assert cont["available"] is True
        assert cont["band"] == "low"
        assert cont.get("approximate") is True
        # Never decorate missing evidence as elite continuity.
        assert cont["band"] != "high"


def test_projected_sos_differs_without_moving_intrinsic_identity() -> None:
    universe = build_packaged_real_universe(season=2026)
    payload = serialize_true_pr_product_surface(
        universe, season=2026, enrich_display_drivers=False
    )
    bands = {
        r["team"]: r["drivers"]["projected_sos_2026"]["band"]
        for r in payload["teams"]
        if r["drivers"]["projected_sos_2026"]["available"]
    }
    assert "easy" in set(bands.values()) or "hard" in set(bands.values())
    # Intrinsic PR present for every team regardless of SOS band.
    for row in payload["teams"]:
        assert isinstance(row["intrinsic_pr"], float)
        assert row["drivers"]["projected_sos_2026"]["intrinsic_pr_unchanged"] is True


def test_qb_missing_fidelity_does_not_claim_elite_lift() -> None:
    universe = build_packaged_real_universe(season=2026)
    payload = serialize_true_pr_product_surface(
        universe, season=2026, enrich_display_drivers=True
    )
    for row in payload["teams"]:
        qb = row["drivers"]["qb_premium"]
        if qb.get("fidelity") == "missing":
            assert qb.get("band") is None
            assert qb.get("band_label") in {"unavailable", "Context only", None} or (
                qb.get("premium") is None
            )
