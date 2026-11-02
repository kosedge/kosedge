"""t5146u R4 ONE EXEC — opt-in last-played reconstruction (2020–21 DEV).

Does not modify recon_driver exact-week path or helper 7e77c57f.
No target scoring labels in the artifact. No error join. No market.
CERT=0. RETRO_FIT / RECONSTRUCTED. Timestamps unverified.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .inputs import GAMES_SHA256, OUTCOMES_SHA256, SOURCE_SHA
from .last_played_t2 import (
    LABELS,
    PATH_ID,
    SCHEMA_VERSION,
    LastPlayedRefuse,
    LastPlayedSelection,
    select_last_played_sides,
    t4_from_last_played,
)
from .recon_contract import CONTRACT_27, _finite
from .recon_driver import (
    DEFAULT_PBP_ARCHIVE,
    HELPER_SHA256,
    HELPER_TIP,
    LABEL_RECONSTRUCTED,
    LABEL_RESEARCH,
    LABEL_RETRO_FIT,
    ReconRefuse,
    apply_2020_23_identity,
    cell_row_hash,
    load_pbp_plays,
    sha256_file,
    sha256_text,
    t4_from_t2_sides,
)

DEV_SEASONS = (2020, 2021)
T4_FIELDS = (
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
)
FORBIDDEN_ARTIFACT_KEYS = (
    "actual_margin",
    "actual_total",
    "home_score",
    "away_score",
    "error",
    "abs_error",
    "m_if",
    "m_challenger",
    "market",
    "quote",
    "spread",
    "total",
)
T1_LINEAGE = (
    "T1=nfl_dp_team_situational_weekly port from helper 7e77c57f. "
    "T2=rolling_5g ROWS 4 PRECEDING AND CURRENT. "
    "T3=opt-in last-played rating_week < target_week (NOT exact week-1). "
    "T4 helper.main contract diffs. "
    "T5 team_strength_from_record same-season as-of prior kickoff. "
    "RETRO_FIT / RECONSTRUCTED. timestamps unverified. "
    "NOT production-causal / real-time source availability."
)


def t1_evidence(ids: Sequence[str]) -> str:
    """Alex Phase B required form: t1=<id>|<id>|..."""
    if not ids:
        raise LastPlayedRefuse("t1= evidence empty")
    return "t1=" + "|".join(ids)


def _fmt(value: float, digits: int) -> str:
    return f"{float(value):.{digits}f}"


def _assert_no_forbidden(payload: Mapping[str, Any]) -> None:
    blob = json.dumps(payload, default=str)
    lowered = blob.lower()
    for key in FORBIDDEN_ARTIFACT_KEYS:
        if f'"{key}"' in lowered or f"'{key}'" in lowered:
            raise ReconRefuse(f"artifact contains forbidden key {key}")


def reconstruct_slate_last_played(
    *,
    targets: Sequence[Mapping[str, Any]],
    games: Sequence[Mapping[str, Any]],
    completed_prior: Sequence[Mapping[str, Any]],
    helper: Any,
    plays: Any,
    pbp_sha_by_season: Mapping[int, str],
) -> dict[str, Any]:
    """Build last-played DEV packets. Completeness decided here; no error join."""
    apply_2020_23_identity(helper)
    if getattr(plays, "empty", True):
        raise ReconRefuse("no prior-week REG pass/run plays")
    # rolling_5g groups by team only. Build T1/T2 per season so 2020 games
    # cannot enter 2021 trailing-five means (same-season formula, unchanged).
    t1_by_season: dict[int, Any] = {}
    t2_by_season: dict[int, Any] = {}
    for season in sorted({int(x) for x in plays["season"].dropna().astype(int).unique()}):
        season_plays = plays[plays["season"] == season]
        if getattr(season_plays, "empty", True):
            continue
        t1_by_season[season] = helper.t1_from_plays(season_plays)
        t2_by_season[season] = helper.rolling_5g(t1_by_season[season])

    matrix: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []
    complete: list[str] = []
    partial: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()

    for rec in targets:
        season = int(rec["season"])
        week = int(rec["week"])
        gid = str(rec["game_id"])
        home = str(rec["home"])
        away = str(rec["away"])
        kick = str(rec["kickoff_utc"])
        if season not in DEV_SEASONS:
            refused.append({"game_id": gid, "reason": f"SEASON_OUT_OF_DEV_{season}"})
            continue
        if week <= 1:
            refused.append(
                {
                    "game_id": gid,
                    "reason": "W1_NO_PRIOR: rating_week < 1 / no last-played same-season snapshot",
                }
            )
            continue
        if not kick:
            refused.append({"game_id": gid, "reason": "MISSING_KICKOFF"})
            continue
        cutoff = helper.parse_utc(kick)
        prior_completed = [
            row
            for row in completed_prior
            if int(row["season"]) == season and str(row.get("game_id")) != gid
        ]
        w_h, l_h, n_h = helper.record_asof(prior_completed, home, cutoff, season)
        w_a, l_a, n_a = helper.record_asof(prior_completed, away, cutoff, season)
        rec_h = f"{w_h}-{l_h}"
        rec_a = f"{w_a}-{l_a}"
        if n_h < 1 or n_a < 1 or rec_h == "0-0" or rec_a == "0-0":
            refused.append(
                {
                    "game_id": gid,
                    "reason": "T5_ZERO_COMPLETED_SAME_SEASON: no-fill / no 0-0 baseline",
                    "n_home": n_h,
                    "n_away": n_a,
                }
            )
            continue

        if season not in t1_by_season or season not in t2_by_season:
            refused.append({"game_id": gid, "reason": f"NO_T1_T2_SEASON_{season}"})
            continue
        t1 = t1_by_season[season]
        t2 = t2_by_season[season]
        t1 = t1[t1["week"] < week].copy()
        t2 = t2[t2["week"] < week].copy()
        try:
            home_sel, away_sel = select_last_played_sides(
                t2,
                home=home,
                away=away,
                season=season,
                target_week=week,
                target_game_id=gid,
                target_kickoff_utc=kick,
                games=games,
                t1=t1,
            )
        except LastPlayedRefuse as exc:
            refused.append({"game_id": gid, "reason": str(exc)})
            continue

        home_t1 = t1_evidence(home_sel.last_five_source_game_ids)
        away_t1 = t1_evidence(away_sel.last_five_source_game_ids)
        if not home_t1.startswith("t1=") or not away_t1.startswith("t1="):
            raise ReconRefuse(f"{gid} Phase B t1= evidence missing")
        if home_t1[3:] != "|".join(home_sel.last_five_source_game_ids):
            raise ReconRefuse(f"{gid} home t1= does not match last-five identities")
        if away_t1[3:] != "|".join(away_sel.last_five_source_game_ids):
            raise ReconRefuse(f"{gid} away t1= does not match last-five identities")

        rating_label = (
            f"H{home_sel.selected_rating_week}/A{away_sel.selected_rating_week}"
        )
        rest_et = helper.rest_days_et(kick)
        values = t4_from_last_played(home_sel, away_sel)
        pbp_sha = pbp_sha_by_season.get(season, "")

        def add(
            field: str,
            status: str,
            *,
            value: object = "",
            source_path: str = "",
            source_sha256: str = "",
            lineage: str = "",
            evidence: str = "",
            exclusion_reason: str = "",
            notes: str = "",
        ) -> None:
            row = {
                "game_id": gid,
                "season": season,
                "week": week,
                "home_team": home,
                "away_team": away,
                "field": field,
                "status": status,
                "reconstructed_value": value,
                "source_path": source_path,
                "source_sha256": source_sha256,
                "source_sha8": source_sha256[:8] if source_sha256 else "",
                "pregame_cutoff_utc": kick,
                "rating_week": rating_label,
                "derivation_lineage": lineage,
                "availability_evidence": evidence,
                "exclusion_reason": exclusion_reason,
                "notes": notes,
                "label": LABEL_RECONSTRUCTED,
                "fit_label": LABEL_RETRO_FIT,
                "research_label": LABEL_RESEARCH,
            }
            row["row_sha256"] = cell_row_hash(row)
            matrix.append(row)
            status_counts[status] += 1

        for field, value in {
            "game_id": gid,
            "home_team": home,
            "away_team": away,
            "matchup_season": str(season),
            "matchup_week": str(week),
        }.items():
            add(
                field,
                "DERIVED_PREGAME",
                value=value,
                source_path="games.csv 4fe1cdd7",
                source_sha256=GAMES_SHA256,
                lineage="2020-21 identity from games.csv pin; kickoff UTC Z",
                evidence=f"game_id={gid}",
                notes="identity plumbing; not a new feature",
            )
        for side in ("home", "away"):
            add(
                f"rest_days_{side}",
                "DERIVED_PREGAME",
                value=str(rest_et),
                source_path="helper.rest_days_et",
                source_sha256=HELPER_SHA256,
                lineage="ET DOW heuristic (Thu=4, Mon=6, else=7). Same both sides.",
                evidence=f"kickoff_utc={kick} rest_et={rest_et}",
                notes="games.csv rest_days_* hardcoded 7.0 NOT used",
            )
        for side, rec_wl, n_played in (("home", rec_h, n_h), ("away", rec_a, n_a)):
            off_i, def_i = helper.team_strength_from_record(rec_wl)
            add(
                f"offense_index_{side}",
                "DERIVED_PREGAME",
                value=_fmt(off_i, 6),
                source_path="helper.team_strength_from_record",
                source_sha256=OUTCOMES_SHA256,
                lineage="T5: off=clamp(0.90+0.22*wp, 0.82, 1.18) same-season as-of prior only",
                evidence=f"record_asof={rec_wl} n={n_played} cutoff={kick}",
                notes="target scores not loaded into artifact; not 1ee90fac",
            )
            add(
                f"defense_index_{side}",
                "DERIVED_PREGAME",
                value=_fmt(def_i, 6),
                source_path="helper.team_strength_from_record",
                source_sha256=OUTCOMES_SHA256,
                lineage="T5: def=clamp(0.92+0.20*wp, 0.82, 1.20) same-season as-of prior only",
                evidence=f"record_asof={rec_wl} n={n_played} cutoff={kick}",
                notes="target scores not loaded into artifact; not 1ee90fac",
            )
        for field in T4_FIELDS:
            val = values[field]
            if not _finite(val):
                add(
                    field,
                    "MISSING_RECORD",
                    source_path="last_played_t2.select_last_played_t2",
                    source_sha256=pbp_sha or HELPER_SHA256,
                    lineage=T1_LINEAGE,
                    evidence=(
                        f"{home_t1}; {away_t1}; rating={rating_label}; "
                        f"newest_nonfinite H={home_sel.newest_nonfinite} "
                        f"A={away_sel.newest_nonfinite}"
                    ),
                    notes=(
                        "no default; newest last-played snapshot kept; "
                        "did not skip to older finite. timestamps unverified."
                    ),
                    exclusion_reason=(
                        "T2 last-played newest row non-finite or T4 undefined"
                    ),
                )
                continue
            add(
                field,
                "DERIVED_PREGAME",
                value=_fmt(float(val), 8),
                source_path="helper.t1_from_plays + rolling_5g + last-played + T4",
                source_sha256=pbp_sha or HELPER_SHA256,
                lineage=T1_LINEAGE,
                evidence=(
                    f"{home_t1}; {away_t1}; rating={rating_label}; cutoff={kick}"
                ),
                notes=(
                    "Same T1–T4 as 7e77c57f. last-played selection only. "
                    "RETRO_FIT / RECONSTRUCTED. NOT production-causal."
                ),
            )

        fields_here = [row["field"] for row in matrix if row["game_id"] == gid]
        if set(fields_here) != set(CONTRACT_27) or len(fields_here) != 27:
            raise ReconRefuse(f"{gid} field set {fields_here} != CONTRACT_27")
        derived_here = sum(
            1
            for row in matrix
            if row["game_id"] == gid and row["status"] == "DERIVED_PREGAME"
        )
        missing_here = sum(
            1
            for row in matrix
            if row["game_id"] == gid and row["status"] == "MISSING_RECORD"
        )
        identity = {
            "game_id": gid,
            "season": season,
            "week": week,
            "home": home,
            "away": away,
            "selected_rating_week_home": home_sel.selected_rating_week,
            "selected_rating_week_away": away_sel.selected_rating_week,
            "exact_week_minus_one": week - 1,
            "no_bye_both_sides": (
                home_sel.selected_rating_week == week - 1
                and away_sel.selected_rating_week == week - 1
            ),
            "consumed_game_ids_home": list(home_sel.consumed_game_ids),
            "consumed_game_ids_away": list(away_sel.consumed_game_ids),
            "t1_home": home_t1,
            "t1_away": away_t1,
            "newest_nonfinite_home": home_sel.newest_nonfinite,
            "newest_nonfinite_away": away_sel.newest_nonfinite,
            "publication_timestamp_status": "unverified",
            "observation_timestamp_status": "unverified",
            "production_causal_claim": False,
            "realtime_source_availability_claim": False,
            "labels": list(LABELS),
            "path_id": PATH_ID,
            "derived": derived_here,
            "missing": missing_here,
        }
        identities.append(identity)
        if derived_here == 27 and missing_here == 0:
            complete.append(gid)
        else:
            partial.append(
                {
                    "game_id": gid,
                    "derived": derived_here,
                    "missing": missing_here,
                    "reason": "T2 last-played newest row non-finite or T4 undefined",
                    "selected_rating_week_home": home_sel.selected_rating_week,
                    "selected_rating_week_away": away_sel.selected_rating_week,
                    "newest_nonfinite_home": home_sel.newest_nonfinite,
                    "newest_nonfinite_away": away_sel.newest_nonfinite,
                    "t1_home": home_t1,
                    "t1_away": away_t1,
                }
            )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "path_id": PATH_ID,
        "label": LABEL_RECONSTRUCTED,
        "fit_label": LABEL_RETRO_FIT,
        "research_label": LABEL_RESEARCH,
        "cert_candidate": 0,
        "eval": None,
        "scored_look": False,
        "error_join": False,
        "forecast_or_market_metrics": False,
        "target_scoring_labels_loaded": False,
        "helper_sha256": HELPER_SHA256,
        "helper_tip": HELPER_TIP,
        "alex_preflight_go": "686ce4dc",
        "seasons": list(DEV_SEASONS),
        "weeks": "2-18",
        "split": "DEV",
        "n_targets": len(targets),
        "n_complete_27": len(complete),
        "n_partial": len(partial),
        "n_refused": len(refused),
        "n_cells": len(matrix),
        "complete_game_ids": complete,
        "partial": partial,
        "refused": refused,
        "identities": identities,
        "matrix": matrix,
        "status_counts": dict(status_counts),
        "pbp_sha_by_season": dict(pbp_sha_by_season),
        "games_sha256": GAMES_SHA256,
        "outcomes_prior_only_sha256": OUTCOMES_SHA256,
        "publication_timestamp_status": "unverified",
        "observation_timestamp_status": "unverified",
        "production_causal_claim": False,
        "realtime_source_availability_claim": False,
    }
    payload["matrix_sha256"] = sha256_text(
        json.dumps(matrix, sort_keys=True, separators=(",", ":"), default=str)
    )
    payload["identities_sha256"] = sha256_text(
        json.dumps(identities, sort_keys=True, separators=(",", ":"), default=str)
    )
    _assert_no_forbidden(
        {k: v for k, v in payload.items() if k not in {"matrix", "identities"}}
    )
    return payload


def compare_no_bye_to_exact_week(
    identities: Sequence[Mapping[str, Any]],
    last_played_matrix: Sequence[Mapping[str, Any]],
    exact_week_csv: Path,
) -> dict[str, Any]:
    """No-bye last-played T4 values must match frozen exact-week reconstructed_value."""
    no_bye = {
        row["game_id"]
        for row in identities
        if row.get("no_bye_both_sides")
    }
    exact: dict[tuple[str, str], str] = {}
    with Path(exact_week_csv).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["field"] in T4_FIELDS and row["game_id"] in no_bye:
                exact[(row["game_id"], row["field"])] = row.get("reconstructed_value", "")
    mismatches: list[dict[str, Any]] = []
    compared = 0
    skipped_missing_exact = 0
    for row in last_played_matrix:
        key = (row["game_id"], row["field"])
        if row["field"] not in T4_FIELDS or row["game_id"] not in no_bye:
            continue
        prior = exact.get(key)
        if prior is None or prior == "":
            skipped_missing_exact += 1
            continue
        compared += 1
        got = str(row.get("reconstructed_value", ""))
        if got != prior:
            try:
                same = float(got) == float(prior)
            except (TypeError, ValueError):
                same = False
            if not same:
                mismatches.append(
                    {
                        "game_id": row["game_id"],
                        "field": row["field"],
                        "last_played": got,
                        "exact_week": prior,
                    }
                )
    return {
        "n_no_bye_games": len(no_bye),
        "n_t4_compared": compared,
        "n_skipped_missing_or_partial_exact": skipped_missing_exact,
        "n_mismatches": len(mismatches),
        "mismatches": mismatches[:20],
        "pass": len(mismatches) == 0,
        "exact_week_csv": str(exact_week_csv),
        "exact_week_csv_sha256": sha256_file(Path(exact_week_csv)),
    }


def classify_2021_previous_partials(
    previous_ids: Sequence[str],
    *,
    complete: Sequence[str],
    partial: Sequence[Mapping[str, Any]],
    refused: Sequence[Mapping[str, Any]],
    identities: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    complete_set = set(complete)
    partial_by = {row["game_id"]: row for row in partial}
    refused_by = {row["game_id"]: row for row in refused}
    ident_by = {row["game_id"]: row for row in identities}
    now_complete: list[dict[str, Any]] = []
    still: list[dict[str, Any]] = []
    for gid in previous_ids:
        if gid in complete_set:
            ident = ident_by[gid]
            now_complete.append(
                {
                    "game_id": gid,
                    "status": "COMPLETE_27",
                    "selected_rating_week_home": ident["selected_rating_week_home"],
                    "selected_rating_week_away": ident["selected_rating_week_away"],
                    "t1_home": ident["t1_home"],
                    "t1_away": ident["t1_away"],
                    "consumed_game_ids_home": ident["consumed_game_ids_home"],
                    "consumed_game_ids_away": ident["consumed_game_ids_away"],
                }
            )
            continue
        if gid in partial_by:
            still.append({"game_id": gid, "status": "STILL_PARTIAL", **partial_by[gid]})
        elif gid in refused_by:
            still.append({"game_id": gid, "status": "STILL_REFUSED", **refused_by[gid]})
        else:
            still.append({"game_id": gid, "status": "NOT_IN_SLATE"})
    return {
        "n_previous_partial": len(previous_ids),
        "n_now_complete": len(now_complete),
        "n_still_refused_or_partial": len(still),
        "now_complete": now_complete,
        "still_refused_or_partial": still,
    }
