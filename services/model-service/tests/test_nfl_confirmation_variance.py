"""Confirmation + variance — high|med|low on committed pack/situation events."""

from __future__ import annotations

import copy

from src.services.nfl_camp_sot_queue import assert_notes_cannot_touch_lines
from src.services.nfl_confirmation_variance import (
    CONFIRMATION_FIELD,
    CONFIRMATION_VARIANCE_VERSION,
    MEAN_SHOCK_SCALE,
    VARIANCE_WIDEN,
    expose_kei_mean_uncertainty,
    mean_shock_scale,
    notes_or_sleeper_cannot_close_open_competition,
    open_competition_mixture_shares,
    resolve_confirmation,
    scale_mean_shock,
    stamp_situation_event,
    variance_widen,
)
from src.services.nfl_daily_intel import ALLOWED_FIELDS, apply_intel_overrides
from src.services.nfl_kei_week1_reprice import Week1Pack, apply_week1_kei_reprice


def _handicap(spread: float = -3.0, total: float = 44.0) -> dict:
    return {"spread_home": spread, "total_mean": total, "home_win_prob": 0.58}


def test_confirmation_field_allowed() -> None:
    assert CONFIRMATION_FIELD in ALLOWED_FIELDS
    assert CONFIRMATION_VARIANCE_VERSION == "confirmation_variance_v1"


def test_high_ir_named_starter_full_mean_shock() -> None:
    assert resolve_confirmation(injury_status="ir") == "high"
    assert resolve_confirmation(competition_status="named_starter") == "high"
    assert resolve_confirmation(
        sources=["official depth chart"], confidence="high"
    ) == "high"
    assert mean_shock_scale("high") == 1.0
    assert variance_widen("high") == 1.0
    s, t, unc = scale_mean_shock(3.5, 1.5, "high")
    assert s == 3.5
    assert t == 1.5
    assert unc["mean_shock_scale"] == 1.0
    assert unc["variance_widen"] == 1.0


def test_low_beat_questionable_widens_variance_small_mean() -> None:
    assert resolve_confirmation(injury_status="questionable") == "low"
    assert resolve_confirmation(confidence="low", sources=["beat writer tweet"]) == "low"
    assert resolve_confirmation(
        sources=["sleeper://note/1"], reason="beat-only rumor"
    ) == "low"
    assert mean_shock_scale("low") == MEAN_SHOCK_SCALE["low"]
    assert variance_widen("low") == VARIANCE_WIDEN["low"]
    s, t, unc = scale_mean_shock(1.0, 0.5, "low")
    assert s == 0.1
    assert t == 0.05
    assert unc["variance_widen"] > 1.0
    assert unc["mean_shock_scale"] < 0.2


def test_med_default_half_mean() -> None:
    assert resolve_confirmation(injury_status="healthy", confidence="medium") == "med"
    s, t, unc = scale_mean_shock(2.0, 1.0, "med")
    assert s == 1.0
    assert t == 0.5
    assert unc["variance_widen"] == VARIANCE_WIDEN["med"]


def test_committed_situation_event_stamped_on_accept() -> None:
    payload = {
        "snapshot_id": "test",
        "rows": [
            {
                "team": "SEA",
                "position": "WR",
                "depth_order": 1,
                "player_id": "P1",
                "player_name": "DK Metcalf",
                "injury_status": "healthy",
            }
        ],
    }
    result = apply_intel_overrides(
        payload,
        [
            {
                "team": "SEA",
                "player_name": "DK Metcalf",
                "player_id": "P1",
                "position": "WR",
                "field": "injury_status",
                "before": "healthy",
                "after": "ir",
                "reason": "season-ending IR — official",
                "as_of": "2026-08-29",
                "confidence": "high",
                "destination": "sot",
                "sources": ["official injury report"],
            }
        ],
        as_of="2026-08-29T00:00:00Z",
    )
    assert len(result.applied) == 1
    events = result.payload.get("situation_events") or []
    assert len(events) == 1
    assert events[0]["confirmation"] == "high"
    assert events[0]["mean_shock_scale"] == 1.0
    assert events[0]["kei"]["mean"]
    assert events[0]["kei"]["uncertainty"]
    row = result.payload["rows"][0]
    assert row["confirmation"] == "high"
    assert row["injury_status"] == "ir"


def test_low_questionable_commit_widens_not_full_mean() -> None:
    payload = {
        "rows": [
            {
                "team": "WAS",
                "position": "WR",
                "depth_order": 1,
                "player_id": "P2",
                "player_name": "McLaurin",
                "injury_status": "healthy",
            }
        ],
    }
    result = apply_intel_overrides(
        payload,
        [
            {
                "team": "WAS",
                "player_name": "McLaurin",
                "player_id": "P2",
                "field": "injury_status",
                "after": "questionable",
                "reason": "beat-only — questionable for Sunday",
                "confidence": "low",
                "destination": "kei_only",
                "sources": ["beat writer"],
            }
        ],
    )
    events = result.payload.get("situation_events") or []
    assert events[0]["confirmation"] == "low"
    assert events[0]["mean_shock_scale"] == MEAN_SHOCK_SCALE["low"]
    assert events[0]["variance_widen"] == VARIANCE_WIDEN["low"]


def test_open_competition_stays_mixture() -> None:
    rows = [
        {
            "team": "ATL",
            "position": "QB",
            "depth_order": 1,
            "player_id": "P1",
            "player_name": "Penix",
            "competition_status": "open_competition",
            "snap_share_prior": 0.55,
        },
        {
            "team": "ATL",
            "position": "QB",
            "depth_order": 2,
            "player_id": "P2",
            "player_name": "Cousins",
            "competition_status": "open_competition",
            "snap_share_prior": 0.45,
        },
    ]
    mixture = open_competition_mixture_shares(rows, team="ATL", position="QB")
    assert mixture["is_open_competition"] is True
    assert mixture["crowned"] is False
    assert len(mixture["mixture"]) == 2
    assert abs(sum(m["mixture_weight"] for m in mixture["mixture"]) - 1.0) < 1e-6


def test_sleeper_notes_cannot_close_open_competition() -> None:
    row = {
        "team": "ATL",
        "position": "QB",
        "player_name": "Penix",
        "competition_status": "open_competition",
    }
    block = notes_or_sleeper_cannot_close_open_competition(
        {
            "field": "competition_status",
            "after": "named_starter",
            "sources": ["sleeper://notes/atl-qb"],
            "confidence": "medium",
            "reason": "Sleeper note crowns Penix",
        },
        row,
    )
    assert block is not None
    assert "mixture" in block.lower() or "cannot close" in block.lower()

    # Also blocked via apply_intel_overrides path.
    payload = {"rows": [copy.deepcopy(row)]}
    result = apply_intel_overrides(
        payload,
        [
            {
                "team": "ATL",
                "player_name": "Penix",
                "position": "QB",
                "field": "competition_status",
                "before": "open_competition",
                "after": "named_starter",
                "reason": "camp note — crown Penix",
                "confidence": "medium",
                "destination": "sot",
                "sources": ["camp-desk:2026-08-29:ATL"],
            }
        ],
    )
    assert result.applied == []
    assert result.skipped
    assert "mixture" in result.skipped[0]["skip_reason"].lower()
    assert result.payload["rows"][0]["competition_status"] == "open_competition"


def test_official_high_may_close_open_competition() -> None:
    payload = {
        "rows": [
            {
                "team": "ATL",
                "position": "QB",
                "player_name": "Penix",
                "player_id": "P1",
                "competition_status": "open_competition",
            }
        ],
    }
    result = apply_intel_overrides(
        payload,
        [
            {
                "team": "ATL",
                "player_name": "Penix",
                "player_id": "P1",
                "field": "competition_status",
                "before": "open_competition",
                "after": "named_starter",
                "reason": "team names Penix QB1 — official depth",
                "confidence": "high",
                "destination": "sot",
                "sources": ["official depth chart"],
                "confirmation": "high",
            }
        ],
    )
    assert len(result.applied) == 1
    assert result.payload["rows"][0]["competition_status"] == "named_starter"
    assert result.payload["rows"][0]["confirmation"] == "high"


def test_kei_exposes_mean_and_uncertainty() -> None:
    pack = Week1Pack(
        loaded=True,
        skill_by_team={
            "PIT": [
                {
                    "team": "PIT",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Starter",
                    "competition_status": "named_starter",
                    "injury_status": "ir",
                    "confirmation": "high",
                }
            ],
            "CLE": [
                {
                    "team": "CLE",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Watson",
                    "competition_status": "named_starter",
                }
            ],
        },
    )
    new_h, log = apply_week1_kei_reprice(
        handicap=_handicap(-7.0),
        home_abbr="PIT",
        away_abbr="CLE",
        week=1,
        season=2026,
        season_type="REG",
        pack=pack,
    )
    assert "mean" in log
    assert "uncertainty" in log
    assert log["mean"]["spread"] == log["spread_delta"]
    assert log["uncertainty"]["confirmation"] in {"high", "med", "low"}
    assert "variance_widen" in log["uncertainty"]
    # High IR → full mean shock (3.5 home weaker).
    assert new_h["spread_home"] == -3.5
    qb = next(e for e in log["applied_factors"] if e["factor"] == "qb_backup_dropoff")
    assert qb["confirmation"] == "high"
    assert qb["uncertainty"]["mean_shock_scale"] == 1.0


def test_kei_low_confirmation_shrinks_mean_widens_uncertainty() -> None:
    pack = Week1Pack(
        loaded=True,
        skill_by_team={
            "WAS": [
                {
                    "team": "WAS",
                    "position": "WR",
                    "depth_order": 1,
                    "player_name": "McLaurin",
                    "injury_status": "questionable",
                    "confirmation": "low",
                }
            ],
            "PHI": [
                {
                    "team": "PHI",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Hurts",
                    "competition_status": "named_starter",
                }
            ],
        },
    )
    _, log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="PHI",
        away_abbr="WAS",
        week=1,
        season=2026,
        pack=pack,
    )
    skill = [
        e
        for e in log["applied_factors"]
        if e.get("factor") == "injury_skill" and e.get("applied")
    ]
    assert skill
    assert skill[0]["confirmation"] == "low"
    # Base unresolved starter was 0.25; low scale 0.1 → 0.025
    assert abs(skill[0]["spread_pts"]) < 0.1
    assert skill[0]["uncertainty"]["variance_widen"] == VARIANCE_WIDEN["low"]
    assert log["uncertainty"]["variance_widen"] >= 1.0


def test_kei_open_competition_mixture_zero_mean() -> None:
    pack = Week1Pack(
        loaded=True,
        skill_by_team={
            "ATL": [
                {
                    "team": "ATL",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Penix",
                    "competition_status": "open_competition",
                },
                {
                    "team": "ATL",
                    "position": "QB",
                    "depth_order": 2,
                    "player_name": "Cousins",
                    "competition_status": "open_competition",
                },
            ],
            "PIT": [
                {
                    "team": "PIT",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Rodgers",
                    "competition_status": "named_starter",
                }
            ],
        },
    )
    new_h, log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="PIT",
        away_abbr="ATL",
        week=1,
        season=2026,
        pack=pack,
    )
    assert new_h["spread_home"] == -3.0
    assert log["spread_delta"] == 0.0
    assert log["qb_clear"] is False
    qb = next(
        e
        for e in log["applied_factors"]
        if e["factor"] == "qb_confirmation" and e.get("team") == "ATL"
    )
    assert qb["spread_pts"] == 0.0
    mix = (qb.get("uncertainty") or {}).get("open_competition_mixture") or {}
    assert mix.get("is_open_competition") is True
    assert mix.get("crowned") is False
    assert "mean" in log and "uncertainty" in log


def test_stamp_and_expose_helpers() -> None:
    event = stamp_situation_event(
        {
            "team": "MIN",
            "player_name": "Adams",
            "field": "injury_status",
            "after": "ir",
            "confidence": "high",
            "sources": ["official injury report"],
            "destination": "sot",
        },
        pack_row={"injury_status": "ir", "competition_status": "named_starter"},
    )
    assert event["confirmation"] == "high"
    surface = expose_kei_mean_uncertainty(
        mean_spread=0.7, mean_total=0.2, confirmation="high"
    )
    assert surface["mean"]["spread"] == 0.7
    assert surface["uncertainty"]["confirmation"] == "high"


def test_notes_still_cannot_touch_means() -> None:
    assert_notes_cannot_touch_lines()
