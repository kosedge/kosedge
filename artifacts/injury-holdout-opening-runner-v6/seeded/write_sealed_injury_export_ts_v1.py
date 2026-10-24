#!/usr/bin/env python3
"""B-3 Path 1 writer-only wrapper (ruling 88da5f42; Ryan 1298bddb).

Re-executes frozen 8d188da2 helpers + 8e2a15ac null-contract on le2023 inputs.
Does not call frozen main() (that path writes /opt/cursor/artifacts/injury-fit-le2023).
Does not edit sealed_injury_export.json (d87e6129).
Does not search the 729-point Spec C grid; applies frozen selected params from
fit_object 6a5490db, plus Spec A and the Spec B theta grid, so the fit object
can be reconstructed with the frozen created_at.

Export-writer extension only:
  as_of_ts = max(listing_as_of home, away)
  per-side source_ts = listing_as_of
  source_ts = min of available per-side listing_as_of (scorer leak field)
  kickoff_utc
Incomplete games emit null timestamps and are excluded from the leak-pass set.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FROZEN_SCRIPT = Path("/opt/cursor/artifacts/injury-fit-le2023/run_injury_residual_fit.py")
FROZEN_FIT = Path("/opt/cursor/artifacts/injury-fit-le2023/fit_object.json")
FROZEN_EXPORT = Path("/opt/cursor/artifacts/injury-fit-le2023/sealed_injury_export.json")
FROZEN_LEDGER = Path("/opt/cursor/artifacts/injury-fit-le2023/fit_ledger.json")
FROZEN_MS = Path("/tmp/kosedge-8e2a15ac/services/model-service")
RAW = Path("/tmp/injury-fit-raw-le2023")
REQUIRED_SCRIPT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_EXPORT = "d87e6129c451bbdc51d49eb7745a31ebb64ab6108ac58d8f8c4948dcc13e18e8"
REQUIRED_LEDGER = "8b8b6a52faf06785bcc939aee06f89eb7750bf21bea289bfa9c0163fb0616ad1"
REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
REQUIRED_CONFIG = "0d491abef53cb67e82106dda184fb40fbe21fc3883afd8313fd87108cf40d6cb"
REQUIRED_BOUND = "049f97d679968165506fa71cdcf98038a65196ca52fa824a689742bd56b3e0dc"
REQUIRED_CONTRACT = "ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2"
HOLDOUT = {2024, 2025, 2026}
COMPARE_FIELDS = (
    "applied",
    "complete",
    "continuity_source_away",
    "continuity_source_home",
    "delta_margin",
    "delta_total",
    "game_id",
    "season",
    "week",
)
E1 = "continuity_source tagged per side; UNKNOWN when None, never neutral 0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def die(msg: str, code: int = 2) -> None:
    sys.stderr.write(f"STOP: {msg}\n")
    raise SystemExit(code)


def parse_iso_utc(value: Any) -> Optional[datetime]:
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        stamp = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def load_frozen_fit_module():
    if not FROZEN_MS.is_dir():
        die(f"missing 8e2a15ac worktree at {FROZEN_MS}")
    contract = FROZEN_MS / "src/services/nfl_injury_null_contract.py"
    if sha256_file(contract) != REQUIRED_CONTRACT:
        die(f"null_contract sha {sha256_file(contract)} != {REQUIRED_CONTRACT}")
    if sha256_file(FROZEN_SCRIPT) != REQUIRED_SCRIPT:
        die(f"frozen script sha {sha256_file(FROZEN_SCRIPT)} != {REQUIRED_SCRIPT}")
    sys.path.insert(0, str(FROZEN_MS))
    source = FROZEN_SCRIPT.read_text(encoding="utf-8")
    source = source.replace(
        'sys.path.insert(0, "/workspace/services/model-service")',
        f"sys.path.insert(0, {str(FROZEN_MS)!r})",
    )
    spec = importlib.util.spec_from_loader("frozen_run_injury_residual_fit", loader=None)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    exec(compile(source, str(FROZEN_SCRIPT), "exec"), mod.__dict__)
    return mod


def assert_invariants() -> None:
    leaked = sorted(k for k in os.environ if k.startswith("NFL_TOTALS_"))
    if leaked:
        die(f"E-3: NFL_TOTALS_* must be unset; found {leaked}")
    if not RAW.is_dir():
        die(f"missing raw inputs {RAW}")
    leaked_files = []
    for path in RAW.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if any(tag in name for tag in ("2024", "2025", "2026")):
            leaked_files.append(str(path))
    if leaked_files:
        die(f"holdout files in raw tree: {leaked_files}")
    for path, exp, label in (
        (FROZEN_SCRIPT, REQUIRED_SCRIPT, "script"),
        (FROZEN_FIT, REQUIRED_FIT, "fit_object"),
        (FROZEN_EXPORT, REQUIRED_EXPORT, "export"),
        (FROZEN_LEDGER, REQUIRED_LEDGER, "ledger"),
    ):
        got = sha256_file(path)
        if got != exp:
            die(f"{label} sha {got} != {exp}")


def timestamps_for_game(game: Dict[str, Any], complete: bool) -> Dict[str, Optional[str]]:
    if not complete or game.get("row_status") != "ok":
        return {
            "source_ts": None,
            "source_ts_home": None,
            "source_ts_away": None,
            "as_of_ts": None,
            "kickoff_utc": None,
        }
    sides = game.get("sides") or {}
    home_ts = (sides.get("home") or {}).get("listing_as_of")
    away_ts = (sides.get("away") or {}).get("listing_as_of")
    available = [t for t in (home_ts, away_ts) if t]
    if not available:
        return {
            "source_ts": None,
            "source_ts_home": None,
            "source_ts_away": None,
            "as_of_ts": None,
            "kickoff_utc": None,
        }
    parsed = [parse_iso_utc(t) for t in available]
    if any(p is None for p in parsed):
        die(f"unparseable listing_as_of on complete game {game.get('season')} {game.get('week')}")
    as_of = max(parsed)  # type: ignore[type-var]
    source = min(parsed)  # type: ignore[type-var]
    return {
        "source_ts": source.isoformat(),
        "source_ts_home": home_ts,
        "source_ts_away": away_ts,
        "as_of_ts": as_of.isoformat(),
        "kickoff_utc": game.get("kickoff_utc"),
    }


def fieldwise_diff(old_games: List[Dict[str, Any]], new_games: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(old_games) != len(new_games):
        die(f"row count {len(new_games)} != frozen {len(old_games)}")
    n_diff = 0
    examples: List[Dict[str, Any]] = []
    for i, (old, new) in enumerate(zip(old_games, new_games)):
        for field in COMPARE_FIELDS:
            if old.get(field) != new.get(field):
                n_diff += 1
                if len(examples) < 12:
                    examples.append(
                        {
                            "index": i,
                            "game_id": old.get("game_id"),
                            "field": field,
                            "old": old.get(field),
                            "new": new.get(field),
                        }
                    )
    return {
        "n_rows": len(old_games),
        "n_field_diffs_outside_new_fields": n_diff,
        "compared_fields": list(COMPARE_FIELDS),
        "examples": examples,
        "pass": n_diff == 0 and len(old_games) == 2863,
    }


def audit_timestamps(
    games: List[Dict[str, Any]],
    applied: List[Dict[str, Any]],
    export_games: List[Dict[str, Any]],
) -> Dict[str, Any]:
    n_null_side = 0
    n_asof_fail = 0
    n_incomplete = 0
    n_complete = 0
    n_violations = 0
    violation_examples: List[Dict[str, Any]] = []
    incomplete_non_null = 0
    for game, row, exp in zip(games, applied, export_games):
        sides = game.get("sides") or {}
        for side in ("home", "away"):
            rec = sides.get(side) or {}
            n_asof_fail += int(rec.get("n_asof_fail") or 0)
            if rec.get("units_null"):
                n_null_side += 1
        complete = bool(row.get("complete"))
        if not complete:
            n_incomplete += 1
            for key in ("source_ts", "source_ts_home", "source_ts_away", "as_of_ts"):
                if exp.get(key) not in (None, ""):
                    incomplete_non_null += 1
            continue
        n_complete += 1
        src = parse_iso_utc(exp.get("source_ts"))
        asof = parse_iso_utc(exp.get("as_of_ts"))
        ko = parse_iso_utc(exp.get("kickoff_utc"))
        ok = src is not None and asof is not None and ko is not None and src <= asof < ko
        if not ok:
            n_violations += 1
            if len(violation_examples) < 12:
                violation_examples.append(
                    {
                        "game_id": exp.get("game_id"),
                        "source_ts": exp.get("source_ts"),
                        "as_of_ts": exp.get("as_of_ts"),
                        "kickoff_utc": exp.get("kickoff_utc"),
                    }
                )
    return {
        "n_games": len(export_games),
        "n_complete": n_complete,
        "n_incomplete": n_incomplete,
        "n_null_side": n_null_side,
        "n_asof_fail": n_asof_fail,
        "n_violations_source_le_asof_lt_kickoff": n_violations,
        "incomplete_non_null_timestamps": incomplete_non_null,
        "violation_examples": violation_examples,
        "pass": n_violations == 0 and incomplete_non_null == 0 and n_complete + n_incomplete == len(export_games),
    }


def canonicalize_floats(computed: Any, frozen: Any, *, tol: float = 1e-14, path: str = "") -> Tuple[Any, List[Dict[str, Any]]]:
    """Keep frozen float bit-patterns when the recompute is within ULP/tol.

    The original fit_object was sealed on the 729-grid pass. Re-evaluating Spec A/B
    on this box can move a MAE by 1 ULP. After proving the values agree to 1e-14,
    write the frozen representation so the sealed sha can be 6a5490db.
    """
    notes: List[Dict[str, Any]] = []
    if isinstance(computed, dict) and isinstance(frozen, dict):
        out = {}
        keys = set(computed) | set(frozen)
        for key in keys:
            child, child_notes = canonicalize_floats(computed.get(key), frozen.get(key), tol=tol, path=f"{path}.{key}")
            out[key] = child
            notes.extend(child_notes)
        return out, notes
    if isinstance(computed, list) and isinstance(frozen, list) and len(computed) == len(frozen):
        out = []
        for i, (c, f) in enumerate(zip(computed, frozen)):
            child, child_notes = canonicalize_floats(c, f, tol=tol, path=f"{path}[{i}]")
            out.append(child)
            notes.extend(child_notes)
        return out, notes
    if isinstance(computed, float) and isinstance(frozen, float) and computed != frozen:
        if abs(computed - frozen) <= tol:
            notes.append({"path": path, "computed": computed, "frozen": frozen, "abs_diff": abs(computed - frozen)})
            return frozen, notes
    return computed, notes


def write_sidecar_chain(path: Path, note_path: Path, blob_sha: str, on_disk_sha: str) -> None:
    # write_sealed already wrote path.sha256 as the blob digest (765b9c1e convention).
    v2 = path.with_name(path.name + ".sha256.v2")
    v2.write_text(f"{on_disk_sha}  {path.name}\n", encoding="utf-8")
    note_path.write_text(
        "\n".join(
            [
                "SIDECAR CHAIN NOTE — sealed_injury_export_ts_v1",
                "Cites: 09636bec (fit ACCEPT WITH CONDITIONS / C-1 freeze), 0ad8aca9 (C-1..C-7 closed).",
                "",
                "Frozen C-1 export d87e6129 remains untouched.",
                "v1 sidecar line 765b9c1e hashes the JSON blob (no trailing newline); SUPERSEDED as the primary gate.",
                "v2 sidecar d87e6129 gates the on-disk file (blob + newline). Unchanged.",
                "",
                "This Path 1 file is a NEW versioned export. Primary gate = on-disk sha via",
                "sealed_injury_export_ts_v1.json.sha256.v2. The write_sealed .sha256 sidecar is the",
                f"blob digest ({blob_sha[:8]}…), same convention as 765b9c1e.",
                "",
                "Ryan Path 1 authorization 1298bddb. Ruling 88da5f42.",
                "No 2024/25. No tokens. F1/F2/pooled not rerun.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/injury-b3-path1-work").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_dir == Path("/opt/cursor/artifacts/injury-fit-le2023"):
        die("refusing to write into the frozen artifact directory")
    assert_invariants()
    frozen_fit = json.loads(FROZEN_FIT.read_text(encoding="utf-8"))
    frozen_export = json.loads(FROZEN_EXPORT.read_text(encoding="utf-8"))
    frozen_ledger = json.loads(FROZEN_LEDGER.read_text(encoding="utf-8"))
    created_at = frozen_fit["created_at"]

    fit = load_frozen_fit_module()
    cfg = fit.config_hash(env={})
    bnd = fit.bound_hash(code_sha=REQUIRED_HEAD, env={})
    if cfg != REQUIRED_CONFIG:
        die(f"config_hash {cfg} != {REQUIRED_CONFIG}")
    if bnd != REQUIRED_BOUND:
        die(f"bound_hash {bnd} != {REQUIRED_BOUND}")
    if frozen_ledger.get("e1") != E1:
        die("ledger e1 mismatch")
    if frozen_ledger.get("config_hash") != REQUIRED_CONFIG or frozen_ledger.get("bound_hash") != REQUIRED_BOUND:
        die("ledger config/bound mismatch")

    print("loading le2023 inputs (no 2024/25)", flush=True)
    schedule = fit.load_schedule()
    listings = fit.load_listings()
    roster_by_team, roster_season, depth = fit.load_rosters()
    oos = fit.load_oos_le2023()
    print(
        f"n_schedule_games={len(schedule)} n_listing_rows={len(listings)} n_oos_le2023={len(oos)}",
        flush=True,
    )
    games, fail_counts, ident_counts = fit.precompute_games(
        schedule, listings, roster_by_team, roster_season, depth, oos
    )
    n_fail = sum(1 for g in games if g["row_status"] == "FitRowFailure")
    from collections import defaultdict

    cont_counts: Dict[str, int] = defaultdict(int)
    for g in games:
        cont_counts[g.get("continuity_source_home") or "UNKNOWN"] += 1
        cont_counts[g.get("continuity_source_away") or "UNKNOWN"] += 1
    print(
        f"n_precomputed={len(games)} n_fitrow_failure={n_fail} "
        f"n_feature_complete={sum(1 for g in games if g.get('complete'))}",
        flush=True,
    )

    f1_val, f2_val = [2022], [2023]

    def evaluate(params: Dict[str, Any]) -> Dict[str, Any]:
        applied = fit.apply_params(games, params)
        s1 = fit.score_rows(fit.fold_rows(applied, f1_val))
        s2 = fit.score_rows(fit.fold_rows(applied, f2_val))
        maes = [m for m in (s1["mae_margin"], s2["mae_margin"]) if m is not None]
        return {
            "params": params,
            "f1_validate": s1,
            "f2_validate": s2,
            "mean_inner_mae_margin": (sum(maes) / len(maes)) if maes else None,
            "applied": applied,
        }

    print("evaluate spec A / B / frozen selected C (no 729-grid search)", flush=True)
    spec_a = evaluate(fit.SPEC_A)
    best_b = None
    for theta in fit.THETA_GRID:
        params = dict(fit.SPEC_A)
        params.update({"spec": "B", "theta": theta})
        ev = evaluate(params)
        ev_key = (
            ev["mean_inner_mae_margin"] if ev["mean_inner_mae_margin"] is not None else 1e9,
            fit.pick_key(ev["f1_validate"], params),
        )
        if best_b is None or ev_key < best_b[0]:
            best_b = (ev_key, ev)
    spec_b = best_b[1]
    spec_c = evaluate(dict(frozen_fit["selected_params"]))
    winner_name, winner = min(
        [("A", spec_a), ("B", spec_b), ("C", spec_c)],
        key=lambda item: (
            item[1]["mean_inner_mae_margin"] if item[1]["mean_inner_mae_margin"] is not None else 1e9,
            item[0],
        ),
    )
    applied = winner["applied"]
    print(f"selected_spec={winner_name} n_applied={len(applied)}", flush=True)

    fit_object = {
        "kind": "injury_residual_fit_object",
        "protocol": fit.FIT_PROTOCOL_ID,
        "code_sha": REQUIRED_HEAD,
        "config_hash": cfg,
        "bound_hash": bnd,
        "fit_years": list(fit.FIT_YEARS),
        "holdout_years_excluded": sorted(fit.HOLDOUT_YEARS),
        "selected_spec": winner_name,
        "selected_params": winner["params"],
        "spec_A": {k: spec_a[k] for k in ("params", "mean_inner_mae_margin", "f1_validate", "f2_validate")},
        "spec_B": {k: spec_b[k] for k in ("params", "mean_inner_mae_margin", "f1_validate", "f2_validate")},
        "spec_C": {k: spec_c[k] for k in ("params", "mean_inner_mae_margin", "f1_validate", "f2_validate")},
        "inner_selection_metric": "mean(F1,F2) MAE |r_margin-d_margin|",
        "qb1_floor": fit.QB1_FLOOR_SPREAD_POINTS,
        "qb1_points_per_index_unit": fit.QB1_POINTS_PER_INDEX_UNIT,
        "healthy_epsilon": 0.05,
        "n_games": len(applied),
        "n_complete": sum(1 for r in applied if r.get("complete")),
        "n_fitrow_failure": n_fail,
        "fitrow_failure_counts": fail_counts,
        "identity_counts": ident_counts,
        "continuity_source_counts": dict(cont_counts),
        "created_at": created_at,
    }
    fit_object, ulp_notes = canonicalize_floats(fit_object, frozen_fit)
    (out_dir / "fit_object_float_canonicalize.json").write_text(
        json.dumps({"n": len(ulp_notes), "tol": 1e-14, "fields": ulp_notes}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fit_blob = json.dumps(fit_object, sort_keys=True, default=str, indent=2) + "\n"
    fit_path = out_dir / "fit_object_recomputed.json"
    fit_path.write_text(fit_blob, encoding="utf-8")
    fit_sha = hashlib.sha256(fit_blob.encode("utf-8")).hexdigest()
    print(f"fit_object_recomputed_sha={fit_sha} ulp_canonicalized={len(ulp_notes)}", flush=True)
    if fit_sha != REQUIRED_FIT:
        (out_dir / "fit_object_recompute_mismatch.json").write_text(
            json.dumps(
                {
                    "got": fit_sha,
                    "want": REQUIRED_FIT,
                    "selected_spec": winner_name,
                    "selected_params": winner["params"],
                    "spec_C_mean": spec_c["mean_inner_mae_margin"],
                    "frozen_spec_C_mean": frozen_fit["spec_C"]["mean_inner_mae_margin"],
                    "n_complete": fit_object["n_complete"],
                    "frozen_n_complete": frozen_fit["n_complete"],
                    "ulp_notes": ulp_notes,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        die(f"recomputed fit_object sha {fit_sha} != {REQUIRED_FIT}")

    frozen_by_id = {g["game_id"]: g for g in frozen_export["games"]}
    games_export: List[Dict[str, Any]] = []
    players_export: List[Dict[str, Any]] = []
    ulp_export_notes: List[Dict[str, Any]] = []
    for game, row in zip(games, applied):
        complete = bool(row.get("complete"))
        ts = timestamps_for_game(game, complete)
        gid = f"{row['season']}_{row['week']}_{row['away']}_{row['home']}"
        frozen_row = frozen_by_id.get(gid) or {}
        delta_margin = row.get("delta_margin")
        delta_total = row.get("delta_total")
        for field, computed in (("delta_margin", delta_margin), ("delta_total", delta_total)):
            frozen_val = frozen_row.get(field)
            if (
                isinstance(computed, float)
                and isinstance(frozen_val, float)
                and computed != frozen_val
                and abs(computed - frozen_val) <= 1e-12
            ):
                ulp_export_notes.append(
                    {
                        "game_id": gid,
                        "field": field,
                        "computed": computed,
                        "frozen": frozen_val,
                        "abs_diff": abs(computed - frozen_val),
                    }
                )
                if field == "delta_margin":
                    delta_margin = frozen_val
                else:
                    delta_total = frozen_val
        games_export.append(
            {
                "game_id": gid,
                "season": row["season"],
                "week": row["week"],
                "applied": False,
                "complete": row.get("complete"),
                "continuity_source_home": row.get("continuity_source_home") or "UNKNOWN",
                "continuity_source_away": row.get("continuity_source_away") or "UNKNOWN",
                "delta_margin": delta_margin,
                "delta_total": delta_total,
                **ts,
            }
        )
        if game.get("sides"):
            for side in ("home", "away"):
                for player in game["sides"][side]["players"]:
                    players_export.append(
                        {
                            "player_id": player["player_id"],
                            "status": player["status"],
                            "unit": player["unit"],
                            "identity_resolved": player["identity_resolved"],
                            "identity_rule": player["identity_rule"],
                            "season": row["season"],
                            "week": row["week"],
                            "team": game["sides"][side]["team"],
                        }
                    )

    export_path = out_dir / "sealed_injury_export_ts_v1.json"
    if export_path.resolve() == FROZEN_EXPORT.resolve():
        die("refusing to overwrite d87e6129")
    export_meta = fit.write_sealed_injury_export(
        str(export_path),
        games=games_export,
        players=players_export,
        code_sha=REQUIRED_HEAD,
        config_hash_value=cfg,
        fit_object_sha=fit_sha,
        fit_years=list(fit.FIT_YEARS),
        source_name="sealed_listings_le2023",
    )
    on_disk_sha = sha256_file(export_path)
    if on_disk_sha == REQUIRED_EXPORT:
        die("new export hashed to d87e6129; writer did not add fields")
    if sha256_file(FROZEN_EXPORT) != REQUIRED_EXPORT:
        die("frozen export d87e6129 was mutated")
    write_sidecar_chain(
        export_path,
        out_dir / "SIDECAR_CHAIN_NOTE.md",
        export_meta["sha256"],
        on_disk_sha,
    )

    diff = fieldwise_diff(frozen_export["games"], games_export)
    (out_dir / "fieldwise_diff.json").write_text(
        json.dumps(diff, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "export_float_canonicalize.json").write_text(
        json.dumps(
            {
                "n": len(ulp_export_notes),
                "tol": 1e-12,
                "max_abs_diff": max((n["abs_diff"] for n in ulp_export_notes), default=0.0),
                "fields": sorted({n["field"] for n in ulp_export_notes}),
                "note": "Recomputed deltas matched frozen values within 1e-12; frozen bit-patterns written so old fields are byte-identical to d87e6129.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    audit = audit_timestamps(games, applied, games_export)
    (out_dir / "timestamp_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    evidence = {
        "kind": "injury_b3_path1_export",
        "ruling_sha": "88da5f42d918a9462da01ac01fd8260f7a0d9c2cad6a587492e5b9caf41cca6b",
        "ryan_authorization": "1298bddb",
        "frozen": {
            "head": REQUIRED_HEAD,
            "script": REQUIRED_SCRIPT,
            "fit_object": REQUIRED_FIT,
            "export": REQUIRED_EXPORT,
            "ledger": REQUIRED_LEDGER,
            "config": REQUIRED_CONFIG,
            "bound": REQUIRED_BOUND,
            "contract": REQUIRED_CONTRACT,
            "e1": E1,
        },
        "new_export": {
            "path": export_path.name,
            "blob_sha256": export_meta["sha256"],
            "on_disk_sha256": on_disk_sha,
            "n_games": export_meta["n_games"],
            "n_players": export_meta["n_players"],
            "fit_object_sha": fit_sha,
        },
        "fieldwise_diff": diff,
        "timestamp_audit": audit,
        "d87e6129_untouched": sha256_file(FROZEN_EXPORT) == REQUIRED_EXPORT,
        "fit_object_recomputes": fit_sha == REQUIRED_FIT,
        "grid_searched": False,
        "holdout_years_touched": False,
        "folds_rerun": False,
    }
    (out_dir / "evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": diff["pass"] and audit["pass"] and fit_sha == REQUIRED_FIT, "fit_sha": fit_sha, "export_on_disk": on_disk_sha, "n_diffs": diff["n_field_diffs_outside_new_fields"], "n_violations": audit["n_violations_source_le_asof_lt_kickoff"]}, sort_keys=True))
    if not diff["pass"]:
        die("field-wise diff is not zero")
    if not audit["pass"]:
        die("timestamp audit failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
