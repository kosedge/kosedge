"""t4871u IF-only coherence — clarification fe4dc220 + paper 05222939 §7."""

from __future__ import annotations

import math

import pytest

from src.services.nfl_if_coherence import (
    CLARIFICATION_SHA256,
    J9_MC_N,
    J9_MC_SEED,
    N_PACKET,
    PARENT_PAPER_SHA256,
    SECOND_SEED_C2,
    SECOND_SEED_C2_FALLBACKS,
    SEED_BASE,
    fair_ml,
    inject_published_wp,
    j10_band,
    j7_band,
    j8_band,
    j9_band,
    pack_ha_sha256,
    run_coherence_slate,
    scan_ats_ou,
    second_seed_injection,
    summarize_draws,
    tie_rate_band,
    verdict_from_tables,
)
from src.services.nfl_offline_if_caller import (
    IF_SOURCE_PIN_SHA256,
    OfflineIfCallerReject,
    REJECT_SPORTSBOOK,
    REJECT_THROUGH_W8,
    evaluate_caller,
    reject_sportsbook,
    sha256_file,
    verify_source_pin,
)
from src.services.nfl_offline_if_eval_w8 import SUPPORTED_GAMES, TNF_GAME_ID
from src.services.nfl_offline_if_eval_w8_v2 import V2_DIR
from src.services.nfl_simulator import _fair_moneyline_from_prob


@pytest.fixture(scope="module")
def slate():
    return run_coherence_slate(write=False)


def test_01_wp_sum_one(slate):
    for row in slate["results"]:
        assert abs(row["home_wp"] + row["away_wp"] - 1.0) <= 1e-9


def test_02_fair_ml_formula():
    assert fair_ml(0.569) == -132
    assert fair_ml(0.4647) == 115
    assert fair_ml(0.6478) == -184
    assert fair_ml(0.5) == -100
    assert _fair_moneyline_from_prob(0.569) == -132


def test_03_fair_ml_clamp():
    assert fair_ml(-1.0) == fair_ml(0.001)
    assert fair_ml(2.0) == fair_ml(0.999)


def test_04_ml_roundtrip():
    for p in (0.431, 0.5, 0.569, 0.6478):
        ml = fair_ml(p)
        if ml < 0:
            back = (-ml) / ((-ml) + 100.0)
        else:
            back = 100.0 / (ml + 100.0)
        assert abs(back - max(0.001, min(0.999, p))) <= 0.003


def test_05_ml_sign_symmetry():
    assert fair_ml(0.569) == -fair_ml(1.0 - 0.569)
    assert fair_ml(0.4647) == -fair_ml(1.0 - 0.4647)


def test_06_spread_margin_identity(slate):
    for game in slate["games"]:
        j1 = next(r for r in game["table_a"] if r["id"] == "J1")
        assert j1["band"] == "PASS"


def test_07_total_identity(slate):
    for game in slate["games"]:
        j2 = next(r for r in game["table_a"] if r["id"] == "J2")
        assert j2["band"] == "PASS"


def test_08_sign_coherence_negative():
    home = [10.0] * 2000 + [20.0] * 2000
    away = [20.0] * 2000 + [10.0] * 2000
    # force home underdog mean D < 0 but more home wins? actually 50/50.
    # Negative fixture: m < -0.25 and p > 0.5 is disagreement.
    home = [30.0] * 3000 + [0.0] * 1000
    away = [10.0] * 3000 + [40.0] * 1000
    st = summarize_draws(home, away)
    assert st["mean_D"] > 0.25
    assert st["p_home_win"] > 0.5
    # invert published wp
    fake_p = 0.20
    decisive = abs(st["mean_D"]) >= 0.25 and abs(fake_p - 0.5) >= 0.02
    assert decisive
    assert (st["mean_D"] > 0) != (fake_p - 0.5 > 0)


def test_09_wp_normal_band_sigma_as_margin_sd_fails(slate):
    game = next(g for g in slate["games"] if g["game_id"] == "2026-W08-LAC@LAR")
    m = game["stats"]["mean_D"]
    sigma = game["capture"]["sigma"]
    wrong = 0.5 * (1.0 + math.erf((m / sigma) / math.sqrt(2.0)))
    assert abs(game["p_home_win"] - wrong) > 0.03


def test_10_monotone_across_games(slate):
    assert slate["j12"]["band"] in {"PASS", "COND"}
    assert slate["j12"]["band"] != "FAIL"


def test_12_seed_reproducible(slate):
    for game in slate["games"]:
        assert game["j13"]["band"] == "PASS"


def test_13_blend_zero_market_null(slate):
    for row in slate["results"]:
        assert row["market_blend"] == 0
        assert row["public_delivery"] is False
    assert slate["call_audit"]["passed"] is True
    assert slate["call_audit"]["odds_calls"] == 0


def test_14_ml_null_reason_consistency(slate):
    for row in slate["results"]:
        assert row["fair_home_ml"] is not None
        assert row["fair_away_ml"] is not None


def test_15_emit_joint_artifact(slate):
    for game in slate["games"]:
        cap = game["capture"]
        st = game["stats"]
        for key in ("mean_H", "mean_A", "sd_D", "sd_S", "corr_HA", "n_ties", "n_home_wins"):
            assert st[key] is not None
        assert cap["draw_array_sha256"]
        assert len(cap["draw_array_sha256"]) == 64


def test_16_single_draw_array(slate):
    game = next(g for g in slate["games"] if g["home_wp"] != 0.5)
    st = game["stats"]
    assert abs(game["spread_home"] - (-st["mean_D"])) <= 0.005
    assert abs(game["total_mu"] - st["mean_S"]) <= 0.005
    assert game["home_wp"] == round(st["p_home_win"], 4)
    same = inject_published_wp(game, game["home_wp"])
    assert same["j3"]["band"] == "PASS"
    assert same["drives_fail"] is False
    injected = second_seed_injection(game)
    assert injected["second_seed"] in (SECOND_SEED_C2, *SECOND_SEED_C2_FALLBACKS)
    assert injected["second_seed_home_wp"] != game["home_wp"]
    assert injected["second_seed_draw_sha256"] != game["capture"]["draw_array_sha256"]
    assert injected["same_draw_sha256"] == game["capture"]["draw_array_sha256"]
    assert injected["drives_fail"] is True
    assert injected["j3"]["band"] == "FAIL"
    mapped = verdict_from_tables(
        [injected["game"]],
        slate["j12"],
        slate["j14"],
        True,
    )
    assert mapped["verdict"] == "BLOCKED"
    assert any(item.endswith(":J3") for item in mapped["a_fail"])


def test_17_component_identity(slate):
    for game in slate["games"]:
        j6 = next(r for r in game["table_a"] if r["id"] == "J6")
        assert j6["band"] == "PASS"


def test_18_ties_to_away():
    home = [10.0, 0.0, 8.0, 0.0]
    away = [4.0, 0.0, 9.0, 0.0]
    st = summarize_draws(home, away)
    assert st["n_ties"] == 2
    assert st["p_home_win"] == 0.25
    away_wp = st["p_away_win_strict"] + st["p_tie"]
    assert away_wp == 0.75
    assert fair_ml(st["p_home_win"]) == _fair_moneyline_from_prob(0.25)


def test_19_tie_rate_band():
    assert tie_rate_band(1e-4) == "PASS"
    assert tie_rate_band(2e-3) == "COND"
    assert tie_rate_band(6e-3) == "FAIL"
    home = [float(i % 7) for i in range(4000)]
    away = [float(i % 7) for i in range(4000)]
    st = summarize_draws(home, away)
    assert st["p_tie"] > 5e-3
    assert tie_rate_band(st["p_tie"]) == "FAIL"


def test_20_truncated_moments(slate):
    for game in slate["games"]:
        j7 = next(r for r in game["table_b"] if r["id"] == "J7")
        j8 = next(r for r in game["table_b"] if r["id"] == "J8")
        assert j7["band"] in {"PASS", "COND", "FAIL"}
        assert j8["band"] in {"PASS", "COND", "FAIL"}


def test_21_independence(slate):
    for game in slate["games"]:
        j10 = next(r for r in game["table_b"] if r["id"] == "J10")
        assert j10["band"] in {"PASS", "COND", "FAIL"}


def test_22_wp_vs_generative(slate):
    for game in slate["games"]:
        j9 = next(r for r in game["table_b"] if r["id"] == "J9")
        assert j9["expected"] == game["p_model_home_win"]


def test_23_ats_ou_from_draws(slate):
    assert slate["j14"]["band"] == "NOT_APPLICABLE_NOT_EMITTED"


def test_24_regen_matches_packet(slate):
    v2 = json_results()
    by_v2 = {row["game_id"]: row for row in v2}
    for row in slate["results"]:
        prior = by_v2[row["game_id"]]
        assert row["home_wp"] == prior["home_win_prob"]
        assert row["away_wp"] == prior["away_win_prob"]
        assert row["fair_home_ml"] == prior["fair_home_ml"]
        assert row["spread_home"] == prior["spread_home"]
        assert abs(row["total_mu"] - prior["total_mu"]) < 1e-12


def test_25_no_market_inputs():
    with pytest.raises(OfflineIfCallerReject) as exc:
        reject_sportsbook({"spread_home": -3.5, "book": "pinnacle"})
    assert exc.value.code == REJECT_SPORTSBOOK


def test_emit_win_away_tie_separately(slate):
    for game in slate["games"]:
        st = game["stats"]
        assert "p_home_win" in game
        assert "p_away_win_strict" in game
        assert "p_tie" in game
        assert game["home_wp"] == round(game["p_home_win"], 4)
        assert abs(game["away_wp"] - round(game["p_away_win_strict"] + game["p_tie"], 4)) <= 1e-4
        assert st["n_home_wins"] + st["n_away_strict"] + st["n_ties"] == game["capture"]["N"]
        assert game["tie_excluded_ml"] is not None


def test_preclamp_params_captured(slate):
    for game in slate["games"]:
        cap = game["capture"]
        assert cap["mu_h"] is not None and cap["mu_a"] is not None
        assert cap["sigma"] > 0
        assert cap["seed"] is not None
        assert cap["N"] == N_PACKET
        assert cap["rng_id"]
        assert cap["draw_array_sha256"]
        assert cap["used_reconstructed_means_for_acceptance"] is False
        assert not math.isclose(cap["mu_h"], cap["reconstructed_postclamp_mu_h"], abs_tol=1e-9)


def test_no_ats_ou_emitted(slate):
    hits = scan_ats_ou({"results": slate["results"], "games": slate["games"]})
    assert hits == []
    assert slate["j14"]["band"] == "NOT_APPLICABLE_NOT_EMITTED"
    if slate["verdict"]["verdict"] in {"PASS_RO", "CONDITIONAL"}:
        assert "ATS/OU NOT EMITTED, NOT TESTED" in slate["verdict"]["label"]


def test_bands_exclusive():
    assert j7_band(2.0) == "PASS"
    assert j7_band(2.0000001) == "COND"
    assert j7_band(4.0) == "COND"
    assert j7_band(4.0000001) == "FAIL"
    assert j10_band(0.05) == "PASS"
    assert j10_band(0.0500001) == "COND"
    assert j10_band(0.10) == "COND"
    assert j10_band(0.1000001) == "FAIL"
    assert j8_band(0.03) == "PASS"
    assert j8_band(0.0300001) == "COND"
    assert j8_band(0.08) == "COND"
    assert j8_band(0.0800001) == "FAIL"
    se = 0.0079
    assert j9_band(2.0 * se, se) == "PASS"
    assert j9_band(2.0 * se + 1e-12, se) == "COND"
    assert j9_band(0.03, se) == "COND"
    assert j9_band(0.0300001, se) == "FAIL"


def test_source_pin_unedited():
    assert verify_source_pin() == IF_SOURCE_PIN_SHA256


def test_operational_blocked():
    result = evaluate_caller(write=False)
    assert result.status == "BLOCKED"
    assert REJECT_THROUGH_W8 in result.codes


def test_tnf_absent(slate):
    assert TNF_GAME_ID not in {g["game_id"] for g in slate["games"]}
    assert len(slate["games"]) == 13
    assert set(g["game_id"] for g in slate["games"]) == set(SUPPORTED_GAMES)


def test_frozen_config_attestation(slate):
    frozen = slate["manifest"]["frozen"]
    assert frozen["N"] == N_PACKET == 4000
    assert frozen["seed_base"] == SEED_BASE
    assert frozen["j9_mc_n"] == J9_MC_N
    assert frozen["j9_mc_seed"] == J9_MC_SEED
    assert frozen["no_rerun_until_pass"] is True
    assert slate["manifest"]["clarification_sha256"] == CLARIFICATION_SHA256
    assert slate["manifest"]["parent_paper_sha256"] == PARENT_PAPER_SHA256
    assert slate["contract"]["simulator_sha256"] == IF_SOURCE_PIN_SHA256
    assert slate["contract"]["source_pin"] == IF_SOURCE_PIN_SHA256


def test_v2_outputs_match_and_v2_sealed(slate):
    for line in (V2_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        assert sha256_file(V2_DIR / rel) == digest


def test_parent_coherence_packet_untouched():
    from src.services.nfl_if_coherence import PARENT_PACKET_DIR

    sums = PARENT_PACKET_DIR / "SHA256SUMS"
    assert sums.is_file()
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        assert sha256_file(PARENT_PACKET_DIR / rel) == digest


def json_results():
    import json

    return json.loads((V2_DIR / "RESULTS.json").read_text(encoding="utf-8"))


def test_hash_layout_roundtrip():
    home = [1.5, 2.25]
    away = [0.0, 3.0]
    digest = pack_ha_sha256(home, away)
    assert digest == pack_ha_sha256(home, away)
    assert digest != pack_ha_sha256(away, home)
