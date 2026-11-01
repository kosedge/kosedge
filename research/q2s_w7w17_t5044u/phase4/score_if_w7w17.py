#!/usr/bin/env python3
"""t5044u Phase 4 — new research copy of score_t4910u for 2017 W7–W17.

Loads IF from pinned tip 6ca03716. blend=0, sims=4000, packet rest only.
Scores 141 complete 27/27 games. 24 T2 partial stay sealed, not scored.
Does NOT open 1ee90fac. Does NOT join realized scores. Does NOT look.
Does NOT edit sealed score_t4910u.py.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PACKET = Path(__file__).resolve().parents[1]
PHASE4 = Path(__file__).resolve().parent
GATE1 = PACKET / "gate1"
GATE2 = PACKET / "gate2"
PINS = PACKET / "pins"
MATRIX_PATH = GATE2 / "RECON_MATRIX_W7W17.csv"
IDENT_PATH = GATE1 / "IDENTITY_MANIFEST.json"
IF_TREE = Path("/tmp/t5044u-if-6ca03716/services/model-service")

IF_TIP = "6ca03716fe52930332d5ffba302c312a651980cc"
SIM_SHA256 = "52d9e90927c9bc9d48314659d2735b9647974f20c2f15944855727e0cfd86385"
FW_SHA256 = "a0051cc423bd733c3342272fdb297ea8f22cf2a4569fe0f9ca0ec47eda04d0e3"
MATRIX_SHA256 = "b56be1462e591ac5e04cfaf860938118e013664a2c661e156afdf5c5f41bc216"
GAMES_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OUTCOMES_SHA256 = "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081"
SEED_BASE = 201710
SEED_MOD = 1000003
SIMULATIONS = 4000
MARKET_BLEND = 0

REQUIRED_FIELDS = [
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
]
CONTEXT_STR = {"game_id", "home_team", "away_team"}
FORBIDDEN_REST_NAMES = (
    "rest_days_from_schedule",
    "verify_rest_days",
    "nfl_offline_if_eval_w8",
)
SEALED_T2 = {
    "2017_07_TB_BUF",
    "2017_07_DAL_SF",
    "2017_07_CIN_PIT",
    "2017_07_SEA_NYG",
    "2017_08_HOU_SEA",
    "2017_08_PIT_DET",
    "2017_09_ARI_SF",
    "2017_09_BAL_TEN",
    "2017_09_CIN_JAX",
    "2017_09_LA_NYG",
    "2017_09_DET_GB",
    "2017_10_CLE_DET",
    "2017_10_GB_CHI",
    "2017_10_LAC_JAX",
    "2017_10_MIN_WAS",
    "2017_10_NE_DEN",
    "2017_10_PIT_IND",
    "2017_11_BAL_GB",
    "2017_11_KC_NYG",
    "2017_11_NE_OAK",
    "2017_11_PHI_DAL",
    "2017_12_CAR_NYJ",
    "2017_12_SEA_SF",
    "2017_12_TEN_IND",
}
EXAMINED_70 = {
    "2017_02_ARI_IND",
    "2017_02_BUF_CAR",
    "2017_02_CLE_BAL",
    "2017_02_DAL_DEN",
    "2017_02_DET_NYG",
    "2017_02_GB_ATL",
    "2017_02_HOU_CIN",
    "2017_02_MIN_PIT",
    "2017_02_NE_NO",
    "2017_02_NYJ_OAK",
    "2017_02_PHI_KC",
    "2017_02_SF_SEA",
    "2017_02_TEN_JAX",
    "2017_02_WAS_LA",
    "2017_03_ATL_DET",
    "2017_03_BAL_JAX",
    "2017_03_CIN_GB",
    "2017_03_CLE_IND",
    "2017_03_DAL_ARI",
    "2017_03_DEN_BUF",
    "2017_03_HOU_NE",
    "2017_03_KC_LAC",
    "2017_03_LA_SF",
    "2017_03_MIA_NYJ",
    "2017_03_NO_CAR",
    "2017_03_NYG_PHI",
    "2017_03_OAK_WAS",
    "2017_03_PIT_CHI",
    "2017_03_SEA_TEN",
    "2017_03_TB_MIN",
    "2017_04_BUF_ATL",
    "2017_04_CAR_NE",
    "2017_04_CHI_GB",
    "2017_04_CIN_CLE",
    "2017_04_DET_MIN",
    "2017_04_IND_SEA",
    "2017_04_JAX_NYJ",
    "2017_04_LA_DAL",
    "2017_04_NO_MIA",
    "2017_04_NYG_TB",
    "2017_04_OAK_DEN",
    "2017_04_PHI_LAC",
    "2017_04_PIT_BAL",
    "2017_04_SF_ARI",
    "2017_04_TEN_HOU",
    "2017_04_WAS_KC",
    "2017_05_ARI_PHI",
    "2017_05_BAL_OAK",
    "2017_05_BUF_CIN",
    "2017_05_CAR_DET",
    "2017_05_GB_DAL",
    "2017_05_JAX_PIT",
    "2017_05_KC_HOU",
    "2017_05_LAC_NYG",
    "2017_05_MIN_CHI",
    "2017_05_NE_TB",
    "2017_05_NYJ_CLE",
    "2017_05_SEA_LA",
    "2017_05_SF_IND",
    "2017_05_TEN_MIA",
    "2017_06_CHI_BAL",
    "2017_06_CLE_HOU",
    "2017_06_GB_MIN",
    "2017_06_IND_TEN",
    "2017_06_LAC_OAK",
    "2017_06_LA_JAX",
    "2017_06_NE_NYJ",
    "2017_06_PHI_CAR",
    "2017_06_PIT_KC",
    "2017_06_TB_ARI",
}


class ScoreRefuse(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seed_for(game_id: str) -> int:
    digest = hashlib.sha256(game_id.encode()).hexdigest()
    return SEED_BASE + (int(digest[:12], 16) % SEED_MOD)


def assert_no_forbidden_open() -> None:
    games = PINS / "games_4fe1cdd7.csv"
    outcomes = PINS / "outcomes_2013_2022_score_only.csv"
    if sha256_file(games) != GAMES_SHA256:
        raise ScoreRefuse("games pin drifted")
    if sha256_file(outcomes) != OUTCOMES_SHA256:
        raise ScoreRefuse("outcomes pin drifted")


def coerce_value(field: str, raw: str) -> Any:
    if field in CONTEXT_STR:
        return raw
    if field in {"matchup_season", "matchup_week"}:
        return int(float(raw))
    return float(raw)


def is_complete(fields: dict[str, dict[str, str]]) -> bool:
    if set(REQUIRED_FIELDS) - set(fields):
        return False
    return all(fields[f]["status"] == "DERIVED_PREGAME" for f in REQUIRED_FIELDS)


def load_matrix() -> dict[str, dict[str, dict[str, str]]]:
    if sha256_file(MATRIX_PATH) != MATRIX_SHA256:
        raise ScoreRefuse(
            f"RECON_MATRIX_W7W17.csv sha != b56be146 — refuse (do not rescore)"
        )
    out: dict[str, dict[str, dict[str, str]]] = {}
    with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            out.setdefault(row["game_id"], {})[row["field"]] = row
    return out


def assemble_sample() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ident = json.loads(IDENT_PATH.read_text())
    if int(ident.get("n") or 0) != 165:
        raise ScoreRefuse(f"identity n={ident.get('n')} != 165")
    by_id = {g["game_id"]: g for g in ident["games"]}
    if set(by_id) != {g["game_id"] for g in ident["games"]} or len(by_id) != 165:
        raise ScoreRefuse("identity game_id set != 165")
    matrix = load_matrix()
    if set(matrix) != set(by_id):
        raise ScoreRefuse("matrix game_ids != Gate 1 identities")

    scored: list[dict[str, Any]] = []
    sealed_partial: list[dict[str, Any]] = []
    unexpected: list[dict[str, Any]] = []

    for gid in sorted(by_id):
        meta = by_id[gid]
        fields = matrix[gid]
        complete = is_complete(fields)
        if gid in SEALED_T2:
            if complete:
                unexpected.append(
                    {
                        "game_id": gid,
                        "reason": "preregistered T2 unexpectedly 27/27 complete",
                    }
                )
                continue
            sealed_partial.append(
                {
                    "game_id": gid,
                    "week": int(meta["week"]),
                    "home_team": meta["home_team"],
                    "away_team": meta["away_team"],
                    "status": "SEALED_T2_NOT_SCORED",
                    "complete_27_27": False,
                    "kickoff_utc": meta["kickoff_utc"],
                    "rest_days_et": meta["rest_days_et"],
                    "rest_bind": "BIND_PACKET_ONLY",
                }
            )
            continue
        if not complete:
            missing = [
                f
                for f in REQUIRED_FIELDS
                if f not in fields or fields[f]["status"] != "DERIVED_PREGAME"
            ]
            unexpected.append(
                {
                    "game_id": gid,
                    "reason": "incomplete beyond sealed T2 24",
                    "missing_fields": missing,
                }
            )
            continue
        if gid in EXAMINED_70:
            unexpected.append(
                {"game_id": gid, "reason": "examined 70 leaked into W7–W17 score set"}
            )
            continue
        row: dict[str, Any] = {
            "game_id": gid,
            "complete_27_27": True,
            "kickoff_utc": meta["kickoff_utc"],
            "forecast_cutoff_utc": meta.get("forecast_cutoff_utc"),
            "rating_week_contiguous": meta.get("rating_week_contiguous"),
            "rest_bind": "BIND_PACKET_ONLY",
            "rest_lineage": "155d3ca0_ET_DOW",
        }
        for field in REQUIRED_FIELDS:
            row[field] = coerce_value(field, fields[field]["reconstructed_value"])
        rest_et = float(meta["rest_days_et"])
        if float(row["rest_days_home"]) != rest_et or float(row["rest_days_away"]) != rest_et:
            unexpected.append(
                {
                    "game_id": gid,
                    "reason": "packet rest_days_* != identity rest_days_et",
                    "rest_home": row["rest_days_home"],
                    "rest_away": row["rest_days_away"],
                    "rest_et": rest_et,
                }
            )
            continue
        row["rest_days_home_packet"] = row["rest_days_home"]
        row["rest_days_away_packet"] = row["rest_days_away"]
        scored.append(row)

    if unexpected:
        raise ScoreRefuse("assemble refused: " + json.dumps(unexpected)[:1200])
    if len(scored) != 141:
        raise ScoreRefuse(f"n complete assembled {len(scored)} != 141")
    if {p["game_id"] for p in sealed_partial} != SEALED_T2:
        raise ScoreRefuse("sealed partial set != T2 24")
    if set(r["game_id"] for r in scored) & EXAMINED_70:
        raise ScoreRefuse("examined 70 intersect score set")
    if set(r["game_id"] for r in scored) & SEALED_T2:
        raise ScoreRefuse("T2 ids in score set")
    return scored, sealed_partial


def import_if():
    if not IF_TREE.is_dir():
        raise ScoreRefuse(
            f"IF worktree missing at {IF_TREE}. "
            "git worktree add /tmp/t5044u-if-6ca03716 "
            "6ca03716fe52930332d5ffba302c312a651980cc"
        )
    if str(IF_TREE) not in sys.path:
        sys.path.insert(0, str(IF_TREE))
    import src.services.nfl_simulator as sim  # type: ignore

    sim_path = Path(sim.__file__)
    fw_path = IF_TREE / "src/services/nfl_handicapping_framework.py"
    sim_sha = sha256_file(sim_path)
    fw_sha = sha256_file(fw_path)
    if sim_sha != SIM_SHA256:
        raise ScoreRefuse(f"simulator sha {sim_sha} != 52d9e909 pin")
    if fw_sha != FW_SHA256:
        raise ScoreRefuse(f"framework sha {fw_sha} != a0051cc4 pin")
    src = sim_path.read_text(encoding="utf-8")
    for name in FORBIDDEN_REST_NAMES:
        if name in src:
            raise ScoreRefuse(f"IF simulator source mentions forbidden rest helper {name}")
    return sim


def build_inputs(sim: Any, game: dict[str, Any]):
    kwargs = {field: game[field] for field in REQUIRED_FIELDS}
    return sim.NflGameInputs(**kwargs)


def score_game(sim: Any, game: dict[str, Any]) -> dict[str, Any]:
    inputs = build_inputs(sim, game)
    if float(inputs.rest_days_home) != float(game["rest_days_home_packet"]):
        raise ScoreRefuse(f"{game['game_id']} rest_days_home not bound from packet")
    if float(inputs.rest_days_away) != float(game["rest_days_away_packet"]):
        raise ScoreRefuse(f"{game['game_id']} rest_days_away not bound from packet")
    seed = seed_for(game["game_id"])
    projection = sim.simulate_nfl_game_independent_fair(
        inputs,
        simulations=SIMULATIONS,
        seed=seed,
        market_spread_home=None,
        market_total=None,
    )
    block = projection.get("independent_fair") or {}
    if block.get("market_blend") != 0:
        raise ScoreRefuse(f"{game['game_id']} market_blend {block.get('market_blend')} != 0")
    margin_mu, total_mu = sim.independent_fair_mus(projection)
    markets = projection.get("markets") or {}
    if not math.isfinite(float(margin_mu)) or not math.isfinite(float(total_mu)):
        raise ScoreRefuse(f"{game['game_id']} non-finite IF mus")
    return {
        "game_id": game["game_id"],
        "season": int(game["matchup_season"]),
        "week": int(game["matchup_week"]),
        "home_team": game["home_team"],
        "away_team": game["away_team"],
        "kickoff_utc": game["kickoff_utc"],
        "status": "SCORED",
        "complete_27_27": True,
        "seed": seed,
        "seed_formula": "201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)",
        "simulations": SIMULATIONS,
        "market_blend": 0,
        "rest_days_home": game["rest_days_home"],
        "rest_days_away": game["rest_days_away"],
        "rest_bind": "BIND_PACKET_ONLY",
        "if_tip": IF_TIP,
        "if_margin_mu": float(margin_mu),
        "if_total_mu": float(total_mu),
        "if_sigma": float(block["sigma"]),
        "if_forecast_wp_home": float(markets["home_win_prob"]),
        "if_forecast_wp_away": float(markets["away_win_prob"]),
        "if_forecast_label": projection.get("forecast_label"),
        "look_run": False,
        "realized_joined": False,
    }


def write_if_mus(
    rows: list[dict[str, Any]],
    sealed_partial: list[dict[str, Any]],
    out_path: Path | None = None,
) -> dict[str, Any]:
    scored_ids = sorted(r["game_id"] for r in rows)
    payload = {
        "ticket": "t5044u",
        "phase": 4,
        "label": "RETRO_FIT / DEV_RESEARCH",
        "cert": 0,
        "nfl": "NO-GO",
        "owner_clear_tip": "12763c08",
        "cos_accept_tip": "adbcf11d",
        "if_tip": IF_TIP,
        "simulator_sha256": SIM_SHA256,
        "framework_sha256": FW_SHA256,
        "matrix_sha256": MATRIX_SHA256,
        "matrix_sha8": "b56be146",
        "pbp_sha8": "84eacd96",
        "rest_bind": "BIND_PACKET_ONLY",
        "rest_heuristic": "155d3ca0",
        "simulations": SIMULATIONS,
        "market_blend": MARKET_BLEND,
        "seed_base": SEED_BASE,
        "seed_formula": "201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)",
        "n_identity": 165,
        "n_scored": len(rows),
        "n_sealed_t2_not_scored": len(sealed_partial),
        "selection_hash": sha256_bytes(("\n".join(scored_ids) + "\n").encode()),
        "selection_hash_recipe": "sha256(utf-8 of sorted scored game_id list joined by \\n with trailing \\n)",
        "weeks": dict(Counter(int(r["week"]) for r in rows)),
        "look_run": False,
        "q2s_emitted": False,
        "realized_joined": False,
        "opened_1ee90fac": False,
        "examined_70_pooled": False,
        "rows": rows,
        "sealed_t2_not_scored": sealed_partial,
    }
    path = out_path or (PHASE4 / "artifacts" / "IF_MUS_W7W17.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    payload["path"] = str(path.relative_to(PACKET)) if path.is_relative_to(PACKET) else str(path)
    payload["sha256"] = sha256_file(path)
    (path.with_suffix(".json.sha256")).write_text(
        f"{payload['sha256']}  {path.name}\n"
    )
    return payload


def main() -> int:
    if not (PHASE4 / "ASSUMPTIONS.md").is_file():
        raise ScoreRefuse("ASSUMPTIONS.md must exist before first IF write")
    assert_no_forbidden_open()
    games, sealed = assemble_sample()
    sim = import_if()
    rows = [score_game(sim, g) for g in games]
    failed = [r for r in rows if r.get("status") != "SCORED"]
    if failed:
        raise ScoreRefuse("IF score failures: " + json.dumps(failed)[:800])
    payload = write_if_mus(rows, sealed)
    print(
        json.dumps(
            {
                "ok": True,
                "n_scored": payload["n_scored"],
                "n_sealed_t2": payload["n_sealed_t2_not_scored"],
                "path": payload["path"],
                "sha256": payload["sha256"],
                "look_run": False,
                "opened_1ee90fac": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScoreRefuse as exc:
        print(f"SCORE_REFUSE: {exc}", file=sys.stderr)
        raise SystemExit(2)
