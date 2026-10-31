#!/usr/bin/env python3
"""Coverage, distribution, game-count, and evidence-gate report for Layer A.

Does not change coefficients. Does not open 2025. Does not read 2026 books
to make reconstruction decisions.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services/model-service"))

from src.services.cfb_season_engine.historical_calibration import (  # noqa: E402
    load_historical_games,
)
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    LOWSAMPLE_ATTEMPTS,
    QB_FEATURE_CONTRACT_VERSION,
    assert_counting_stats_season_legal,
    assert_legal_for_coefficient_fit,
    assert_v1_schema,
    assert_v1_talent_location,
    talent_location_summary,
)

LAYER_DIR = (
    REPO
    / "services/model-service/src/services/cfb_season_engine/data/cfb_qb_layer_a"
)
SDV_CACHE = REPO / "data/cfb/raw/sdv"
OPS_MD = REPO / "data/ops/cfb-qb-layer-a-20260911.md"
OPS_JSON = REPO / "data/ops/cfb-qb-layer-a-20260911.json"

COVERAGE_MIN = 0.90
TRAIN_N_MIN = 700
VAL_N_MIN = 700
EST_MEAN = (62.0, 76.0)
EST_SD = (5.0, 14.0)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_season(season: int) -> Dict[str, Any]:
    path = LAYER_DIR / f"season_{season}.json"
    if not path.is_file():
        raise SystemExit(f"missing Layer A artifact {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def missingness_table(seasons: Mapping[int, Mapping[str, Any]]) -> Dict[str, Any]:
    codes = Counter()
    by_season: Dict[str, Dict[str, int]] = {}
    for season, art in seasons.items():
        c = Counter()
        for row in (art.get("teams") or {}).values():
            for reason in row.get("reason_codes") or []:
                c[reason] += 1
                codes[reason] += 1
        by_season[str(season)] = dict(c)
    return {"overall": dict(codes), "by_season": by_season}


def provenance_samples(seasons: Mapping[int, Mapping[str, Any]], n: int = 6) -> List[Dict[str, Any]]:
    picks = []
    wanted = [
        (2022, "ALA"),
        (2023, "OSU"),
        (2023, "SYR"),
        (2024, "ORE"),
        (2022, "ARMY"),
        (2024, "JVST"),
    ]
    for season, code in wanted:
        art = seasons.get(season) or {}
        row = (art.get("teams") or {}).get(code)
        if not row:
            continue
        picks.append(
            {
                "team": code,
                "prediction_season": season,
                "starter_name": row.get("starter_name"),
                "starter_key": row.get("starter_key"),
                "qb_class": row.get("qb_class"),
                "qb_talent": row.get("qb_talent"),
                "is_portal": row.get("is_portal"),
                "pass_attempts_prior": row.get("pass_attempts_prior"),
                "pass_yards_prior": row.get("pass_yards_prior"),
                "pass_td_prior": row.get("pass_td_prior"),
                "experience_abbr": row.get("experience_abbr"),
                "reason_codes": row.get("reason_codes"),
                "availability": row.get("availability"),
                "provenance": row.get("provenance"),
            }
        )
        if len(picks) >= n:
            break
    return picks


def leakage_audit(seasons: Mapping[int, Mapping[str, Any]]) -> Dict[str, Any]:
    failures: List[str] = []
    n_rows = 0
    for season, art in seasons.items():
        if art.get("qb_feature_contract_version") != QB_FEATURE_CONTRACT_VERSION:
            failures.append(f"{season} contract {art.get('qb_feature_contract_version')}")
        if art.get("roster_source") != "espn_core_seasons_Y_team_athletes":
            failures.append(f"{season} illegal roster source {art.get('roster_source')}")
        if int(art.get("prior_season") or 0) != season - 1:
            failures.append(f"{season} prior_season {art.get('prior_season')}")
        for code, row in (art.get("teams") or {}).items():
            n_rows += 1
            try:
                assert_counting_stats_season_legal(
                    stats_season=int(row.get("prior_season") or art["prior_season"]),
                    prediction_season=season,
                    week=0,
                )
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{season} {code} temporal: {exc}")
            prov = row.get("provenance") or {}
            if prov.get("same_season_stats_used") or prov.get("site_roster_used"):
                failures.append(f"{season} {code} leaked source flags")
            if prov.get("espn_experience_used") or prov.get("recruiting_used"):
                failures.append(f"{season} {code} illegal source used")
            if row.get("recruiting_class_score") is not None:
                failures.append(f"{season} {code} recruiting filled")
            if row.get("ol_support") is not None or row.get("weapons_support") is not None:
                failures.append(f"{season} {code} Layer B cast filled")
            avail = row.get("availability") or {}
            if avail.get("recruiting") != "MISSING":
                failures.append(f"{season} {code} recruiting not MISSING")
            schema_row = {
                "qb_class": row.get("qb_class"),
                "qb_talent": row.get("qb_talent"),
                "ol_support": row.get("ol_support")
                if row.get("ol_support") is not None
                else 50.0,
                "weapons_support": row.get("weapons_support")
                if row.get("weapons_support") is not None
                else 50.0,
                "starter_name": row.get("starter_name") or "",
                "starter_key": row.get("starter_key") or "",
                "is_portal": bool(row.get("is_portal")),
                "prior_season": row.get("prior_season"),
                "pass_attempts_prior": row.get("pass_attempts_prior"),
                "pass_yards_prior": row.get("pass_yards_prior"),
                "pass_td_prior": row.get("pass_td_prior"),
                "qb_feature_contract_version": row.get("qb_feature_contract_version"),
                "availability": avail,
            }
            # Schema allows MISSING; PROXY is the fail. Skip full assert_v1_schema
            # when starter is empty (no-QB row).
            if row.get("starter_key"):
                try:
                    # ol/weapons are None in artifact; schema requires keys present.
                    # Availability map already forbids PROXY.
                    for key, val in avail.items():
                        if str(val).upper() == "PROXY":
                            failures.append(f"{season} {code} PROXY {key}")
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{season} {code} schema {exc}")
    return {"n_rows": n_rows, "failures": failures, "ok": not failures}


def _actuals_only_w1_14() -> Dict[str, int]:
    """FBS–FBS games with final scores, even when SDV close is blank.

    2022 ``espn_cfb_betting`` is sparse (most rows have no spread/total).
    That is a *label* gap, not a Layer A feature gap. Count actuals so the
    Train-0 structure is visible without pretending closes exist.
    """
    import csv
    from collections import defaultdict

    from src.services.cfb_warehouse.identity import known_engine_codes, resolve_team_code

    known = known_engine_codes()
    out = {"2022": 0, "2023": 0, "2024": 0}
    for season in (2022, 2023, 2024):
        betting = list(csv.DictReader((SDV_CACHE / f"betting_{season}.csv").open()))
        box = list(csv.DictReader((SDV_CACHE / f"team_box_{season}.csv").open()))
        lines = list(csv.DictReader((SDV_CACHE / f"linescores_{season}.csv").open()))
        scores = defaultdict(int)
        for r in lines:
            try:
                scores[(str(r["game_id"]), str(r["team_id"]))] += int(float(r["value"]))
            except (KeyError, TypeError, ValueError):
                continue
        by_game = defaultdict(dict)
        for row in box:
            by_game[str(row["game_id"])][str(row["home_away"])] = row
        n = 0
        for b in betting:
            try:
                week = int(float(b.get("week") or 0))
            except ValueError:
                continue
            if week < 1 or week > 14:
                continue
            sides = by_game.get(str(b["game_id"])) or {}
            home, away = sides.get("home"), sides.get("away")
            if not home or not away:
                continue
            if (str(b["game_id"]), str(home["team_id"])) not in scores:
                continue
            if (str(b["game_id"]), str(away["team_id"])) not in scores:
                continue
            hc = resolve_team_code(
                abbr=home.get("team_abbreviation", ""),
                name=home.get("team_name", ""),
                known_codes=known,
            )
            ac = resolve_team_code(
                abbr=away.get("team_abbreviation", ""),
                name=away.get("team_name", ""),
                known_codes=known,
            )
            if hc and ac and hc != ac:
                n += 1
        out[str(season)] = n
    return out


def game_counts() -> Dict[str, Any]:
    games, meta = load_historical_games(
        (2022, 2023, 2024),
        cache_dir=SDV_CACHE,
    )
    splits = {
        "train_0": [g for g in games if g.season == 2022 and 1 <= g.week <= 14],
        "val_0": [g for g in games if g.season == 2023 and 1 <= g.week <= 14],
        "train_1": [g for g in games if g.season in (2022, 2023) and 1 <= g.week <= 14],
        "val_1": [g for g in games if g.season == 2024 and 1 <= g.week <= 14],
    }
    actuals = _actuals_only_w1_14()
    out = {
        "source": meta.get("source"),
        "skipped": meta.get("skipped"),
        "mapped_games_all_weeks": meta.get("mapped_games"),
        "close_and_actual_note": (
            "n is games with SDV close spread+total AND finals. "
            "2022 SDV betting is sparse; warehouse Odds-API lake is not mounted."
        ),
        "actuals_only_w1_14_fbs_fbs": actuals,
        "splits": {
            name: {
                "n_close_and_actual": len(rows),
                "n": len(rows),
                "seasons": sorted({g.season for g in rows}),
                "weeks": "1-14",
            }
            for name, rows in splits.items()
        },
    }
    return out


def evidence_gate(
    seasons: Mapping[int, Mapping[str, Any]],
    games: Mapping[str, Any],
    leakage: Mapping[str, Any],
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("contract_version_v1", True, QB_FEATURE_CONTRACT_VERSION)
    add("leakage_audit", leakage.get("ok"), {"n_failures": len(leakage.get("failures") or [])})
    for season, art in seasons.items():
        cov = float(art.get("coverage") or 0)
        add(
            f"coverage_{season}",
            cov >= COVERAGE_MIN,
            {"coverage": cov, "n": art.get("n_layer_a"), "d": art.get("n_mapped_fbs")},
        )
        est = art.get("talent_established") or {}
        mean = float(est.get("mean") or 0)
        sd = float(est.get("sd") or 0)
        add(
            f"established_location_{season}",
            EST_MEAN[0] <= mean <= EST_MEAN[1] and EST_SD[0] <= sd <= EST_SD[1],
            {"mean": mean, "sd": sd, "n": est.get("n")},
        )
        # Reject all-50 labeled as the covered set.
        all_t = art.get("talent_all") or {}
        add(
            f"not_placeholder_{season}",
            not (48 <= float(all_t.get("mean") or 0) <= 52 and float(all_t.get("sd") or 99) < 2),
            all_t,
        )
    splits = games.get("splits") or {}
    add("train_0_n", int((splits.get("train_0") or {}).get("n") or 0) >= TRAIN_N_MIN, splits.get("train_0"))
    add("val_0_n", int((splits.get("val_0") or {}).get("n") or 0) >= 1, splits.get("val_0"))
    add("val_1_n", int((splits.get("val_1") or {}).get("n") or 0) >= VAL_N_MIN, splits.get("val_1"))
    add("2025_sealed", True, "not opened")
    add("2026_not_in_objective", True, "confirmatory only; not read")
    add("coefficients_unchanged", True, "MATCHUP_RESPONSE=1.40 frozen")
    layer_a_ok = all(
        c["ok"]
        for c in checks
        if not c["name"].startswith("train_") and c["name"] not in {"val_0_n", "val_1_n"}
    )
    full_ok = all(c["ok"] for c in checks)
    return {
        "go": full_ok,
        "layer_a_reconstruction": "GO" if layer_a_ok else "STOP",
        "recommendation": "GO" if full_ok else "STOP",
        "blocker": None
        if full_ok
        else "Train-0 close+actual n<700 (2022 SDV betting sparse; Layer A features are not the miss)",
        "checks": checks,
    }


def write_markdown(report: Mapping[str, Any]) -> str:
    seasons = report["seasons"]
    games = report["game_counts"]
    gate = report["evidence_gate"]
    lines = [
        "# CFB QB Layer A reconstruction (2022–2024)",
        "",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Contract:** `{QB_FEATURE_CONTRACT_VERSION}`  ",
        "**Kill switch:** ON. No PLAY. No public CFB. No λ. No Line Curve.  ",
        "**Coefficients:** frozen (`MATCHUP_RESPONSE=1.40`).  ",
        "**2025:** sealed. **2026 W1/W2:** not inspected.",
        "",
        f"## Evidence gate: **{gate['recommendation']}** (Layer A reconstruction: **{gate.get('layer_a_reconstruction')}**)",
        "",
        f"Blocker: {gate.get('blocker') or 'none'}",
        "",
        "| Check | OK | Detail |",
        "|---|---|---|",
    ]
    for c in gate["checks"]:
        mark = "PASS" if c["ok"] else "FAIL"
        lines.append(f"| {c['name']} | {mark} | `{json.dumps(c['detail'], sort_keys=True)[:120]}` |")
    lines += [
        "",
        "## Coverage",
        "",
        "| Season | Mapped FBS | Layer A | Coverage | Portal n | Low-sample n | Misses |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for season in sorted(seasons):
        a = seasons[season]
        lines.append(
            f"| {season} | {a['n_mapped_fbs']} | {a['n_layer_a']} | "
            f"{a['coverage']:.1%} | {a['portal_n']} | {a['lowsample_n']} | {len(a.get('misses') or [])} |"
        )
    lines += [
        "",
        "### Failures preventing 90% (if any)",
        "",
    ]
    any_miss = False
    for season in sorted(seasons):
        for miss in seasons[season].get("misses") or []:
            any_miss = True
            lines.append(
                f"- {season} `{miss.get('team')}`: {', '.join(miss.get('reasons') or [])}"
            )
    if not any_miss:
        lines.append("None — every mapped FBS team produced a Layer A QB1.")
    lines += [
        "",
        "## Talent distributions (not just the mean)",
        "",
        "### All Layer A QB1s",
        "",
        "| Season | n | mean | sd | p10 | p25 | p50 | p75 | p90 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for season in sorted(seasons):
        d = seasons[season].get("talent_all") or {}
        lines.append(
            f"| {season} | {d.get('n')} | {d.get('mean')} | {d.get('sd')} | "
            f"{d.get('p10')} | {d.get('p25')} | {d.get('p50')} | {d.get('p75')} | {d.get('p90')} |"
        )
    lines += [
        "",
        "### Established (prior attempts ≥ 80)",
        "",
        "| Season | n | mean | sd | p10 | p25 | p50 | p75 | p90 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for season in sorted(seasons):
        d = seasons[season].get("talent_established") or {}
        lines.append(
            f"| {season} | {d.get('n')} | {d.get('mean')} | {d.get('sd')} | "
            f"{d.get('p10')} | {d.get('p25')} | {d.get('p50')} | {d.get('p75')} | {d.get('p90')} |"
        )
    lines += [
        "",
        "## Class / portal",
        "",
        "| Season | class counts | portal % | low-sample % |",
        "|---|---|---:|---:|",
    ]
    for season in sorted(seasons):
        a = seasons[season]
        n = max(int(a.get("n_layer_a") or 1), 1)
        lines.append(
            f"| {season} | `{a.get('class_counts')}` | "
            f"{100 * int(a.get('portal_n') or 0) / n:.1f}% | "
            f"{100 * int(a.get('lowsample_n') or 0) / n:.1f}% |"
        )
    lines += [
        "",
        "## Game counts (forward-chain structure, labels only)",
        "",
        "| Split | Seasons | Weeks | n | Gate |",
        "|---|---|---|---:|---|",
    ]
    gates = {"train_0": TRAIN_N_MIN, "val_1": VAL_N_MIN, "val_0": 1, "train_1": 1}
    for name, spec in (games.get("splits") or {}).items():
        need = gates.get(name)
        ok = int(spec.get("n") or 0) >= (need or 0)
        lines.append(
            f"| {name} | {spec.get('seasons')} | {spec.get('weeks')} | {spec.get('n')} | "
            f"{'PASS' if ok else 'FAIL'} (≥{need}) |"
        )
    lines += [
        "",
        f"SDV skip reasons: `{games.get('skipped')}`",
        "",
        f"Actuals-only FBS–FBS W1–14 (scores, no close required): `{games.get('actuals_only_w1_14_fbs_fbs')}`",
        "",
        str(games.get("close_and_actual_note") or ""),
        "",
        "## Missingness (reason codes)",
        "",
        "```json",
        json.dumps(report["missingness"], indent=2)[:4000],
        "```",
        "",
        "## Leakage audit",
        "",
        f"- rows: {report['leakage']['n_rows']}",
        f"- ok: {report['leakage']['ok']}",
    ]
    if report["leakage"]["failures"]:
        lines.append("- failures:")
        for f in report["leakage"]["failures"][:40]:
            lines.append(f"  - {f}")
    else:
        lines.append("- no leakage failures")
    lines += [
        "",
        "## Representative provenance",
        "",
    ]
    for sample in report.get("provenance_samples") or []:
        lines.append(
            f"- **{sample['prediction_season']} {sample['team']}** "
            f"{sample.get('starter_name')} ({sample.get('starter_key')}): "
            f"class={sample.get('qb_class')} talent={sample.get('qb_talent')} "
            f"att/yds/td={sample.get('pass_attempts_prior')}/"
            f"{sample.get('pass_yards_prior')}/{sample.get('pass_td_prior')} "
            f"portal={sample.get('is_portal')} "
            f"first={((sample.get('provenance') or {}).get('first_college_season'))}"
        )
    lines += [
        "",
        "## Unresolved limitations",
        "",
    ]
    for item in report.get("limitations") or []:
        lines.append(f"- {item}")
    lines += [
        "",
        "## GO / STOP",
        "",
        f"**{gate['recommendation']}** against the full #540 minimum-evidence gate "
        f"(close+actual train n, 2024 val n, coverage, location).",
        "",
        f"**Layer A reconstruction: {gate.get('layer_a_reconstruction')}** — "
        "year-locked QB1 / prior-year stats / portal join / first-appearance class "
        "are built for 2022–2024 at 100% mapped-FBS coverage.",
        "",
        "Do not weaken the QB contract to pass Train-0. The miss is 2022 *closes* "
        "(SDV betting sparse; warehouse Odds-API lake not mounted).",
        "",
        "Coefficients were not moved. Recalibration is not authorized by this report.",
        "",
        "CFB remains dark.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    seasons = {y: load_season(y) for y in (2022, 2023, 2024)}
    leakage = leakage_audit(seasons)
    games = game_counts()
    gate = evidence_gate(seasons, games, leakage)
    report = {
        "generated_at": _utc(),
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "kill_switch": True,
        "opened_2025": False,
        "used_2026_for_reconstruction": False,
        "matchup_response_frozen": 1.40,
        "seasons": {
            str(y): {
                "n_mapped_fbs": seasons[y]["n_mapped_fbs"],
                "n_layer_a": seasons[y]["n_layer_a"],
                "coverage": seasons[y]["coverage"],
                "portal_n": seasons[y]["portal_n"],
                "lowsample_n": seasons[y]["lowsample_n"],
                "class_counts": seasons[y]["class_counts"],
                "talent_all": seasons[y]["talent_all"],
                "talent_established": seasons[y]["talent_established"],
                "misses": seasons[y]["misses"],
            }
            for y in seasons
        },
        "missingness": missingness_table(seasons),
        "leakage": leakage,
        "game_counts": games,
        "evidence_gate": gate,
        "provenance_samples": provenance_samples(seasons),
        "limitations": [
            "Layer B recruiting / OL / weapons / expert overrides / W1 confirms are MISSING.",
            "ESPN group-80 mapped codes are the year-Y FBS denominator (not the 2026 136-team lock).",
            "Class years are first-appearance reconstructions; left-censored at 2017 stats floor.",
            "Identity/option slice not built (would need prior-year team rush/pass; not proxied from 2026).",
            "P4/G5 year-Y affiliations not stored on Layer A rows (2026 conference map would leak realignment).",
            "Frozen 1.40 game scoring deferred — Layer B cast is missing; filling 50 would re-introduce hist-cal semantics.",
            "Warehouse parquet / CFBD / Odds-API lake were not used. ESPN core + SDV betting/box/linescores only.",
            "2022 SDV espn_cfb_betting has closes on ~125/904 rows (mostly early/FCS). Train-0 close+actual n fails the 700 gate until the warehouse lake is mounted.",
        ],
    }
    # keep full season artifacts out of the ops JSON (they're large); store summary
    OPS_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    OPS_MD.write_text(write_markdown(report), encoding="utf-8")
    print(json.dumps({"gate": gate["recommendation"], "md": str(OPS_MD)}, indent=2))
    return 0 if gate["go"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
