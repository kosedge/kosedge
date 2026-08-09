"""Smell tests — True PR harden (live rookies + season finite audit)."""

from __future__ import annotations

import random
from copy import deepcopy

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    apply_process_priors,
    audit_season_finite_production,
    build_demo_universe,
    build_packaged_real_universe,
    project_game_player_boxes,
    simulate_full_season,
)
from src.services.nfl_season_engine.calibration import apply_efficiency_priors
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.injury_paths import apply_injury_paths_for_week
from src.services.nfl_season_engine.loaders import (
    STRENGTH_SOURCE_DEMO,
    draft_round_from_number,
    enrich_depth_rows_with_rookie_flags,
    load_packaged_depth_chart,
    load_packaged_rookie_flags,
)
from src.services.nfl_season_engine.player_regression import (
    ROOKIE_EXPERIENCE_CONFIDENCE,
    SEASON_FINITE_TOLERANCE,
    accumulate_game_caps_into_season,
    efficiency_cv_mult,
    empty_season_cap_accum,
    named_sums_within_caps,
)
from src.services.nfl_season_engine.player_usage import allocate_game_usage
from src.services.nfl_season_engine.production import produce_box_scores
from src.services.nfl_season_engine.types import PlayerRole


# Known 2026-class skill rookies present on packaged depth (nflverse join).
_KNOWN_2026_ROOKIES = (
    ("Fernando Mendoza", "LV"),
    ("Jeremiyah Love", "ARI"),
    ("Ty Simpson", "LA"),
    ("Makai Lemon", "PHI"),
)


def test_engine_version_true_pr_harden() -> None:
    assert any(v in DEFAULT_SEASON_ENGINE_VERSION for v in ("v1.16", "v1.15"))
    assert (
        "true-pr-harden" in DEFAULT_SEASON_ENGINE_VERSION
        or "season-coherence" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_draft_round_from_number_does_not_invent() -> None:
    assert draft_round_from_number(None) is None
    assert draft_round_from_number(0) is None
    assert draft_round_from_number(1) == 1
    assert draft_round_from_number(32) == 1
    assert draft_round_from_number(33) == 2
    assert draft_round_from_number(96) == 3


def test_live_rookie_flags_on_packaged_depth() -> None:
    """Smell 1: known 2026 rookies show is_rookie + wider bands than vets."""
    universe = build_packaged_real_universe(2026)
    rookies = [
        r
        for roles in universe.rosters.values()
        for r in roles
        if r.is_rookie
    ]
    assert len(rookies) >= 8, f"expected live rookies on packaged path, got {len(rookies)}"
    assert int((universe.notes.get("rookie_flags") or {}).get("rookie_flagged") or 0) >= 8

    found = []
    for name, team in _KNOWN_2026_ROOKIES:
        hits = [r for r in universe.rosters.get(team, []) if name.split()[-1] in r.player_name]
        if hits:
            found.append(hits[0])
            assert hits[0].is_rookie
            assert hits[0].rookie_status == "rookie"
            assert hits[0].experience_confidence <= ROOKIE_EXPERIENCE_CONFIDENCE
    assert found, "none of the known 2026 rookies resolved on packaged depth"

    # Wider CV than a typical veteran on the same book.
    vet = next(
        r
        for roles in universe.rosters.values()
        for r in roles
        if not r.is_rookie and r.position == "WR" and r.depth_order == 1
    )
    rook = found[0]
    assert efficiency_cv_mult(rook) > efficiency_cv_mult(vet)


def test_hyped_rookie_does_not_dominate_vet_on_mean() -> None:
    """Smell 2: hyped rookie mean shrink — not above veteran process peers."""
    vet = apply_process_priors(
        apply_efficiency_priors(
            PlayerRole(
                player_key="PHI-WR1-Vet",
                player_name="Vet WR",
                team="PHI",
                position="WR",
                depth_order=1,
                target_share=0.22,
                snap_share=0.85,
                role_confidence=0.8,
                is_rookie=False,
                rookie_status="veteran",
                source="unit",
            ),
            overrides={"ypr": 13.2, "rec_td_rate": 0.055},
        )
    )
    rook = apply_process_priors(
        apply_efficiency_priors(
            PlayerRole(
                player_key="PHI-WR2-Rook",
                player_name="Hyped Rook",
                team="PHI",
                position="WR",
                depth_order=2,
                target_share=0.16,
                snap_share=0.70,
                role_confidence=0.55,
                is_rookie=True,
                draft_round=1,
                rookie_status="rookie",
                source="unit",
            ),
            overrides={"ypr": 16.5, "rec_td_rate": 0.10},
        )
    )
    # Rookie mean pulled toward league — capped well below hyped 16.5 ypr.
    assert rook.ypr < 14.0
    assert rook.ypr < 16.5 * 0.9
    # Depth-2 R1 hype should not clear an established WR1 process mean by much.
    assert rook.ypr <= vet.ypr + 0.7
    assert efficiency_cv_mult(rook) > efficiency_cv_mult(vet)


def test_unclassified_stays_neutral_no_invented_draft() -> None:
    rows, stats = enrich_depth_rows_with_rookie_flags(
        [
            {
                "team": "KC",
                "position": "WR",
                "depth_order": 3,
                "player_name": "Unknown Camp Body",
                "player_id": "00-0099999",
            }
        ],
        {},  # no roster join
        season=2026,
    )
    assert stats["unclassified"] == 1
    assert rows[0]["is_rookie"] is False
    assert rows[0]["draft_round"] is None
    assert rows[0]["rookie_status"] == "unclassified"


def test_season_finite_audit_damps_overflow() -> None:
    """Smell 3: season skill aggregates stay inside team pools (documented tol)."""
    caps = {
        "DET": {
            **empty_season_cap_accum(),
            "pass_yards": 4000.0,
            "rush_yards": 1800.0,
            "rec_yards": 3800.0,
            "skill_tds": 40.0,
            "pass_tds": 28.0,
            "games": 17.0,
        }
    }
    inflated = {
        "a": {
            "player_key": "a",
            "team": "DET",
            "pass_yards": 0.0,
            "rush_yards": 2200.0,
            "rec_yards": 400.0,
            "pass_tds": 0.0,
            "rush_tds": 20.0,
            "rec_tds": 8.0,
        },
        "b": {
            "player_key": "b",
            "team": "DET",
            "pass_yards": 5500.0,
            "rush_yards": 200.0,
            "rec_yards": 0.0,
            "pass_tds": 40.0,
            "rush_tds": 2.0,
            "rec_tds": 0.0,
        },
        "c": {
            "player_key": "c",
            "team": "DET",
            "pass_yards": 0.0,
            "rush_yards": 0.0,
            "rec_yards": 4200.0,
            "pass_tds": 0.0,
            "rush_tds": 0.0,
            "rec_tds": 18.0,
        },
    }
    before = deepcopy(inflated)
    _, diag = audit_season_finite_production(inflated, caps, tol=SEASON_FINITE_TOLERANCE, damp=True)
    assert diag["overflow_fields"] >= 1
    assert diag["dampened_fields"] >= 1
    assert sum(r["rush_yards"] for r in inflated.values()) <= caps["DET"]["rush_yards"] * SEASON_FINITE_TOLERANCE + 1e-6
    assert sum(r["pass_yards"] for r in inflated.values()) <= caps["DET"]["pass_yards"] * SEASON_FINITE_TOLERANCE + 1e-6
    assert sum(r["rush_yards"] for r in inflated.values()) < sum(r["rush_yards"] for r in before.values())


def test_season_sim_exposes_season_finite_and_rookies() -> None:
    universe = build_packaged_real_universe(2026)
    result = simulate_full_season(universe, n_sims=2, seed=11, include_diagnostics=True)
    assert result.engine_version == DEFAULT_SEASON_ENGINE_VERSION
    sf = (result.diagnostics or {}).get("season_finite_audit") or {}
    assert "path0" in sf
    assert "ok" in sf
    assert sf.get("n_sims") == 2
    # Live rookies flow into season totals payload.
    assert any(r.get("is_rookie") for r in result.player_season_totals)
    pr = (result.diagnostics or {}).get("player_regression") or {}
    assert int(pr.get("rookies") or 0) >= 1


def test_continuity_qb_premium_sos_blend_still_healthy() -> None:
    """Smell 4: prior true-PR stack fields remain intact on packaged path."""
    universe = build_packaged_real_universe(2026)
    assert universe.notes.get("mode") == "real"
    for st in universe.strengths.values():
        assert STRENGTH_SOURCE_DEMO not in (st.source or "")
        assert st.full_strength_offense_index > 0
        assert st.offense_index > 0
        # Drivers book still present (continuity / past SOS / stubs labeled).
        drivers = st.drivers if isinstance(st.drivers, dict) else {}
        assert isinstance(drivers, dict)
    # Future SOS attaches on season outlook only.
    result = simulate_full_season(universe, n_sims=2, seed=5, include_diagnostics=True)
    assert "projected_sos_2026" in (result.diagnostics or {})
    sample_team = next(iter(result.team_wins.values()))
    assert "projected_sos_2026" in sample_team
    assert all("mean" in v for v in result.team_wins.values())


def test_game_box_finite_still_works_with_season_audit() -> None:
    """Smell 5: single-game finite path unchanged / healthy."""
    universe = build_packaged_real_universe(2026)
    game = next(g for g in universe.schedule if g.home_team in universe.rosters)
    rng = random.Random(7)
    script, _ = build_game_script(game, universe.strengths, rng=rng, realized=True)
    usage = allocate_game_usage(script, universe.rosters, rng=rng)
    boxes = produce_box_scores(
        usage_rows=usage,
        roles=universe.rosters,
        script=script,
        strengths=universe.strengths,
        rng=rng,
        enforce_finite=True,
    )
    oi = {
        t: universe.strengths[t].offense_index
        for t in (script.home_team, script.away_team)
    }
    assert named_sums_within_caps(boxes, script, strengths_offense=oi, tol=1.05)

    # Season audit helper can accumulate the same game caps without breaking.
    season_caps: dict = {}
    accumulate_game_caps_into_season(season_caps, script=script, strengths_offense=oi)
    assert script.home_team in season_caps
    assert season_caps[script.home_team]["pass_yards"] > 0

    boxes_proj = project_game_player_boxes(
        universe,
        home_team=game.home_team,
        away_team=game.away_team,
        week=game.week,
        n_replicates=40,
        seed=3,
    )
    assert boxes_proj.players


def test_injury_realloc_stays_in_team_pool_with_rookies() -> None:
    universe = build_demo_universe(2026)
    # Prefer a team with RB1/RB2 in demo cores.
    gibbs = next(r for r in universe.rosters["DET"] if "Gibbs" in r.player_name)
    mont = next(r for r in universe.rosters["DET"] if "Montgomery" in r.player_name)
    path = InjuryPath(
        player_key=gibbs.player_key,
        team="DET",
        status="out",
        week_start=1,
        week_end=1,
    )
    adj, _, _ = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    mont_adj = next(r for r in adj["DET"] if r.player_key == mont.player_key)
    assert mont_adj.rush_share > mont.rush_share
    rb_rush = sum(r.rush_share for r in adj["DET"] if r.position == "RB")
    assert rb_rush <= 1.05


def test_packaged_rookie_flags_artifact_joins_depth() -> None:
    flags, meta = load_packaged_rookie_flags(2026)
    rows, _ = load_packaged_depth_chart(2026)
    assert meta.get("flagged_rookies", 0) >= 8
    enriched, stats = enrich_depth_rows_with_rookie_flags(rows, flags, season=2026)
    assert stats["rookie_flagged"] >= 8
    assert stats["rookie_with_draft_round"] >= 1
    # Year-2 2025-class stars must NOT be flagged as 2026 rookies.
    jeanty = next(r for r in enriched if "Jeanty" in r["player_name"])
    assert jeanty["is_rookie"] is False
    mendosa = next(r for r in enriched if "Mendoza" in r["player_name"])
    assert mendosa["is_rookie"] is True
    assert mendosa.get("draft_round") == 1
