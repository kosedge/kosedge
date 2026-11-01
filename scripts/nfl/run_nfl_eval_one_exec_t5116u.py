#!/usr/bin/env python3
"""t5116u ONE EXEC — EVAL fac21ebe only. Claim then join. No second look."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.evaluator import (  # noqa: E402
    freeze_eligible_cohorts,
    freeze_forecast_cohort,
    run_eval_score,
    select_market_quotes,
)
from src.services.nfl_t5107u.inputs import QUOTE_MANIFEST_SHA256  # noqa: E402
from src.services.nfl_t5107u.manifest import DESIGN_SEAL_SHA256, design_body_sha256  # noqa: E402
from src.services.nfl_t5107u.metric_cohorts import (  # noqa: E402
    DECLARED_REG_UNIVERSE,
    WILDCARD_2020_W18,
    declared_reg_hold_table,
    pin_metric_cohorts,
)
from src.services.nfl_t5107u.one_run import (  # noqa: E402
    DEFAULT_PATH,
    bind_one_run,
    fail_one_run,
    hash_code_tree,
    sha256_file,
)
from src.services.nfl_odds_reader import iter_jsonl_quotes, iter_open_close_csv_quotes  # noqa: E402

ALEX_GO = "c122b1088a404db550ae570ccf0c2099e084d900233bd5d317b84990288eef3b"
EVAL_SHA = "fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0"
DEV_REG_SHA = "92b915850b6094c4fa73923eeeb86763b91368007b8d5977d97e6770f40e6c49"
WC_SHA = "f81d381e0553a82a87a86b5e1a980cc2792be2e12f73203e48aa1435199d0722"
METRIC_FILE_SHA = "c301a09189f332a2017fd082408962dbb5a97a57c17c362b4fa012f382090923"
FREEZE_FILE_SHA = "9e704b980b6ce33acc883725823c39766ea19f8a86a7a781ac2a02d95344a732"
FORECAST_SHA = "f326a39aeaf4bc43b139f2441fab3c07c2d4e6d5bb363ecea421010d5983a458"
FULL_COHORT_SHA = "af129383acdad81316897cea6a1d5b48ca51647b3fc51092b55b29ca284908bc"
GAMES_SHA = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OUTCOMES_SHA = "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081"
HEAD = "3013f111a7daa0b433e8adf92f18381f0b958e21"
IMPL = "a9668540c94e76fcf6f542097c0bf350c213b2a4"

GAMES = Path("/tmp/t5111u-recon-43b5a622/pins/games_4fe1cdd7.csv")
OUTCOMES = Path("/tmp/t5111u-recon-43b5a622/pins/outcomes_2013_2022_score_only.csv")
SCORES_2023 = ROOT / "data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2023.csv"
FREEZE = ROOT / "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json"
METRIC = ROOT / "data/ops/nfl-forecast-builder-t5107u/METRIC_COHORTS_t5115u.json"
QUOTE_MANIFEST = ROOT / "data/ops/nfl-odds-reader-2020-2023-join-manifest.json"
FROZEN_MANIFEST = ROOT / "data/ops/nfl-forecast-builder-t5107u/FROZEN_MANIFEST.json"
CODE_ROOT = ROOT / "services/model-service/src/services/nfl_t5107u"
ONE_RUN = ROOT / DEFAULT_PATH
OUT_DIR = ROOT / "data/ops/nfl-forecast-builder-t5107u"


def _die(msg: str) -> None:
    print(json.dumps({"status": "PIN_MISMATCH_OR_REFUSE", "error": msg}), flush=True)
    raise SystemExit(2)


def verify_pins() -> dict:
    live = {
        "metric_file": sha256_file(METRIC),
        "freeze_file": sha256_file(FREEZE),
        "quote": sha256_file(QUOTE_MANIFEST),
        "games": sha256_file(GAMES),
        "outcomes": sha256_file(OUTCOMES),
        "design": design_body_sha256(json.loads(FROZEN_MANIFEST.read_text())),
    }
    expect = {
        "metric_file": METRIC_FILE_SHA,
        "freeze_file": FREEZE_FILE_SHA,
        "quote": QUOTE_MANIFEST_SHA256,
        "games": GAMES_SHA,
        "outcomes": OUTCOMES_SHA,
        "design": DESIGN_SEAL_SHA256,
    }
    bad = {k: (live[k], expect[k]) for k in expect if live[k] != expect[k]}
    if bad:
        _die(f"pin mismatch {bad}")
    freeze = json.loads(FREEZE.read_text())
    if freeze["forecast_sha256"] != FORECAST_SHA or freeze["cohort_sha256"] != FULL_COHORT_SHA:
        _die("freeze forecast/cohort pin mismatch")
    pins = pin_metric_cohorts(freeze["forecasts"])
    if pins["eval"]["cohort_sha256"] != EVAL_SHA or pins["eval"]["n"] != 449:
        _die("EVAL pin mismatch")
    if pins["dev_reg"]["cohort_sha256"] != DEV_REG_SHA or pins["dev_reg"]["n"] != 437:
        _die("DEV REG pin mismatch")
    if pins["non_reg_wildcard"]["cohort_sha256"] != WC_SHA or pins["non_reg_wildcard"]["n"] != 6:
        _die("WILDCARD pin mismatch")
    if ONE_RUN.is_file():
        _die("ONE_RUN.json already exists — refuse second look")
    return {"freeze": freeze, "pins": pins, "live": live}


def eval_payload(freeze: dict) -> dict:
    rows = [r for r in freeze["forecasts"] if int(r["season"]) in (2022, 2023)]
    return {
        "schema_version": "nfl-t5107u-forecast-v1",
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
        "fit_policy": "TRANSFER_FROZEN_DEV_2013_2016",
        "if_arm": {
            "archived": 0,
            "reconstructed": sum(1 for r in rows if r.get("if_status") == "reconstructed"),
            "blocked": sum(1 for r in rows if r.get("if_status") == "blocked"),
            "total": len(rows),
        },
        "forecasts": rows,
        "eval": None,
        "scoring": None,
        "look": None,
    }


def load_eval_games(eval_ids: set[str]) -> list[dict]:
    games = []
    with GAMES.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            gid = raw["game_id"]
            if gid not in eval_ids:
                continue
            games.append(
                {
                    "game_id": gid,
                    "season": int(raw["season"]),
                    "week": int(raw["week"]),
                    "home": raw["home"],
                    "away": raw["away"],
                    "kickoff": raw["kickoff_utc"],
                    "kickoff_utc": raw["kickoff_utc"],
                    "game_date": raw.get("nflverse_gameday") or "",
                }
            )
    if len(games) != len(eval_ids):
        _die(f"games identity incomplete for EVAL {len(games)} != {len(eval_ids)}")
    return games


def load_quotes() -> list[dict]:
    quotes = list(iter_jsonl_quotes(seasons=(2022, 2023)))
    quotes.extend(list(iter_open_close_csv_quotes(seasons=(2022, 2023))))
    return quotes


def load_outcomes(eval_ids: set[str], games: list[dict]) -> dict[str, dict]:
    by_key = {(g["season"], g["week"], g["home"], g["away"]): g["game_id"] for g in games}
    out: dict[str, dict] = {}
    with OUTCOMES.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            season = int(raw["season"])
            if season != 2022:
                continue
            gid = by_key.get((season, int(raw["week"]), raw["home"], raw["away"]))
            if gid and gid in eval_ids:
                out[gid] = {
                    "game_id": gid,
                    "season": season,
                    "week": int(raw["week"]),
                    "home_score": raw["home_score"],
                    "away_score": raw["away_score"],
                }
    with SCORES_2023.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            gid = raw["game_id"]
            if gid in eval_ids and str(raw.get("season_type") or "REG").upper() == "REG":
                out[gid] = {
                    "game_id": gid,
                    "season": int(raw["season"]),
                    "week": int(raw["week"]),
                    "home_score": raw["home_score"],
                    "away_score": raw["away_score"],
                }
    return out


def scoring_hold(quote_eligible_by_season: dict[int, int]) -> dict:
    recon_excl = {2020: 16, 2021: 16, 2022: 18, 2023: 16}
    recon_partial = {2020: 30, 2021: 29, 2022: 32, 2023: 28}
    # EVAL seasons: declared minus quote-eligible complete (W1/partial/T5 already out).
    # Quote-eligible n is among the 449 complete; remaining declared exclusion =
    # declared - quote_eligible.
    excl = dict(recon_excl)
    partial = dict(recon_partial)
    for season in (2022, 2023):
        declared = DECLARED_REG_UNIVERSE[season]
        qn = int(quote_eligible_by_season.get(season, 0))
        excluded_total = declared - qn
        # split back into helper fields: keep recon excl, put the rest in partial bucket
        partial[season] = max(0, excluded_total - excl[season])
    return declared_reg_hold_table(recon_excluded_n=excl, recon_partial_n=partial)


def main() -> int:
    if ONE_RUN.is_file():
        _die("ONE_RUN.json exists — refuse second look")
    verified = verify_pins()
    freeze = verified["freeze"]
    pins = verified["pins"]
    payload = eval_payload(freeze)
    frozen = freeze_forecast_cohort(payload)
    if frozen.cohort_sha256 != EVAL_SHA:
        _die(f"EVAL FrozenCohort {frozen.cohort_sha256} != {EVAL_SHA}")
    eval_ids = set(pins["eval"]["game_ids"])
    games = load_eval_games(eval_ids)
    print(json.dumps({"phase": "quotes", "eval_n": len(eval_ids)}), flush=True)
    quotes = load_quotes()
    print(json.dumps({"phase": "quotes_loaded", "n": len(quotes)}), flush=True)
    market = select_market_quotes(quotes, games, forecasts=payload["forecasts"])
    points = list(market.get("points") or [])
    eligible_margin = [p for p in points if p.get("market_margin") is not None]
    q_by_season = Counter(int(p["season"]) for p in eligible_margin)
    hold = scoring_hold(dict(q_by_season))
    eligible = freeze_eligible_cohorts(
        payload,
        market,
        quote_manifest_sha256=QUOTE_MANIFEST_SHA256,
        g5_hold=hold,
    )
    print(
        json.dumps(
            {
                "phase": "eligible",
                "margin_n": eligible["margin_cohort"]["n"],
                "hold": hold["any_season_hold"],
                "q_by_season": dict(q_by_season),
            }
        ),
        flush=True,
    )

    spec_sha = sha256_file(FROZEN_MANIFEST)
    code_sha = hash_code_tree(CODE_ROOT)
    input_sha = sha256_file(FREEZE)
    rec = bind_one_run(
        effective_spec_sha256=spec_sha,
        code_sha256=code_sha,
        input_sha256=input_sha,
        forecast_sha256=frozen.forecast_sha256,
        cohort_sha256=frozen.cohort_sha256,
        alex_go_id=ALEX_GO,
        path=ONE_RUN,
    )
    print(json.dumps({"phase": "bound", "bind_id": rec["bind_id"]}), flush=True)

    outcomes = load_outcomes(eval_ids, games)
    try:
        scored = run_eval_score(
            frozen,
            outcomes,
            exec_bind=rec["bind_id"],
            alex_go_id=ALEX_GO,
            one_run_path=ONE_RUN,
            eligible_cohorts=eligible,
            market_points=points,
            live_effective_spec_sha256=spec_sha,
            live_code_sha256=code_sha,
            live_input_sha256=input_sha,
        )
    except Exception as exc:
        try:
            fail_one_run(ONE_RUN, rec["bind_id"], str(exc))
        except Exception:
            pass
        result = {
            "status": "FAILED",
            "error": str(exc),
            "bind_id": rec["bind_id"],
            "eval_n": 449,
            "quote_eligible_n": eligible["margin_cohort"]["n"],
            "dev_reg_n": 437,
            "wildcard_n": 6,
            "partials_119": 119,
            "g5_hold": hold,
            "second_look": False,
            "failed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (OUT_DIR / "ONE_EXEC_RESULT_t5116u.json").write_text(
            json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
        )
        print(json.dumps({"phase": "failed", "error": str(exc)}), flush=True)
        return 1

    by_season = Counter(int(r["season"]) for r in scored.get("games") or [])
    package = {
        "status": "CONSUMED",
        "bind_id": rec["bind_id"],
        "alex_go_id": ALEX_GO,
        "eval_n": 449,
        "eval_cohort_sha256": EVAL_SHA,
        "quote_eligible_n": eligible["margin_cohort"]["n"],
        "quote_eligible_by_season": dict(q_by_season),
        "scored_n": scored.get("n"),
        "scored_by_season": dict(by_season),
        "dev_reg_n": 437,
        "dev_reg_cohort_sha256": DEV_REG_SHA,
        "wildcard_n": 6,
        "wildcard_ids": list(WILDCARD_2020_W18),
        "partials_119": 119,
        "partials_by_season": {2020: 30, 2021: 29, 2022: 32, 2023: 28},
        "g5_hold": hold,
        "metrics": {
            "mae_challenger": scored.get("mae_challenger"),
            "mae_if": scored.get("mae_if"),
            "delta_mae_vs_if": scored.get("delta_mae_vs_if"),
            "mean_signed_diff_vs_if": scored.get("mean_signed_diff_vs_if"),
            "mae_market": scored.get("mae_market"),
            "delta_mae_vs_market": scored.get("delta_mae_vs_market"),
            "mean_signed_diff_vs_market": scored.get("mean_signed_diff_vs_market"),
            "bootstrap_game": scored.get("bootstrap_game"),
            "bootstrap_season_week": scored.get("bootstrap_season_week"),
            "bootstrap_game_vs_market": scored.get("bootstrap_game_vs_market"),
            "reporting_class": scored.get("reporting_class"),
        },
        "eval_forecast_sha256": frozen.forecast_sha256,
        "source_freeze_forecast_sha256": FORECAST_SHA,
        "source_full_cohort_sha256": FULL_COHORT_SHA,
        "one_run_status": scored.get("one_run_status"),
        "scoring": scored.get("scoring"),
        "label": "RESEARCH_CONSUMED_RETRO",
        "cert_candidate": 0,
        "second_look": False,
        "scored_892_as_eval": False,
        "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    dest = OUT_DIR / "ONE_EXEC_RESULT_t5116u.json"
    dest.write_text(json.dumps(package, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"phase": "consumed", "n": scored.get("n"), "path": str(dest)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
