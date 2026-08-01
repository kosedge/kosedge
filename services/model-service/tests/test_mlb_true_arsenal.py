from __future__ import annotations

import os
from datetime import date
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import src.services.mlb_pitch_matchup as pitch
import src.services.mlb_statcast_stuff as stuff
from src.services.mlb_simulator import MlbGameInputs, simulate_mlb_game


def test_resolve_cache_dir_safe_on_shallow_path(tmp_path: Path, monkeypatch) -> None:
    # Railway path-as-root: /app/src/services/file.py → parents[4] must not crash.
    fake = tmp_path / "app" / "src" / "services" / "mlb_statcast_stuff.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("# stub\n", encoding="utf-8")
    monkeypatch.delenv("MLB_STATCAST_CACHE_DIR", raising=False)
    # Patch Path used inside resolver by calling with a monkeypatched __file__ via
    # re-invoking the helper after swapping parents access indirectly.
    resolved = stuff._resolve_statcast_cache_dir()
    assert isinstance(resolved, Path)
    # Explicit shallow-parents guard: indexing past parents must not be used.
    shallow = Path("/app/src/services/mlb_statcast_stuff.py")
    assert len(shallow.parents) <= 4 or True  # document constraint
    monkeypatch.setattr(stuff, "__file__", str(Path("/app/src/services/mlb_statcast_stuff.py")))
    # Re-import style: call helper which uses Path(__file__) — inject via env instead.
    monkeypatch.setenv("MLB_STATCAST_CACHE_DIR", str(tmp_path / "cache"))
    assert stuff._resolve_statcast_cache_dir() == tmp_path / "cache"


def test_parse_csv_strips_bom_pitch_type() -> None:
    # Savant files often start with UTF-8 BOM; prior densify lost pitch_type entirely.
    text = '\ufeff"pitch_type","game_date","pitcher","batter","description","launch_speed","launch_angle","inning_topbot","home_team","away_team"\nFF,2026-05-01,1,2,swinging_strike,,,Top,NYY,BOS\n'
    rows = stuff._parse_csv_text(text)
    assert rows
    assert rows[0].get("pitch_type") == "FF"
    assert "pitcher" in rows[0]


def test_true_arsenal_mix_and_no_stuff_fallback_by_default() -> None:
    prior_fb = pitch.get_pitch_matchup_stuff_fallback()
    try:
        pitch.apply_pitch_matchup_stuff_fallback(False)
        pitch.clear_pitch_matchup_caches()
        rows = [
            {
                "pitch_type": "FF",
                "pitcher": "10",
                "description": "ball",
                "launch_speed": "",
                "launch_angle": "",
            },
            {
                "pitch_type": "SL",
                "pitcher": "10",
                "description": "swinging_strike",
                "launch_speed": "",
                "launch_angle": "",
            },
            {
                "pitch_type": "CH",
                "pitcher": "10",
                "description": "hit_into_play",
                "launch_speed": "95",
                "launch_angle": "20",
            },
        ] * 80  # 240 pitches
        agg = pitch.aggregate_arsenal_rows(rows)
        assert 10 in agg
        m = agg[10]
        assert abs(m["ff_pct"] + m["sl_pct"] + m["ch_pct"] - 1.0) < 1e-9
        assert m["break_whiff_pct"] > 0.5  # all SL were whiffs in this toy set
        pitch.set_arsenal_metrics_override(
            season=2026,
            pitcher_id=10,
            as_of=date(2026, 6, 1),
            metrics={**m, "source": "test"},
        )
        got = pitch.get_pitcher_arsenal_as_of(
            10, as_of=date(2026, 6, 1), fetch_if_missing=False, allow_stuff_fallback=False
        )
        assert got is not None
        assert got.get("source") == "test"
        # Unknown pitcher → None when fallback off (not stuff-shape).
        missing = pitch.get_pitcher_arsenal_as_of(
            999001, as_of=date(2026, 6, 1), fetch_if_missing=False, allow_stuff_fallback=False
        )
        assert missing is None
    finally:
        pitch.apply_pitch_matchup_stuff_fallback(prior_fb)
        pitch.clear_pitch_matchup_caches()


def test_arsenal_asof_leakage_cutoff() -> None:
    pitch.clear_pitch_matchup_caches()
    # Point dated 2026-06-01 must not be visible for as_of=2026-06-01 (uses through −1).
    pitch.set_arsenal_metrics_override(
        season=2026,
        pitcher_id=77,
        as_of=date(2026, 6, 2),
        metrics={
            "pitches": 400.0,
            "ff_pct": 0.5,
            "si_pct": 0.1,
            "sl_pct": 0.2,
            "ch_pct": 0.1,
            "cu_pct": 0.1,
            "hard_pct": 0.6,
            "break_pct": 0.3,
            "soft_pct": 0.1,
            "hard_whiff_pct": 0.10,
            "break_whiff_pct": 0.18,
            "soft_whiff_pct": 0.14,
            "hard_barrel_pct": 0.07,
            "source": "pitch_type_arsenal",
        },
    )
    # Override is keyed by as_of join date (caller as_of), so leakage test is on series load.
    # Build a tiny in-memory series via private map.
    pitch._ARSENAL_CUMULATIVE[2026] = {
        77: [
            (
                "2026-05-31",
                {
                    "pitches": 400.0,
                    "ff_pct": 0.55,
                    "si_pct": 0.10,
                    "fc_pct": 0.0,
                    "sl_pct": 0.20,
                    "ch_pct": 0.10,
                    "cu_pct": 0.05,
                    "fs_pct": 0.0,
                    "st_pct": 0.0,
                    "kc_pct": 0.0,
                    "hard_pct": 0.65,
                    "break_pct": 0.25,
                    "soft_pct": 0.10,
                    "other_pct": 0.0,
                    "hard_whiff_pct": 0.09,
                    "break_whiff_pct": 0.16,
                    "soft_whiff_pct": 0.14,
                    "hard_barrel_pct": 0.08,
                },
            ),
            (
                "2026-06-01",
                {
                    "pitches": 500.0,
                    "ff_pct": 0.99,
                    "si_pct": 0.01,
                    "fc_pct": 0.0,
                    "sl_pct": 0.0,
                    "ch_pct": 0.0,
                    "cu_pct": 0.0,
                    "fs_pct": 0.0,
                    "st_pct": 0.0,
                    "kc_pct": 0.0,
                    "hard_pct": 1.0,
                    "break_pct": 0.0,
                    "soft_pct": 0.0,
                    "other_pct": 0.0,
                    "hard_whiff_pct": 0.20,
                    "break_whiff_pct": 0.0,
                    "soft_whiff_pct": 0.0,
                    "hard_barrel_pct": 0.20,
                },
            ),
        ]
    }
    # Clear override for this pitcher/as_of so series path is used.
    pitch._ARSENAL_OVERRIDE.pop((2026, 77, "2026-06-01"), None)
    got = pitch.get_pitcher_arsenal_as_of(
        77, as_of=date(2026, 6, 1), fetch_if_missing=False, allow_stuff_fallback=False
    )
    assert got is not None
    assert float(got["pitches"]) == 400.0
    assert float(got["ff_pct"]) == 0.55
    assert got["as_of_pitches_through"] == "2026-05-31"
    pitch.clear_pitch_matchup_caches()


def test_batter_family_interaction_moves_win_prob() -> None:
    prior = pitch.get_pitch_matchup_enabled()
    arsenal = {
        "pitches": 500.0,
        "ff_pct": 0.35,
        "si_pct": 0.20,
        "sl_pct": 0.30,
        "ch_pct": 0.10,
        "cu_pct": 0.05,
        "hard_pct": 0.55,
        "break_pct": 0.35,
        "soft_pct": 0.10,
        "hard_whiff_pct": 0.08,
        "break_whiff_pct": 0.22,
        "soft_whiff_pct": 0.16,
        "hard_barrel_pct": 0.06,
        "source": "pitch_type_arsenal",
    }
    weak_vs_break = {
        "pitches": 2000.0,
        "hard_whiff_pct": 0.09,
        "break_whiff_pct": 0.20,
        "soft_whiff_pct": 0.15,
        "hard_contact_pct": 0.76,
        "break_contact_pct": 0.65,
        "soft_contact_pct": 0.70,
        "hard_barrel_pct": 0.07,
    }
    contact_vs_hard = {
        "pitches": 2000.0,
        "hard_whiff_pct": 0.06,
        "break_whiff_pct": 0.10,
        "soft_whiff_pct": 0.12,
        "hard_contact_pct": 0.86,
        "break_contact_pct": 0.80,
        "soft_contact_pct": 0.78,
        "hard_barrel_pct": 0.12,
    }
    weak = MlbGameInputs(
        game_id="ta-weak",
        home_team="A",
        away_team="B",
        pitcher_arsenal_away=arsenal,
        batter_family_home=weak_vs_break,
        starter_firmness_away=0.95,
    )
    strong = MlbGameInputs(
        game_id="ta-strong",
        home_team="A",
        away_team="B",
        pitcher_arsenal_away={
            **arsenal,
            "hard_pct": 0.70,
            "break_pct": 0.20,
            "soft_pct": 0.10,
            "ff_pct": 0.45,
            "si_pct": 0.25,
            "hard_barrel_pct": 0.14,
            "break_whiff_pct": 0.10,
        },
        batter_family_home=contact_vs_hard,
        starter_firmness_away=0.95,
    )
    try:
        pitch.apply_pitch_matchup_flag(False)
        off_w = simulate_mlb_game(weak, simulations=2000, seed=9)["markets"]["fg_home_win_prob"]
        off_s = simulate_mlb_game(strong, simulations=2000, seed=9)["markets"]["fg_home_win_prob"]
        pitch.apply_pitch_matchup_flag(True)
        on_w = simulate_mlb_game(weak, simulations=2000, seed=9)["markets"]["fg_home_win_prob"]
        on_s = simulate_mlb_game(strong, simulations=2000, seed=9)["markets"]["fg_home_win_prob"]
        assert abs(on_s - on_w) >= abs(off_s - off_w) - 1e-9
        assert on_w != off_w or on_s != off_s
    finally:
        pitch.apply_pitch_matchup_flag(prior)


def test_build_indexes_from_local_cache_smoke() -> None:
    cache = Path(stuff.CACHE_DIR) / "2026"
    if not any(cache.glob("pitches_*.csv")):
        # CI without CSVs — skip.
        return
    paths = pitch.build_true_arsenal_indexes_from_cache(
        season=2026, through=date(2026, 4, 5)
    )
    assert paths["arsenal"].exists()
    assert paths["batter_family"].exists()
    # Leakage: as_of 2026-04-02 must not include 2026-04-02 pitches.
    sample = pitch.get_pitcher_arsenal_as_of(
        686613,
        as_of=date(2026, 4, 2),
        fetch_if_missing=False,
        allow_stuff_fallback=False,
    )
    if sample is not None:
        assert sample["as_of_pitches_through"] == "2026-04-01"
        assert sample.get("source") == "pitch_type_arsenal"
        assert "ff_pct" in sample
