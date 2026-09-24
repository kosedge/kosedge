#!/usr/bin/env python3
"""Freeze runner for the isolated NFL Clock-Play Baseline v1 experiment.

The runner accepts only a committed JSON config plus synthetic/train-only
inputs.  It neither reads historical actuals nor market data, and produces no
production-facing output.  Every JSON artifact is canonicalized so a replay
with the same source, config, inputs, and seed manifest is byte-identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_clock_play_simulator import (  # noqa: E402
    ClockPlayConfig,
    ClockPlayGameInputs,
    ClockPlayTeamInput,
    derive_replicate_seed,
    simulate_clock_play_game,
    simulate_clock_play_overtime_probe,
)


ARTIFACT_ID = "Clock-Play Baseline v1"
RUNNER_VERSION = "clock-play-baseline-freeze-runner-v1"
SOURCE_FILES = (
    "services/model-service/src/services/nfl_clock_play_simulator.py",
    "services/model-service/src/services/nfl_season_engine/kicker_layer.py",
    "scripts/nfl/run_clock_play_baseline_v1.py",
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.write_bytes(_canonical_json(payload))


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected object in {path}")
    return payload


def _load_clock_play_priors(
    config_payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    engine_config = dict(
        config_payload.get("engine_config")
        if isinstance(config_payload.get("engine_config"), Mapping)
        else {}
    )
    receipts: dict[str, dict[str, str]] = {}
    for config_key, engine_key, label in (
        (
            "fourth_down_continuation_priors_path",
            "fourth_down_continuation_priors",
            "fourth_down_continuation",
        ),
        ("clock_flow_priors_path", "clock_flow_priors", "clock_flow"),
        (
            "red_zone_rush_transition_priors_path",
            "red_zone_rush_transition_priors",
            "red_zone_rush_transition",
        ),
        (
            "red_zone_pass_transition_priors_path",
            "red_zone_pass_transition_priors",
            "red_zone_pass_transition",
        ),
        (
            "red_zone_fourth_decision_priors_path",
            "red_zone_fourth_decision_priors",
            "red_zone_fourth_decision",
        ),
        (
            "pre_entry_pass_rz_priors_path",
            "pre_entry_pass_rz_priors",
            "pre_entry_pass_rz",
        ),
    ):
        raw_path = config_payload.get(config_key)
        if raw_path is None:
            continue
        path = (ROOT / str(raw_path)).resolve()
        priors_payload = _load_json_object(path)
        priors = priors_payload.get("priors")
        if not isinstance(priors, Mapping):
            raise SystemExit(f"{label} priors need a priors object")
        engine_config[engine_key] = dict(priors)
        receipts[label] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": _sha256_file(path),
        }
    return engine_config, receipts


def _as_team(raw: Mapping[str, Any]) -> ClockPlayTeamInput:
    return ClockPlayTeamInput(
        offense_rating=float(raw.get("offense_rating", 1.0)),
        defense_rating=float(raw.get("defense_rating", 1.0)),
        pace_factor=float(raw.get("pace_factor", 1.0)),
    )


def _as_game(case: Mapping[str, Any]) -> ClockPlayGameInputs:
    home = case.get("home")
    away = case.get("away")
    if not isinstance(home, Mapping) or not isinstance(away, Mapping):
        raise SystemExit(f"Case {case.get('case_id')!r} needs home and away objects")
    case_id = str(case.get("case_id") or "").strip()
    if not case_id:
        raise SystemExit("Every input case needs a non-empty case_id")
    return ClockPlayGameInputs(
        game_id=case_id,
        home_team=str(case.get("home_team") or "SYN_HOME"),
        away_team=str(case.get("away_team") or "SYN_AWAY"),
        home=_as_team(home),
        away=_as_team(away),
        regular_season=True,
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _merge_counts(target: Counter[str], row: Mapping[str, Any]) -> None:
    for key, value in row.items():
        target[str(key)] += int(value)


def _quantile(sorted_values: list[int], probability: float) -> int:
    if not sorted_values:
        return 0
    index = int(round((len(sorted_values) - 1) * probability))
    return int(sorted_values[index])


def _case_summary(
    *,
    case: Mapping[str, Any],
    config: ClockPlayConfig,
    seeds: list[int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    game = _as_game(case)
    home_scores: list[int] = []
    away_scores: list[int] = []
    play_counts: list[int] = []
    event_counts: Counter[str] = Counter()
    transition_counts: Counter[str] = Counter()
    result_reasons: Counter[str] = Counter()
    all_invariants_ok = True
    trace_sample: dict[str, Any] = {}

    for index, seed in enumerate(seeds):
        result = simulate_clock_play_game(
            game,
            seed=seed,
            config=config,
            collect_events=index == 0,
        )
        home_scores.append(int(result["home_score"]))
        away_scores.append(int(result["away_score"]))
        play_counts.append(int(result["play_count"]))
        _merge_counts(event_counts, result["event_counts"])
        _merge_counts(transition_counts, result["transition_counts"])
        result_reasons[str(result["result_reason"])] += 1
        all_invariants_ok = all_invariants_ok and bool(result["state_invariants"]["ok"])
        if index == 0:
            trace_sample = result

    totals = sorted(home + away for home, away in zip(home_scores, away_scores))
    margins = sorted(home - away for home, away in zip(home_scores, away_scores))
    summary = {
        "case_id": game.game_id,
        "replicates": len(seeds),
        "home_score_mean": round(_mean([float(v) for v in home_scores]), 6),
        "away_score_mean": round(_mean([float(v) for v in away_scores]), 6),
        "total_mean": round(_mean([float(v) for v in totals]), 6),
        "margin_mean": round(_mean([float(v) for v in margins]), 6),
        "total_p10": _quantile(totals, 0.10),
        "total_p50": _quantile(totals, 0.50),
        "total_p90": _quantile(totals, 0.90),
        "play_count_mean": round(_mean([float(v) for v in play_counts]), 6),
        "event_counts": dict(sorted(event_counts.items())),
        "transition_counts": dict(sorted(transition_counts.items())),
        "result_reasons": dict(sorted(result_reasons.items())),
        "state_invariants_ok": all_invariants_ok,
        "inputs": {
            "home_team": game.home_team,
            "away_team": game.away_team,
            "home": {
                "offense_rating": game.home.offense_rating,
                "defense_rating": game.home.defense_rating,
                "pace_factor": game.home.pace_factor,
            },
            "away": {
                "offense_rating": game.away.offense_rating,
                "defense_rating": game.away.defense_rating,
                "pace_factor": game.away.pace_factor,
            },
        },
    }
    return summary, trace_sample


def _checksum_manifest(output_dir: Path) -> dict[str, str]:
    excluded = {"artifact-checksums.json", "checksums.sha256"}
    return {
        path.relative_to(output_dir).as_posix(): _sha256_file(path)
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name not in excluded
    }


def _write_checksum_files(output_dir: Path) -> dict[str, str]:
    manifest = _checksum_manifest(output_dir)
    _write_json(output_dir / "artifact-checksums.json", manifest)
    final_manifest = _checksum_manifest(output_dir)
    lines = [
        f"{digest}  {relative_path}"
        for relative_path, digest in sorted(final_manifest.items())
    ]
    (output_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return final_manifest


def run(
    *,
    config_path: Path,
    inputs_path: Path,
    output_dir: Path,
    source_sha: str,
) -> dict[str, Any]:
    config_payload = _load_json_object(config_path)
    inputs_payload = _load_json_object(inputs_path)
    artifact_id = str(config_payload.get("artifact_id") or ARTIFACT_ID)
    engine_config, clock_play_priors_receipt = _load_clock_play_priors(
        config_payload
    )
    config = ClockPlayConfig.from_mapping(engine_config)
    run_spec = config_payload.get("freeze_run")
    if not isinstance(run_spec, Mapping):
        raise SystemExit("Config needs a freeze_run object")
    replicates = int(run_spec.get("replicates_per_case", 0))
    if replicates < 1:
        raise SystemExit("freeze_run.replicates_per_case must be positive")
    cases = inputs_payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SystemExit("Inputs needs a non-empty cases list")
    if inputs_payload.get("held_out_data") is not False:
        raise SystemExit("Inputs must explicitly assert held_out_data=false")
    if inputs_payload.get("market_data") is not False:
        raise SystemExit("Inputs must explicitly assert market_data=false")

    output_dir.mkdir(parents=True, exist_ok=True)
    root_seeds = run_spec.get("root_seeds")
    if not isinstance(root_seeds, Mapping):
        raise SystemExit("freeze_run.root_seeds must be an object keyed by case_id")

    case_summaries: list[dict[str, Any]] = []
    trace_samples: dict[str, Any] = {}
    seed_manifest_cases: list[dict[str, Any]] = []
    aggregate_events: Counter[str] = Counter()
    aggregate_transitions: Counter[str] = Counter()
    aggregate_invariants_ok = True
    games_simulated = 0

    for raw_case in cases:
        if not isinstance(raw_case, Mapping):
            raise SystemExit("Every case must be an object")
        case_id = str(raw_case.get("case_id") or "")
        if case_id not in root_seeds:
            raise SystemExit(f"Missing root seed for case {case_id!r}")
        root_seed = int(root_seeds[case_id])
        seeds = [
            derive_replicate_seed(root_seed, case_id, replicate_index)
            for replicate_index in range(replicates)
        ]
        summary, trace = _case_summary(case=raw_case, config=config, seeds=seeds)
        case_summaries.append(summary)
        trace_samples[case_id] = trace
        seed_manifest_cases.append(
            {
                "case_id": case_id,
                "root_seed": root_seed,
                "replicate_seeds": seeds,
            }
        )
        _merge_counts(aggregate_events, summary["event_counts"])
        _merge_counts(aggregate_transitions, summary["transition_counts"])
        aggregate_invariants_ok = aggregate_invariants_ok and bool(summary["state_invariants_ok"])
        games_simulated += replicates

    probe_case = _as_game(cases[0])
    probe_seed = derive_replicate_seed(
        int(root_seeds[str(cases[0]["case_id"])]), str(cases[0]["case_id"]), replicates
    )
    overtime_probe = simulate_clock_play_overtime_probe(
        probe_case, seed=probe_seed, config=config, collect_events=True
    )
    structural_probes = {
        "overtime_probe": overtime_probe,
        "checks": {
            "iterative_play_progression": all(row["play_count_mean"] > 0 for row in case_summaries),
            "down_distance_state": aggregate_events["scrimmage_play"] > 0,
            "possession_state": aggregate_events["possession_start"] > games_simulated,
            "clock_decrement_between_plays": all(
                any(
                    event.get("event_type") == "scrimmage_play"
                    and float(event.get("clock_elapsed_seconds") or 0) > 0
                    for event in trace["events"]
                )
                for trace in trace_samples.values()
            ),
            "touchdown_to_try": aggregate_transitions["touchdown_to_try"]
            == aggregate_events["touchdown"],
            "post_score_kickoff": aggregate_transitions["field_goal_to_kickoff"] > 0
            and aggregate_transitions["try_to_kickoff"] > 0,
            "timeout_endgame_logic": aggregate_events["timeout"] > 0,
            "overtime_path": aggregate_events["overtime_start"] > 0
            or overtime_probe["event_counts"].get("overtime_start", 0) == 1,
        },
    }

    metric_packet = {
        "artifact_id": artifact_id,
        "model_version": config.model_version,
        "experiment_scope": "isolated_train_only_structural_baseline",
        "games_simulated": games_simulated,
        "case_count": len(case_summaries),
        "held_out_data": False,
        "market_data": False,
        "calibration": "none",
        "manual_key_number_targeting": False,
        "state_invariants_ok": aggregate_invariants_ok,
        "aggregate_event_counts": dict(sorted(aggregate_events.items())),
        "aggregate_transition_counts": dict(sorted(aggregate_transitions.items())),
        "structural_checks": structural_probes["checks"],
        "metrics_not_evaluated": [
            "spread_mae",
            "total_mae",
            "key_3",
            "key_7",
        ],
        "case_summaries": case_summaries,
    }
    seed_manifest = {
        "artifact_id": artifact_id,
        "derivation": "sha256(root_seed|case_id|replicate_index) first 8 bytes unsigned big-endian",
        "cases": seed_manifest_cases,
        "overtime_probe_seed": probe_seed,
    }
    command_receipt = {
        "artifact_id": artifact_id,
        "runner_version": RUNNER_VERSION,
        "source_sha": source_sha,
        "canonical_command": (
            "PYTHONPATH=services/model-service python3 "
            "scripts/nfl/run_clock_play_baseline_v1.py "
            f"--config {config_path.as_posix()} "
            f"--inputs {inputs_path.as_posix()} "
            "--output-dir <ARTIFACT_OUTPUT_DIR> "
            f"--source-sha {source_sha}"
        ),
        "pythonpath": "services/model-service",
        "network_access": False,
        "output_directory_contract": (
            "Caller-selected artifact destination; excluded from canonical payload "
            "so an independent replay is byte-identical."
        ),
    }
    source_hashes = {
        relative_path: _sha256_file(ROOT / relative_path)
        for relative_path in SOURCE_FILES
    }

    _write_json(output_dir / "seed-manifest.json", seed_manifest)
    _write_json(output_dir / "case-summaries.json", case_summaries)
    _write_json(output_dir / "trace-samples.json", trace_samples)
    _write_json(output_dir / "structural-probes.json", structural_probes)
    _write_json(output_dir / "metric-packet.json", metric_packet)
    _write_json(output_dir / "command-receipt.json", command_receipt)
    receipt = {
        "artifact_id": artifact_id,
        "model_version": config.model_version,
        "source_sha": source_sha,
        "runner_version": RUNNER_VERSION,
        "config": {
            "path": config_path.as_posix(),
            "sha256": _sha256_file(config_path),
            "effective_engine_config": config_payload["engine_config"],
        },
        "data": {
            "path": inputs_path.as_posix(),
            "sha256": _sha256_file(inputs_path),
            "held_out_data": False,
            "market_data": False,
        },
        "source_files_sha256": source_hashes,
        "seed_manifest_sha256": _sha256_file(output_dir / "seed-manifest.json"),
        "metric_packet_sha256": _sha256_file(output_dir / "metric-packet.json"),
        "command_receipt_sha256": _sha256_file(output_dir / "command-receipt.json"),
        "replay_contract": {
            "deterministic": True,
            "required_inputs": [
                "source_sha",
                "source_files_sha256",
                "config_sha256",
                "data_sha256",
                "seed_manifest",
                "canonical_command",
            ],
            "timestamp_in_artifacts": False,
        },
    }
    for label, prior_receipt in clock_play_priors_receipt.items():
        receipt[f"{label}_priors"] = prior_receipt
    _write_json(output_dir / "receipt.json", receipt)
    checksums = _write_checksum_files(output_dir)
    return {
        "artifact_id": artifact_id,
        "output_dir": output_dir.as_posix(),
        "source_sha": source_sha,
        "games_simulated": games_simulated,
        "state_invariants_ok": aggregate_invariants_ok,
        "structural_checks": structural_probes["checks"],
        "checksums": checksums,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze Clock-Play Baseline v1")
    parser.add_argument("--config", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    result = run(
        config_path=Path(args.config),
        inputs_path=Path(args.inputs),
        output_dir=Path(args.output_dir),
        source_sha=str(args.source_sha),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
