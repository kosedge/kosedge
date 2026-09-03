#!/usr/bin/env python3
"""Read-only CFB totals-guard unused holdout (no product KEI / pack write).

Joins hist-cal proxy model totals + SDV close (same spine as
``run_spread_tag_close_holdout.py``). Fits candidates on **2023–2024** W0–2
only; evaluates **unused 2025**. Does not retune from 2025. Does not mint CLV.

Candidates (design Task 5):
  (b) primary — matchup-inflation dampen λ on the sum (preserves spread)
  (a) fallback — additive level offset

Does NOT edit apply_cfb_kei / pack / live tagger / PLAY flags.

Usage:
  PYTHONPATH=services/model-service \\
    python3 scripts/cfb/run_totals_guard_holdout.py --seasons 2023,2024,2025

Requires network (or a populated --cache-dir) for SportsDataverse release CSVs:
  espn_cfb_betting / espn_cfb_team_box / espn_cfb_linescores + cfb_ratings.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine import priors as P  # noqa: E402
from src.services.cfb_season_engine.historical_calibration import (  # noqa: E402
    build_historical_proxy_universe,
    load_historical_games,
    ratings_to_efficiency_map,
)
from src.services.cfb_season_engine.team_projection import project_game  # noqa: E402
from src.services.cfb_season_engine.totals_guard_holdout import (  # noqa: E402
    FIT_SEASONS,
    OPTIONAL_WEEK_MAX,
    PRIMARY_WEEK_MAX,
    UNUSED_EVAL_SEASONS,
    apply_level_offset,
    apply_matchup_inflation_dampen,
    assert_no_eval_leakage_in_fit,
    filter_eval_rows,
    filter_fit_rows,
    fit_lambda_ols,
    fit_level_offset,
    green_bars_vs_identity,
    matchup_inflation_on_sum,
    summarize_kei_vs_close,
    year_label,
)


def _project_totals_rows(
    seasons: Sequence[int],
    *,
    cache_dir: Optional[Path],
) -> Dict[str, Any]:
    """Same join as hist-cal / spread Tag holdout, plus matchup-inflation features."""
    from collections import defaultdict

    games, load_meta = load_historical_games(seasons, cache_dir=cache_dir)
    codes_by_season: Dict[int, set] = defaultdict(set)
    for g in games:
        codes_by_season[g.season].add(g.home_code)
        codes_by_season[g.season].add(g.away_code)

    universes = {}
    eff_meta: Dict[str, Any] = {}
    for season in seasons:
        prior = season - 1
        eff = ratings_to_efficiency_map(prior, cache_dir=cache_dir)
        codes = set(eff) | set(codes_by_season.get(season) or ())
        universes[season] = build_historical_proxy_universe(
            season, eff, codes=sorted(codes)
        )
        eff_meta[str(season)] = {
            "prior_ratings_year": prior,
            "teams_with_efficiency": len(eff),
            "universe_teams": len(codes),
        }

    rows: List[Dict[str, Any]] = []
    skipped_proj = 0
    for g in games:
        universe = universes.get(g.season)
        if universe is None:
            skipped_proj += 1
            continue
        if g.home_code not in universe.teams or g.away_code not in universe.teams:
            skipped_proj += 1
            continue
        proj = project_game(
            universe,
            home_team=g.home_code,
            away_team=g.away_code,
            week=g.week,
            season=g.season,
            neutral_site=False,
            engine_version=P.ENGINE_VERSION,
        )
        model_total = float(proj.expected_total)
        model_spread = float(proj.spread_home)
        home_exp = float(proj.expected_home_score)
        away_exp = float(proj.expected_away_score)
        matchup = (proj.drivers or {}).get("matchup") or {}
        home_diag = matchup.get("home_points_diag") or {}
        away_diag = matchup.get("away_points_diag") or {}
        st_nudge = float(matchup.get("st_total_nudge") or 0.0)
        if not home_diag or not away_diag:
            skipped_proj += 1
            continue
        total_neutral, inflation = matchup_inflation_on_sum(
            model_total=model_total,
            home_diag=home_diag,
            away_diag=away_diag,
            league_ppg=float(P.LEAGUE_TEAM_PPG),
            points_clamp=tuple(P.EXPECTED_POINTS_CLAMP),  # type: ignore[arg-type]
            st_nudge=st_nudge,
        )
        # Coherence check: spread from scores must match published spread.
        spread_from_scores = away_exp - home_exp
        rows.append(
            {
                "game_id": g.game_id,
                "season": int(g.season),
                "week": int(g.week),
                "home": g.home_code,
                "away": g.away_code,
                "year_label": year_label(int(g.season)),
                "model_total": model_total,
                "model_spread_home": model_spread,
                "expected_home_score": home_exp,
                "expected_away_score": away_exp,
                "spread_from_scores": round(spread_from_scores, 4),
                "close_total": float(g.close_total),
                "close_spread_home": float(g.close_spread_home),
                "actual_total": float(g.home_score + g.away_score),
                "total_neutral": round(total_neutral, 4),
                "matchup_inflation": round(inflation, 4),
                "st_nudge": st_nudge,
            }
        )

    load_meta = dict(load_meta)
    load_meta["skipped_proj"] = skipped_proj
    return {
        "load": load_meta,
        "efficiency": eff_meta,
        "rows": rows,
        "priors_snapshot": {
            "ENGINE_VERSION": P.ENGINE_VERSION,
            "CALIBRATION_TAG": P.CALIBRATION_TAG,
            "LEAGUE_TEAM_PPG": P.LEAGUE_TEAM_PPG,
            "MATCHUP_RESPONSE": P.MATCHUP_RESPONSE,
            "EXPECTED_POINTS_CLAMP": list(P.EXPECTED_POINTS_CLAMP),
        },
    }


def _apply_candidates(
    rows: Sequence[Mapping[str, Any]],
    *,
    lam: float,
    offset: float,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        model = float(r["model_total"])
        infl = float(r["matchup_inflation"])
        home = float(r["expected_home_score"])
        away = float(r["expected_away_score"])
        kei_b = apply_matchup_inflation_dampen(model, infl, lam)
        kei_a = apply_level_offset(model, offset)
        delta_b = kei_b - model
        # Even split of ΔT would leave spread unchanged.
        spread_after_b = (away + 0.5 * delta_b) - (home + 0.5 * delta_b)
        out.append(
            {
                **dict(r),
                "kei_total_identity": model,
                "kei_total_b_dampen": round(kei_b, 4),
                "kei_total_a_offset": round(kei_a, 4),
                "spread_after_b_even_split": round(spread_after_b, 4),
                "margin_preserved_b": abs(spread_after_b - float(r["model_spread_home"]))
                < 1e-6,
            }
        )
    return out


def _window_block(
    enriched: Sequence[Mapping[str, Any]],
    *,
    week_max: int,
    lam: float,
    offset: float,
) -> Dict[str, Any]:
    fit = filter_fit_rows(enriched, week_max=week_max)
    assert_no_eval_leakage_in_fit(fit)
    unused = filter_eval_rows(enriched, week_max=week_max)
    contaminated = [
        r
        for r in enriched
        if int(r["season"]) in FIT_SEASONS and 0 <= int(r["week"]) <= week_max
    ]

    def _metrics(subset: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        return {
            "identity": summarize_kei_vs_close(subset, kei_key="kei_total_identity"),
            "b_matchup_dampen": summarize_kei_vs_close(
                subset, kei_key="kei_total_b_dampen"
            ),
            "a_level_offset": summarize_kei_vs_close(
                subset, kei_key="kei_total_a_offset"
            ),
        }

    unused_m = _metrics(unused)
    green_b = green_bars_vs_identity(
        candidate=unused_m["b_matchup_dampen"],
        identity=unused_m["identity"],
    )
    green_a = green_bars_vs_identity(
        candidate=unused_m["a_level_offset"],
        identity=unused_m["identity"],
    )
    return {
        "week_max": week_max,
        "window": f"W0-{week_max}",
        "fit_n": len(fit),
        "coefficients_locked_from_fit": {
            "lambda_b": lam,
            "level_offset_a": offset,
            "fit_seasons": sorted(FIT_SEASONS),
            "fit_week_max": week_max,
            "note": "Coefficients fit on contaminated W0–week_max only; unused eval does not retune",
        },
        "unused_2025": {
            **unused_m,
            "green_b_vs_identity": green_b,
            "green_a_vs_identity": green_a,
        },
        "contaminated_2023_2024": _metrics(contaminated),
        "by_season": {
            str(s): {
                "year_label": year_label(s),
                **_metrics(
                    [
                        r
                        for r in enriched
                        if int(r["season"]) == s and 0 <= int(r["week"]) <= week_max
                    ]
                ),
            }
            for s in sorted({int(r["season"]) for r in enriched})
        },
    }


def _fmt_row(label: str, m: Mapping[str, Any]) -> str:
    return (
        f"| {label} | {m['n']} | {m['mean_kei_minus_close']} | {m['mae']} | "
        f"{m['over_sign_bias']} | unavailable |"
    )


def _render_md(report: Mapping[str, Any], out_path: Path) -> None:
    w02 = report["windows"]["W0_2"]
    w04 = report["windows"]["W0_4"]
    unused = w02["unused_2025"]
    contam = w02["contaminated_2023_2024"]
    lam = report["coefficients"]["lambda_b_fit_w0_2"]
    offset = report["coefficients"]["level_offset_a_fit_w0_2"]
    lines = [
        f"# CFB totals-guard unused holdout ({report['stamp']})",
        "",
        f"**Branch:** `{report.get('branch', 'cursor/cfb-totals-guard-holdout')}` → `deploy-vercel`",
        "**Script:** `scripts/cfb/run_totals_guard_holdout.py`",
        f"**Artifacts:** `data/ops/cfb-totals-guard-holdout-{report['stamp']}/`",
        "**Design SoT:** `docs/CFB_KEI_CALIBRATOR_DESIGN.md` (Task 5; may land via PR 441)",
        "**Spine:** `scripts/cfb/run_spread_tag_close_holdout.py` · "
        "`data/ops/cfb-spread-tag-close-holdout-20260903.md`",
        "**Product change:** none (read-only harness). No `apply_cfb_kei` edit, no pack remat,",
        "no `kei_total` divergence enabled, no PLAY unsat.",
        "",
        "## Honesty",
        "",
        "- Join = hist-cal proxy model totals + SDV close (same honesty as spread Tag holdout).",
        "- Fit **2023–2024** only; eval **unused 2025**. Do **not** retune λ / offset from 2025.",
        "- W0–2 is the first GREEN window — do **not** retune λ on live W1 street.",
        "- CLV **unavailable** (close-only SDV). Labeled; not minted.",
        "- Proxy KEI understates live 2026 Over-drunk (league-avg roster/QB). Unused GREEN on",
        "  proxy is a necessary gate, not a claim live W1 will match.",
        "- This harness does **not** enable `kei_total` divergence or unsat PLAY.",
        "- GREEN bars below are design §4 divergence gates only. PLAY unsat needs CLV or a",
        "  second unused year (ATS-only vs close is insufficient).",
        f"- Mapped games projected: **{report['n_games_projected']}**. "
        f"Margin preserved under (b) even-split on all rows: "
        f"**{report['margin_preserved_on_all_rows_b']}**.",
        "",
        "## Coefficients (locked from fit 2023–2024 W0–2)",
        "",
        f"| Candidate | Coefficient | fit n |",
        f"| --- | ---: | ---: |",
        f"| (b) λ matchup-inflation dampen | {lam} | {report['coefficients']['fit_n_w0_2']} |",
        f"| (a) level offset | {offset} | {report['coefficients']['fit_n_w0_2']} |",
        "",
        "W0–4 tables reuse these locked coefficients (no retune on the wider window).",
        "",
        "## Results — unused 2025 W0–2 (PRIMARY)",
        "",
        "| Path | n | mean(KEI−close) | MAE | Over-sign bias | CLV+ |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
        _fmt_row("identity (`kei=model`)", unused["identity"]),
        _fmt_row("(b) λ dampen", unused["b_matchup_dampen"]),
        _fmt_row("(a) level offset", unused["a_level_offset"]),
    ]
    gb = unused["green_b_vs_identity"]
    ga = unused["green_a_vs_identity"]
    lines.extend(
        [
            "",
            "### GREEN bars (divergence only — not PLAY)",
            "",
            "| Candidate | abs(mean)≤1 | MAE not worse >0.3 | mean not >+2 | all GREEN |",
            "| --- | --- | --- | --- | --- |",
            f"| (b) | {gb['level_ok']} | {gb['mae_ok']} | {gb['direction_ok']} | {gb['all_green']} |",
            f"| (a) | {ga['level_ok']} | {ga['mae_ok']} | {ga['direction_ok']} | {ga['all_green']} |",
            "",
            "Proxy note: identity mean gap on unused W0–2 is already near zero "
            f"({unused['identity']['mean_kei_minus_close']}). Live 2026 roster path is hotter; "
            "do not ship divergence from this proxy table alone.",
            "",
            "## Results — contaminated 2023–2024 W0–2 (fit / confirmatory)",
            "",
            "| Path | n | mean(KEI−close) | MAE | Over-sign bias | CLV+ |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
            _fmt_row("identity", contam["identity"]),
            _fmt_row("(b) λ dampen", contam["b_matchup_dampen"]),
            _fmt_row("(a) level offset", contam["a_level_offset"]),
            "",
            "## Results — unused 2025 W0–4 (optional confirmatory)",
            "",
            "| Path | n | mean(KEI−close) | MAE | Over-sign bias | CLV+ |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
            _fmt_row("identity", w04["unused_2025"]["identity"]),
            _fmt_row("(b) λ dampen", w04["unused_2025"]["b_matchup_dampen"]),
            _fmt_row("(a) level offset", w04["unused_2025"]["a_level_offset"]),
            "",
            f"W0–4 GREEN (b): `{w04['unused_2025']['green_b_vs_identity']['all_green']}` · "
            f"(a): `{w04['unused_2025']['green_a_vs_identity']['all_green']}` "
            "(still not a PLAY unlock; coefficients not retuned).",
            "",
            "## Reproduce",
            "",
            "```bash",
            "PYTHONPATH=services/model-service \\",
            f"  python3 scripts/cfb/run_totals_guard_holdout.py --seasons 2023,2024,2025 --stamp {report['stamp']}",
            "```",
            "",
            "Requires SportsDataverse HTTP fetch (`espn_cfb_betting` / `team_box` / "
            "`linescores` + `cfb_ratings`) or a populated `--cache-dir` from a prior run.",
            "",
            "## CoS one-liner",
            "",
            "**Harness only: identity vs (b)/(a) on unused 2025 W0–2; coefficients locked on "
            "2023–24; no product KEI path change; PLAY stays sat until CLV/second-year bar.**",
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="CFB totals-guard unused holdout")
    ap.add_argument("--seasons", default="2023,2024,2025")
    ap.add_argument("--stamp", default=date.today().strftime("%Y%m%d"))
    ap.add_argument(
        "--cache-dir",
        default=None,
        help="SDV CSV cache dir (default: data/ops/cfb-totals-guard-holdout-<stamp>/cache)",
    )
    ap.add_argument(
        "--skip-fetch-doc-only",
        action="store_true",
        help="If set and no rows can be loaded, still write a stub ops note documenting SDV need",
    )
    args = ap.parse_args()
    seasons = [int(x.strip()) for x in args.seasons.split(",") if x.strip()]
    out_dir = ROOT / "data" / "ops" / f"cfb-totals-guard-holdout-{args.stamp}"
    cache_dir = Path(args.cache_dir) if args.cache_dir else (out_dir / "cache")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".gitignore").write_text(
        "# SportsDataverse re-fetch cache (not committed).\ncache/\n",
        encoding="utf-8",
    )

    print(f"== totals-guard holdout seasons={seasons} cache={cache_dir} ==")
    try:
        payload = _project_totals_rows(seasons, cache_dir=cache_dir)
    except Exception as exc:  # noqa: BLE001 — research harness documents fetch failure
        if not args.skip_fetch_doc_only:
            print(f"ERROR: SDV/hist-cal load failed: {exc}")
            print(
                "Re-run with network access, or pass --cache-dir pointing at prior "
                "espn_cfb_* / cfb_ratings CSVs, or --skip-fetch-doc-only for stub note."
            )
            return 2
        stub = {
            "stamp": args.stamp,
            "error": str(exc),
            "required_fetch": {
                "source": "SportsDataverse GitHub releases",
                "tags": [
                    "espn_cfb_betting",
                    "espn_cfb_team_box",
                    "espn_cfb_linescores",
                    "cfb_ratings",
                ],
                "join": "same as scripts/cfb/run_spread_tag_close_holdout.py",
            },
            "product_change": False,
        }
        (out_dir / "summary.json").write_text(
            json.dumps(stub, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote stub {out_dir / 'summary.json'}")
        return 0

    rows_in = payload.get("rows") or []
    if not rows_in:
        print("ERROR: no projected rows", list(payload.keys()))
        return 2

    # Fit coefficients on contaminated W0–2 ONLY (primary window). Never touch 2025.
    fit_primary = filter_fit_rows(rows_in, week_max=PRIMARY_WEEK_MAX)
    assert_no_eval_leakage_in_fit(fit_primary)
    lam = fit_lambda_ols(fit_primary)
    offset = fit_level_offset(fit_primary)
    print(f"fit W0-{PRIMARY_WEEK_MAX}: n={len(fit_primary)} λ={lam:.4f} offset={offset:.4f}")

    enriched = _apply_candidates(rows_in, lam=lam, offset=offset)
    margin_ok = all(bool(r.get("margin_preserved_b")) for r in enriched)
    if not margin_ok:
        print("ERROR: (b) dampen failed margin-preservation check on at least one row")
        return 3

    windows = {
        "W0_2": _window_block(
            enriched, week_max=PRIMARY_WEEK_MAX, lam=lam, offset=offset
        ),
        "W0_4": _window_block(
            enriched, week_max=OPTIONAL_WEEK_MAX, lam=lam, offset=offset
        ),
    }
    # W0–4 table reuses λ/offset locked from W0–2 fit (do not retune on W1 / wider).
    windows["W0_4"]["coefficients_locked_from_fit"] = {
        **windows["W0_2"]["coefficients_locked_from_fit"],
        "note": (
            "λ/offset locked from W0–2 fit only; W0–4 is confirmatory table — "
            "do not retune λ on W1 or on the wider window"
        ),
    }

    report: Dict[str, Any] = {
        "stamp": args.stamp,
        "branch": "cursor/cfb-totals-guard-holdout-2896",
        "rule": {
            "identity": "kei_total = model_total (live today)",
            "candidate_b": "kei_total = model_total - (1-λ)*matchup_inflation (sum-only)",
            "candidate_a": "kei_total = model_total + level_offset",
            "fit_seasons": sorted(FIT_SEASONS),
            "unused_eval_seasons": sorted(UNUSED_EVAL_SEASONS),
            "primary_window": f"W0-{PRIMARY_WEEK_MAX}",
            "optional_window": f"W0-{OPTIONAL_WEEK_MAX}",
            "clv_definition": (
                "movement-CLV+: owned open≠close; unavailable when only close exists"
            ),
            "market": "SDV espn_cfb_betting over_under (close)",
            "model": "hist-cal proxy project_game expected_total",
        },
        "honesty": {
            "reconstruction": (
                "Hist-cal proxy: prior-year cfb_ratings + league-avg roster/QB — "
                "not live 2026 roster/SP+ KEI. Understates live Over-drunk."
            ),
            "year_split": {
                "fit_contaminated": sorted(FIT_SEASONS),
                "unused_eval": sorted(UNUSED_EVAL_SEASONS),
                "note": (
                    "Fit 2023–2024 only; eval unused 2025; do not retune from 2025; "
                    "W0–2 first window — do not retune λ on W1"
                ),
            },
            "product": {
                "writes_pack": False,
                "edits_apply_cfb_kei": False,
                "enables_kei_total_divergence": False,
                "unsats_totals_play": False,
                "note": (
                    "Harness does not enable kei_total divergence or unsat PLAY. "
                    "GREEN bars are design divergence gates only. PLAY unsat needs "
                    "CLV or second unused year (ATS-only insufficient)."
                ),
            },
            "clv": "CLV unavailable — labeled; not minted",
        },
        "load": payload.get("load"),
        "efficiency": payload.get("efficiency"),
        "priors_snapshot": payload.get("priors_snapshot"),
        "n_games_projected": len(rows_in),
        "coefficients": {
            "lambda_b_fit_w0_2": round(lam, 6),
            "level_offset_a_fit_w0_2": round(offset, 6),
            "fit_n_w0_2": len(fit_primary),
        },
        "margin_preserved_on_all_rows_b": margin_ok,
        "windows": windows,
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sample = enriched[:40]
    (out_dir / "sample_rows.json").write_text(
        json.dumps(sample, indent=2) + "\n", encoding="utf-8"
    )
    ops_md = ROOT / "data" / "ops" / f"cfb-totals-guard-holdout-{args.stamp}.md"
    _render_md(report, ops_md)
    print(json.dumps(windows["W0_2"]["unused_2025"], indent=2))
    print(f"wrote {summary_path}")
    print(f"wrote {ops_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
