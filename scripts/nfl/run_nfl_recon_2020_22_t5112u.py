#!/usr/bin/env python3
"""t5112u — 2020/2021/2022 REG recon + 2020–23 produce-μ / forecast freeze.

Same hash-verified helpers as t5111u. Per-season completeness seals BEFORE PBP.
Does not score outcomes, open a look, Stage C, or 1ee90fac. CERT=0.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.builder import build_forecasts, hash_forecasts  # noqa: E402
from src.services.nfl_t5107u.evaluator import freeze_forecast_cohort  # noqa: E402
from src.services.nfl_t5107u.if_control import REQUIRED_FIELDS  # noqa: E402
from src.services.nfl_t5107u.inputs import (  # noqa: E402
    GAMES_SHA256,
    OUTCOMES_SHA256,
    SOURCE_SHA,
    sha256_file,
)
from src.services.nfl_t5107u.manifest import DESIGN_SEAL_SHA256  # noqa: E402
from src.services.nfl_t5107u.recon_driver import (  # noqa: E402
    DEFAULT_GAMES_CANDIDATES,
    DEFAULT_OUTCOMES_CANDIDATES,
    DEFAULT_PBP_ARCHIVE,
    DEFAULT_SCORES_2023,
    HELPER_SHA256,
    SCORES_2023_SHA256,
    ReconRefuse,
    attach_kickoffs,
    freeze_completeness,
    load_games_identity,
    load_prior_scores,
    load_verified_helper,
    reconstruct_slate,
    refuse_forbidden_path,
    sha256_text,
)

OUT = ROOT / "data/ops/nfl-forecast-builder-t5107u/recon"
NEW_SEASONS = (2020, 2021, 2022)
ALL_SEASONS = (2020, 2021, 2022, 2023)
SPLIT = {2020: "DEV", 2021: "DEV", 2022: "EVAL", 2023: "EVAL"}


def _write_csv(path: Path, rows: list[dict]) -> str:
    if not rows:
        raise ReconRefuse(f"no rows for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return sha256_file(path)


def _packet_from_rows(rows: list[dict]) -> dict:
    packet = {}
    for row in rows:
        packet[row["field"]] = {
            "status": row["status"],
            "reconstructed_value": row["reconstructed_value"],
        }
    return packet


def reconstruct_season(season: int, helper, games, completed) -> dict:
    season_games = [g for g in games if int(g["season"]) == season]
    if not season_games:
        raise ReconRefuse(f"no games.csv identity for {season}")
    seal = freeze_completeness(season_games, completed, helper)
    if not seal.get("frozen_before_errors") or not seal.get("frozen_before_pbp_open"):
        raise ReconRefuse(f"{season} completeness not frozen before PBP")
    targets = [g for g in season_games if int(g["week"]) >= 2]
    result = reconstruct_slate(
        targets=targets,
        games=games,
        completed=completed,
        helper=helper,
        archive=DEFAULT_PBP_ARCHIVE,
        pbp_sha_by_season={season: SOURCE_SHA[season]},
        completeness_seal=seal,
    )
    max_week = max(int(g["week"]) for g in season_games)
    stem = f"{season}_REG_W2W{max_week}"
    matrix_path = OUT / f"RECON_MATRIX_{stem}.csv"
    file_sha = _write_csv(matrix_path, result["matrix"])
    seal_path = OUT / f"COMPLETENESS_SEAL_{season}_REG.json"
    seal_path.write_text(json.dumps(seal, indent=2, default=str) + "\n", encoding="utf-8")
    summary = {
        "season": season,
        "split": SPLIT[season],
        "weeks": f"2-{max_week}",
        "n_identity": len(season_games),
        "n_targets_reconstructed": len(targets),
        "n_eligible": seal["n_eligible"],
        "n_excluded": seal["n_excluded"],
        "completeness_sha256": seal["completeness_sha256"],
        "completeness_file_sha256": sha256_file(seal_path),
        "matrix_sha256": result["matrix_sha256"],
        "matrix_file_sha256": file_sha,
        "n_complete_27": result["n_complete_27"],
        "n_partial": result["n_partial"],
        "n_cells": result["n_cells"],
        "partial": result["partial"],
        "label": result["label"],
        "fit_label": result["fit_label"],
        "research_label": result["research_label"],
        "cert_candidate": 0,
        "helper_sha256": HELPER_SHA256,
        "frozen_before_errors": True,
        "opened_1ee90fac": False,
    }
    (OUT / f"RECON_SUMMARY_{stem}.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "summary": summary,
        "result": result,
        "matrix_path": str(matrix_path),
        "seal_path": str(seal_path),
    }


def load_q2_history(helper) -> list[dict]:
    """Score-only 2013–23 for Q2 as-of carry. Not a look / not Stage C."""
    games_path = next(p for p in DEFAULT_GAMES_CANDIDATES if p.is_file())
    refuse_forbidden_path(games_path)
    if sha256_file(games_path) != GAMES_SHA256:
        raise ReconRefuse("games pin drifted for Q2 history")
    identity = {}
    with games_path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            season = int(raw["season"])
            if season >= 2024:
                raise ReconRefuse(f"sealed season in Q2 games {season}")
            if season < 2013:
                continue
            week = int(raw["week"])
            if week < 1 or week > 18:
                continue
            identity[(season, week, raw["home"], raw["away"])] = {
                "season": season,
                "week": week,
                "game_id": raw["game_id"],
                "home": raw["home"],
                "away": raw["away"],
                "kickoff_utc": raw["kickoff_utc"],
                "season_type": "REG",
            }
    outcomes = next(p for p in DEFAULT_OUTCOMES_CANDIDATES if p.is_file())
    refuse_forbidden_path(outcomes)
    if sha256_file(outcomes) != OUTCOMES_SHA256:
        raise ReconRefuse("outcomes pin drifted for Q2 history")
    history = []
    with outcomes.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        banned = {
            c
            for c in (reader.fieldnames or [])
            if c.startswith(("trailing_", "packaged_")) or "epa" in c.lower()
        }
        if banned:
            raise ReconRefuse(f"Q2 history banned columns {sorted(banned)}")
        for raw in reader:
            season = int(raw["season"])
            if season >= 2024:
                raise ReconRefuse("sealed season in outcomes")
            key = (season, int(raw["week"]), raw["home"], raw["away"])
            hit = identity.get(key)
            if hit is None:
                continue
            history.append(
                {
                    **hit,
                    "home_score": float(raw["home_score"]),
                    "away_score": float(raw["away_score"]),
                }
            )
    if DEFAULT_SCORES_2023.is_file():
        refuse_forbidden_path(DEFAULT_SCORES_2023)
        if sha256_file(DEFAULT_SCORES_2023) != SCORES_2023_SHA256:
            raise ReconRefuse("2023 extract drifted")
        by_id = {g["game_id"]: g for g in identity.values() if g["season"] == 2023}
        with DEFAULT_SCORES_2023.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                if str(raw.get("season_type") or "REG").upper() != "REG":
                    continue
                gid = str(raw.get("game_id") or "")
                hit = by_id.get(gid)
                if hit is None:
                    home = helper.normalize_pbp_abbr(str(raw["home"]))
                    away = helper.normalize_pbp_abbr(str(raw["away"]))
                    hit = identity.get((2023, int(raw["week"]), home, away))
                if hit is None:
                    continue
                history.append(
                    {
                        **hit,
                        "home_score": float(raw["home_score"]),
                        "away_score": float(raw["away_score"]),
                    }
                )
    return history


def complete_packets(matrix_rows: list[dict]) -> dict[str, dict]:
    by_game: dict[str, list[dict]] = defaultdict(list)
    for row in matrix_rows:
        by_game[row["game_id"]].append(row)
    packets = {}
    for gid, rows in by_game.items():
        derived = [r for r in rows if r["status"] == "DERIVED_PREGAME"]
        if len(derived) != 27:
            continue
        packet = _packet_from_rows(rows)
        if any(packet.get(f, {}).get("status") != "DERIVED_PREGAME" for f in REQUIRED_FIELDS):
            continue
        packets[gid] = packet
    return packets


def freeze_forecasts(packets: dict[str, dict], history: list[dict], games: list[dict]) -> dict:
    by_id = {g["game_id"]: g for g in games}
    targets = []
    for gid, packet in packets.items():
        game = by_id.get(gid)
        if game is None:
            continue
        targets.append(game)
    if not targets:
        raise ReconRefuse("no complete 27/27 targets for forecast freeze")
    # Per-kickoff batches so history never includes the target row.
    # produce-μ runs inside resolve_if_margin (not a supplied-μ consume).
    by_kick = defaultdict(list)
    for game in targets:
        by_kick[game["kickoff_utc"]].append(game)
    forecasts = []
    for kick in sorted(by_kick):
        batch = by_kick[kick]
        hist = [h for h in history if h["kickoff_utc"] < kick]
        recon = {g["game_id"]: packets[g["game_id"]] for g in batch}
        payload = build_forecasts(
            batch,
            history=hist,
            recon_packets=recon,
            allow_eval_generation=True,
            frozen_manifest_sealed=True,
        )
        if payload.get("eval") not in (None, {}):
            raise ReconRefuse("builder attached eval — refuse (not a look)")
        if payload.get("scoring") not in (None, {}):
            raise ReconRefuse("builder attached scoring — refuse (not a look)")
        forecasts.extend(payload["forecasts"])
    produced = {
        row["game_id"]: row["m_if"]
        for row in forecasts
        if row.get("if_status") == "reconstructed" and row.get("m_if") is not None
    }
    combined = {
        "schema_version": "nfl-t5107u-forecast-v1",
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
        "purpose": "research_forecast_freeze_t5112u",
        "design_seal_sha256": DESIGN_SEAL_SHA256,
        "design_seal_is_forecast_freeze": False,
        "helper_sha256": HELPER_SHA256,
        "fit_policy": "TRANSFER_FROZEN_DEV_2013_2016",
        "if_arm": {
            "archived": 0,
            "reconstructed": sum(1 for r in forecasts if r.get("if_status") == "reconstructed"),
            "blocked": sum(1 for r in forecasts if r.get("if_status") == "blocked"),
            "total": len(forecasts),
        },
        "forecasts": forecasts,
        "eval": None,
        "scoring": None,
        "stage_c": None,
        "look": None,
        "notes": [
            "CERT=0. RESEARCH_CONSUMED_RETRO. Not a scored look.",
            "produce-μ from frozen IF 6ca03716 on complete 27/27 packets.",
            "Forecast/cohort hashes sealed before any outcome join.",
        ],
    }
    frozen = freeze_forecast_cohort(combined)
    mus_sha = sha256_text(
        json.dumps(
            {k: produced[k] for k in sorted(produced)},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return {
        "combined": combined,
        "frozen": frozen.as_dict(),
        "produced_n": len(produced),
        "produced_mus_sha256": mus_sha,
        "forecasts_sha256": hash_forecasts(combined),
        "forecast_sha256": frozen.forecast_sha256,
        "cohort_sha256": frozen.cohort_sha256,
        "n_forecasts": len(forecasts),
        "if_arm": combined["if_arm"],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    helper = load_verified_helper()
    games = load_games_identity()
    completed = attach_kickoffs(load_prior_scores(helper=helper), games)
    season_runs = {}
    all_matrix: list[dict] = []
    for season in NEW_SEASONS:
        print(json.dumps({"phase": "recon", "season": season}), flush=True)
        season_runs[season] = reconstruct_season(season, helper, games, completed)
        all_matrix.extend(season_runs[season]["result"]["matrix"])

    # Existing 2023 artifacts stay; reload matrix for combined packets.
    y2023 = OUT / "RECON_MATRIX_2023_REG_W2W18.csv"
    if y2023.is_file():
        with y2023.open(newline="", encoding="utf-8") as handle:
            all_matrix.extend(list(csv.DictReader(handle)))
        season_runs[2023] = {
            "summary": json.loads((OUT / "RECON_SUMMARY_2023_REG_W2W18.json").read_text()),
            "matrix_path": str(y2023),
            "seal_path": str(OUT / "COMPLETENESS_SEAL_2023_REG.json"),
        }

    packets = complete_packets(all_matrix)
    print(json.dumps({"phase": "produce_mu", "n_complete_packets": len(packets)}), flush=True)
    history = load_q2_history(helper)
    freeze = freeze_forecasts(packets, history, games)

    binding = {
        "schema_version": "nfl-t5112u-recon-bindings-2020-2023-v1",
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
        "alex_return": "7e88850996588a3467c234e74f74cce994c56bd77837a56b0ebb2921888d5220",
        "helper_sha256": HELPER_SHA256,
        "design_seal_sha256": DESIGN_SEAL_SHA256,
        "design_seal_is_forecast_freeze": False,
        "scored_look": False,
        "stage_c": False,
        "opened_1ee90fac": False,
        "seasons": {
            str(season): {
                **{
                    k: v
                    for k, v in season_runs[season]["summary"].items()
                    if k != "partial"
                },
                "split": SPLIT[season],
            }
            for season in ALL_SEASONS
            if season in season_runs
        },
        "combined": {
            "n_complete_27_packets": len(packets),
            "n_forecasts": freeze["n_forecasts"],
            "if_arm": freeze["if_arm"],
            "produced_mus_sha256": freeze["produced_mus_sha256"],
            "forecast_sha256": freeze["forecast_sha256"],
            "cohort_sha256": freeze["cohort_sha256"],
            "forecasts_payload_sha256": freeze["forecasts_sha256"],
        },
        "written_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    bind_path = OUT / "RECON_BINDINGS_2020_2023.json"
    bind_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    freeze_path = ROOT / "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json"
    freeze_doc = {
        "schema_version": "nfl-t5112u-forecast-freeze-v1",
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
        "design_seal_sha256": DESIGN_SEAL_SHA256,
        "design_seal_is_forecast_freeze": False,
        "forecast_sha256": freeze["forecast_sha256"],
        "cohort_sha256": freeze["cohort_sha256"],
        "forecasts_payload_sha256": freeze["forecasts_sha256"],
        "produced_mus_sha256": freeze["produced_mus_sha256"],
        "n_forecasts": freeze["n_forecasts"],
        "if_arm": freeze["if_arm"],
        "sealed_before_outcome_join": True,
        "eval": None,
        "scoring": None,
        "look": None,
        "stage_c": None,
        "game_ids": freeze["frozen"]["game_ids"],
        "forecasts": freeze["combined"]["forecasts"],
    }
    freeze_path.write_text(json.dumps(freeze_doc, indent=2) + "\n", encoding="utf-8")
    summary = {
        "binding_sha256": sha256_file(bind_path),
        "freeze_file_sha256": sha256_file(freeze_path),
        "forecast_sha256": freeze["forecast_sha256"],
        "cohort_sha256": freeze["cohort_sha256"],
        "n_complete_packets": len(packets),
        "n_forecasts": freeze["n_forecasts"],
        "if_arm": freeze["if_arm"],
        "seasons": {str(s): season_runs[s]["summary"] for s in NEW_SEASONS},
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
