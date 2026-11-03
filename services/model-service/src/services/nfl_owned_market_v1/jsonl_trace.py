"""Bounded 143 JSONL source/value/clock/export trace (CLEAR 92861). CERT=0.

Already-owned selected sources only:
  7834cbc7 MARKET_ARM_FREEZE.json#intersection.games[].quotes (187)
  7834cbc7 ADMISSIBLE_QUOTES_B1.jsonl rows whose game_id is in freeze selected 96
  CLOCK_LINEAGE_LEDGER_81759 44 mapped (game_id, book) + 23 proven events

No broad scan. No new API. No outcomes. No model. No historical ATS/ROI.
Does not mark freeze#limitations verified. owned_completion_claimed stays false.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    CERT,
    CLEAR_92861,
    CLEAR_92861_TICKET,
    PACKAGE,
    PIN_ADMISSIBLE_PATH,
    PIN_ADMISSIBLE_SHA256,
    PIN_CSV_PROVIDER_EVENT_N,
    PIN_CSV_SELECTED_N,
    PIN_FREEZE_PATH,
    PIN_FREEZE_SHA256,
    PIN_INTERSECTION_N,
    PIN_JSONL_143_PROJECTION_BYTES,
    PIN_JSONL_143_PROJECTION_PATH,
    PIN_JSONL_143_PROJECTION_SHA256,
    PIN_JSONL_UNKNOWN_N,
    PIN_LEDGER_81759_PATH,
    PIN_LEDGER_81759_SHA256,
    PIN_MISSING_N,
    PIN_OWNED_HISTORY,
    PIN_REG496_N,
    PIN_SELECTED_187,
)
from src.services.nfl_owned_market_v1.hashing import canonical_sha256, sha256_bytes
from src.services.nfl_owned_market_v1.identity_join import build_identity_ledger
from src.services.nfl_owned_market_v1.owned_readiness import git_root
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse

ALLOWED_SEASONS = frozenset({2020, 2021})
JSONL_SOURCE = "the-odds-api-historical-enterprise"
CSV_SOURCE_SUFFIX = "open_close/lines.csv"
FREEZE_LIMITATIONS_LOCATOR = f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#limitations"
CLOCK_ABSENT_FIELDS = (
    "request_date",
    "payload_timestamp",
    "previous_timestamp",
    "next_timestamp",
    "last_update",
    "market_last_update",
    "pulled_at",
    "available_at",
    "observed_at",
    "book_last_update",
)


def _git_show_bytes(root: Path, commit: str, rel: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{rel}"],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise OwnedMarketRefuse(f"git show {commit}:{rel} failed")
    return proc.stdout


def _verify_sha256(raw: bytes, expected: str, *, where: str) -> str:
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected:
        raise OwnedMarketRefuse(f"{where} sha256 {digest} != pinned {expected}")
    return digest


def load_freeze(repo_root: Path) -> tuple[dict[str, Any], str]:
    root = git_root(repo_root)
    raw = _git_show_bytes(root, PIN_OWNED_HISTORY, PIN_FREEZE_PATH)
    digest = _verify_sha256(raw, PIN_FREEZE_SHA256, where=PIN_FREEZE_PATH)
    return json.loads(raw.decode("utf-8")), digest


def verify_staged_143_projection(path: Path) -> bytes:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PIN_JSONL_143_PROJECTION_SHA256:
        raise OwnedMarketRefuse(
            f"{path} sha256 {digest} != pinned {PIN_JSONL_143_PROJECTION_SHA256}"
        )
    if len(raw) != PIN_JSONL_143_PROJECTION_BYTES:
        raise OwnedMarketRefuse(
            f"{path} bytes {len(raw)} != {PIN_JSONL_143_PROJECTION_BYTES}"
        )
    return raw


def _cross_check_staged_projection(
    repo_root: Path, bound: list[dict[str, Any]]
) -> dict[str, Any]:
    staged_path = repo_root / PIN_JSONL_143_PROJECTION_PATH
    doc = json.loads(verify_staged_143_projection(staged_path).decode("utf-8"))
    if int(doc.get("n_selected") or 0) != PIN_JSONL_UNKNOWN_N:
        raise OwnedMarketRefuse("staged 143 n_selected drifted")
    if int(doc.get("n_exact_unique") or 0) != PIN_JSONL_UNKNOWN_N:
        raise OwnedMarketRefuse("staged 143 n_exact_unique drifted")
    if int(doc.get("n_other") or 0) != 0:
        raise OwnedMarketRefuse("staged 143 n_other != 0")
    rows = doc.get("rows") or []
    if len(rows) != PIN_JSONL_UNKNOWN_N:
        raise OwnedMarketRefuse(f"staged 143 rows {len(rows)} != {PIN_JSONL_UNKNOWN_N}")
    ours = {(row["game_id"], row["book"]): row for row in bound}
    staged_pairs: set[tuple[str, str]] = set()
    clock_false = 0
    avail_false = 0
    for row in rows:
        key = (str(row.get("game_id")), str(row.get("book")))
        staged_pairs.add(key)
        hit = ours.get(key)
        if hit is None:
            raise OwnedMarketRefuse(f"staged pair {key} not in bound 143")
        evidence = row.get("evidence") or []
        if len(evidence) != 1:
            raise OwnedMarketRefuse(f"{key} staged evidence n={len(evidence)} != 1")
        values = evidence[0].get("selected_values") or {}
        if (
            hit["line"] != values.get("spread_home")
            or hit["price_home"] != values.get("price_home")
            or hit["price_away"] != values.get("price_away")
        ):
            raise OwnedMarketRefuse(f"{key} staged selected_values != bound freeze/ADMISSIBLE")
        if evidence[0].get("selected_captured_at") != hit["clocks"]["claimed_capture"]["value"]:
            raise OwnedMarketRefuse(f"{key} staged selected_captured_at != freeze captured_at")
        if row.get("clock_semantics_verified") is not False:
            raise OwnedMarketRefuse(f"{key} staged clock_semantics_verified drifted")
        if row.get("contemporaneous_model_availability_verified") is not False:
            raise OwnedMarketRefuse(f"{key} staged availability verified drifted")
        if int(row.get("n_exact_value_matches") or 0) != 1:
            raise OwnedMarketRefuse(f"{key} staged n_exact_value_matches != 1")
        clock_false += 1
        avail_false += 1
    if staged_pairs != set(ours):
        raise OwnedMarketRefuse("staged 143 pair set != bound 143")
    missing_raw: list[dict[str, Any]] = []
    for spec in doc.get("sources") or []:
        rel = str(spec.get("relative_source") or "")
        present = (repo_root / rel).is_file()
        missing_raw.append(
            {
                "claimed_sha256": spec.get("sha256"),
                "count_present_on_this_host": 1 if present else 0,
                "field": "source_file_sha256",
                "locator": rel,
                "status": "PRESENT" if present else "NOT_EVALUABLE",
                "reason": (
                    "raw snapshot JSONL present on this host"
                    if present
                    else "raw snapshot JSONL absent on this Cursor host and absent from 7834cbc7/HEAD; cannot recompute claimed source_file_sha256"
                ),
            }
        )
    if any(row["status"] != "NOT_EVALUABLE" for row in missing_raw):
        raise OwnedMarketRefuse("expected raw snapshot JSONL absent on this host")
    return {
        "clock_semantics_verified_n": 0,
        "clock_semantics_verified_false_n": clock_false,
        "contemporaneous_availability_verified_n": 0,
        "contemporaneous_availability_verified_false_n": avail_false,
        "n_exact_unique": PIN_JSONL_UNKNOWN_N,
        "n_other": 0,
        "path": PIN_JSONL_143_PROJECTION_PATH,
        "purpose": doc.get("purpose"),
        "raw_snapshot_files": missing_raw,
        "sha256": PIN_JSONL_143_PROJECTION_SHA256,
        "sha256_match": True,
        "value_pairs_match_bound_143": True,
    }


def load_admissible_selected(repo_root: Path, selected_ids: set[str]) -> tuple[list[dict[str, Any]], str]:
    root = git_root(repo_root)
    raw = _git_show_bytes(root, PIN_OWNED_HISTORY, PIN_ADMISSIBLE_PATH)
    digest = _verify_sha256(raw, PIN_ADMISSIBLE_SHA256, where=PIN_ADMISSIBLE_PATH)
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("game_id") in selected_ids:
            rows.append(row)
    return rows, digest


def _require_season(season: Any, *, where: str) -> int:
    value = int(season)
    if value not in ALLOWED_SEASONS:
        raise OwnedMarketRefuse(f"{where} season {value!r} not in {sorted(ALLOWED_SEASONS)}")
    return value


def _clock_not_evaluable(*, field: str, locator: str, n_present: int, n_scope: int, reason: str) -> dict[str, Any]:
    return {
        "count_present": n_present,
        "count_scope": n_scope,
        "field": field,
        "locator": locator,
        "reason": reason,
        "status": "NOT_EVALUABLE",
        "value": None,
    }


def _bind_unique_spread(
    quote: dict[str, Any], candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    gid = quote["game_id"]
    book = quote["book"]
    hits = [
        row
        for row in candidates
        if row.get("market") == "spread"
        and row.get("kickoff_utc") == quote.get("kickoff_utc")
        and row.get("spread_home") == quote.get("spread_home")
    ]
    if len(hits) != 1:
        raise OwnedMarketRefuse(
            f"{gid}/{book} unique spread bind failed: n={len(hits)} "
            f"(file={PIN_ADMISSIBLE_PATH} field=market+kickoff_utc+spread_home)"
        )
    row = hits[0]
    if row.get("price_home") is None or row.get("price_away") is None:
        raise OwnedMarketRefuse(
            f"{gid}/{book} ADMISSIBLE spread row missing price_home/price_away"
        )
    if row.get("captured_at") != quote.get("captured_at"):
        raise OwnedMarketRefuse(
            f"{gid}/{book} captured_at freeze != ADMISSIBLE unique spread row"
        )
    if row.get("source") != JSONL_SOURCE:
        raise OwnedMarketRefuse(f"{gid}/{book} ADMISSIBLE source {row.get('source')!r}")
    if row.get("snapshot_kind") != "enterprise_snapshot":
        raise OwnedMarketRefuse(
            f"{gid}/{book} snapshot_kind {row.get('snapshot_kind')!r} != enterprise_snapshot"
        )
    return row


def _quote_clocks(quote: dict[str, Any], admis: dict[str, Any]) -> dict[str, Any]:
    n = 1
    jsonl_locator = (
        f"{PIN_OWNED_HISTORY}:{PIN_ADMISSIBLE_PATH} "
        f"selected game_id+book spread row; freeze {PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}"
        f"#intersection.games[].quotes"
    )
    return {
        "availability": _clock_not_evaluable(
            field="contemporaneous_model_availability",
            locator=f"{jsonl_locator} field=observation_is_not_file_mtime",
            n_present=0,
            n_scope=n,
            reason=(
                "observation_is_not_file_mtime="
                f"{admis.get('observation_is_not_file_mtime')}; "
                "no contemporaneous availability stamp; pulled_at is CSV-download-only"
            ),
        ),
        "book_update": _clock_not_evaluable(
            field="book.last_update|market_last_updates[spreads].last_update",
            locator=f"{jsonl_locator} fields=last_update,market_last_update",
            n_present=0,
            n_scope=n,
            reason="JSONL freeze/ADMISSIBLE spread rows have no book-update stamp (CSV envelopes cover 44 only)",
        ),
        "claimed_capture": {
            "count_present": 1,
            "count_scope": 1,
            "field": "captured_at",
            "locator": f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#quotes.captured_at == ADMISSIBLE.captured_at",
            "reason": (
                "claimed capture field present and equal on freeze quote and unique "
                "ADMISSIBLE spread row; freeze#limitations publication/observation "
                "remain unverified; snapshot_kind=enterprise_snapshot (not open/close)"
            ),
            "status": "CLAIMED_FIELD_PRESENT_NOT_VERIFIED",
            "value": quote.get("captured_at"),
        },
        "download": _clock_not_evaluable(
            field="pulled_at",
            locator=f"{jsonl_locator} field=pulled_at",
            n_present=0,
            n_scope=n,
            reason="pulled_at absent on JSONL quotes (CSV envelopes only; 2026-08-18 retrieval is not JSONL download proof)",
        ),
        "provider": _clock_not_evaluable(
            field="payload_timestamp|previous_timestamp|next_timestamp",
            locator=f"{jsonl_locator} fields=payload_timestamp,previous_timestamp,next_timestamp",
            n_present=0,
            n_scope=n,
            reason="provider historical snapshot neighbor stamps exist only on CSV_CLOCK_METADATA 44 envelopes",
        ),
        "request": _clock_not_evaluable(
            field="request_date",
            locator=f"{jsonl_locator} field=request_date",
            n_present=0,
            n_scope=n,
            reason="request_date absent on JSONL freeze/ADMISSIBLE rows; CSV request clocks cover 44 only",
        ),
    }


def build_jsonl_trace_ledger(repo_root: Path) -> dict[str, Any]:
    freeze, freeze_sha = load_freeze(repo_root)
    limits = freeze.get("limitations") or {}
    if limits.get("publication_timestamp_status") != "unverified":
        raise OwnedMarketRefuse("freeze publication_timestamp_status drifted")
    if limits.get("observation_timestamp_status") != "unverified":
        raise OwnedMarketRefuse("freeze observation_timestamp_status drifted")

    inter = freeze.get("intersection") or {}
    selected_ids = [str(x) for x in (inter.get("game_ids") or [])]
    missing_ids = [str(x) for x in (inter.get("missing_game_ids") or [])]
    if len(selected_ids) != PIN_INTERSECTION_N:
        raise OwnedMarketRefuse(f"selected game_ids {len(selected_ids)} != {PIN_INTERSECTION_N}")
    if len(missing_ids) != PIN_MISSING_N:
        raise OwnedMarketRefuse(f"missing_game_ids {len(missing_ids)} != {PIN_MISSING_N}")
    if len(set(selected_ids) & set(missing_ids)) != 0:
        raise OwnedMarketRefuse("selected∩missing != 0")
    if len(set(selected_ids) | set(missing_ids)) != PIN_REG496_N:
        raise OwnedMarketRefuse("selected∪missing != 496")

    quotes: list[dict[str, Any]] = []
    for game in inter.get("games") or []:
        for quote in game.get("quotes") or []:
            _require_season(quote.get("season"), where=str(quote.get("game_id")))
            quotes.append(quote)
    if len(quotes) != PIN_SELECTED_187:
        raise OwnedMarketRefuse(f"freeze quotes {len(quotes)} != {PIN_SELECTED_187}")

    identity = build_identity_ledger(repo_root)
    if identity["n_44_mapped"] != PIN_CSV_SELECTED_N or identity["n_44_hold"] != 0:
        raise OwnedMarketRefuse("44 CSV identity mapping drifted")
    if identity["identity"]["n_proven"] != PIN_CSV_PROVIDER_EVENT_N:
        raise OwnedMarketRefuse("23 proven events drifted")
    committed = repo_root / PIN_LEDGER_81759_PATH
    committed_sha = hashlib.sha256(committed.read_bytes()).hexdigest()
    if committed_sha != PIN_LEDGER_81759_SHA256:
        raise OwnedMarketRefuse(
            f"{PIN_LEDGER_81759_PATH} sha256 {committed_sha} != pinned {PIN_LEDGER_81759_SHA256}"
        )

    mapped_pairs = {(row["game_id"], row["book"]) for row in identity["subset"]}
    if len(mapped_pairs) != PIN_CSV_SELECTED_N:
        raise OwnedMarketRefuse("mapped pair uniqueness drifted")

    csv_44 = [q for q in quotes if (q["game_id"], q["book"]) in mapped_pairs]
    jsonl_143 = [q for q in quotes if (q["game_id"], q["book"]) not in mapped_pairs]
    if len(csv_44) != PIN_CSV_SELECTED_N or len(jsonl_143) != PIN_JSONL_UNKNOWN_N:
        raise OwnedMarketRefuse(
            f"187 split drifted: csv={len(csv_44)} jsonl={len(jsonl_143)}"
        )
    if mapped_pairs - {(q["game_id"], q["book"]) for q in quotes}:
        raise OwnedMarketRefuse("mapped_not_in_quotes != 0")
    if any(CSV_SOURCE_SUFFIX not in str(q.get("source") or "") for q in csv_44):
        raise OwnedMarketRefuse("44 row source is not open_close CSV")
    if any(q.get("source") != JSONL_SOURCE for q in jsonl_143):
        raise OwnedMarketRefuse("143 row source is not enterprise JSONL")

    admis_rows, admis_sha = load_admissible_selected(repo_root, set(selected_ids))
    by_gb: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in admis_rows:
        by_gb[(row.get("game_id"), row.get("book"))].append(row)

    bound: list[dict[str, Any]] = []
    provenance_files: dict[str, int] = {}
    for quote in jsonl_143:
        for field in CLOCK_ABSENT_FIELDS:
            if quote.get(field) not in (None, "", [], {}):
                raise OwnedMarketRefuse(
                    f"{quote['game_id']}/{quote['book']} unexpected clock field {field}"
                )
        admis = _bind_unique_spread(quote, by_gb[(quote["game_id"], quote["book"])])
        season = _require_season(quote.get("season"), where=quote["game_id"])
        prov = str(admis.get("provenance") or quote.get("provenance") or "")
        if "snapshots-2022" in prov and season != 2021:
            raise OwnedMarketRefuse(
                f"{quote['game_id']} snapshots-2022 provenance with season={season}"
            )
        provenance_files[prov] = provenance_files.get(prov, 0) + 1
        bound.append(
            {
                "admissible_spread_row_sha256": canonical_sha256(admis),
                "book": quote["book"],
                "clocks": _quote_clocks(quote, admis),
                "csv_envelope": False,
                "freeze_quote_sha256": canonical_sha256(quote),
                "game_id": quote["game_id"],
                "identity_csv_mapped": False,
                "kickoff_utc": quote["kickoff_utc"],
                "line": quote["spread_home"],
                "line_status": "BOUND_UNIQUE_FREEZE_AND_ADMISSIBLE",
                "market": "spread",
                "observation_is_not_file_mtime": bool(
                    admis.get("observation_is_not_file_mtime")
                ),
                "price_away": admis["price_away"],
                "price_home": admis["price_home"],
                "price_status": "BOUND_UNIQUE_ADMISSIBLE_SPREAD_ROW",
                "provenance": prov,
                "quoted_home_margin": quote.get("home_margin"),
                "season": season,
                "side": "home",
                "snapshot_kind": admis.get("snapshot_kind"),
                "source": JSONL_SOURCE,
                "week": quote["week"],
            }
        )

    if len(bound) != PIN_JSONL_UNKNOWN_N:
        raise OwnedMarketRefuse(f"bound 143 drifted: {len(bound)}")

    n_claim = sum(
        1
        for row in bound
        if row["clocks"]["claimed_capture"]["status"]
        == "CLAIMED_FIELD_PRESENT_NOT_VERIFIED"
    )
    envelope_clocks = ("request", "provider", "book_update", "download", "availability")
    not_evaluable_counts = {
        name: sum(1 for row in bound if row["clocks"][name]["status"] == "NOT_EVALUABLE")
        for name in envelope_clocks
    }
    if n_claim != PIN_JSONL_UNKNOWN_N:
        raise OwnedMarketRefuse("claimed_capture count drifted")
    if any(v != PIN_JSONL_UNKNOWN_N for v in not_evaluable_counts.values()):
        raise OwnedMarketRefuse(f"NOT_EVALUABLE counts drifted: {not_evaluable_counts}")

    staged = _cross_check_staged_projection(repo_root, bound)

    unavailable = [
        {
            "count_present": 0,
            "count_scope": PIN_JSONL_UNKNOWN_N,
            "field": "request_date",
            "locator": f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#quotes + {PIN_ADMISSIBLE_PATH} selected spread rows",
            "status": "NOT_EVALUABLE",
        },
        {
            "count_present": 0,
            "count_scope": PIN_JSONL_UNKNOWN_N,
            "field": "payload_timestamp|previous_timestamp|next_timestamp",
            "locator": f"{PIN_OWNED_HISTORY}:{PIN_ADMISSIBLE_PATH} selected JSONL rows",
            "status": "NOT_EVALUABLE",
        },
        {
            "count_present": 0,
            "count_scope": PIN_JSONL_UNKNOWN_N,
            "field": "book.last_update|market_last_updates[spreads].last_update",
            "locator": f"{PIN_OWNED_HISTORY}:{PIN_ADMISSIBLE_PATH} selected JSONL rows",
            "status": "NOT_EVALUABLE",
        },
        {
            "count_present": 0,
            "count_scope": PIN_JSONL_UNKNOWN_N,
            "field": "pulled_at",
            "locator": f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#quotes + {PIN_ADMISSIBLE_PATH}",
            "status": "NOT_EVALUABLE",
        },
        {
            "count_present": 0,
            "count_scope": PIN_JSONL_UNKNOWN_N,
            "field": "contemporaneous_model_availability",
            "locator": f"{PIN_ADMISSIBLE_PATH}#observation_is_not_file_mtime + {FREEZE_LIMITATIONS_LOCATOR}",
            "status": "NOT_EVALUABLE",
        },
        {
            "count_present": PIN_JSONL_UNKNOWN_N,
            "count_scope": PIN_JSONL_UNKNOWN_N,
            "field": "publication_timestamp_status|observation_timestamp_status",
            "locator": FREEZE_LIMITATIONS_LOCATOR,
            "status": "HOLD_UNVERIFIED",
        },
        *[
            {
                "count_present": row["count_present_on_this_host"],
                "count_scope": 1,
                "field": row["field"],
                "locator": row["locator"],
                "status": row["status"],
            }
            for row in staged["raw_snapshot_files"]
        ],
    ]

    return {
        "admissible_selected_n": len(admis_rows),
        "admissible_sha256": admis_sha,
        "bound_143": bound,
        "cert": CERT,
        "claimed_capture_n": n_claim,
        "clear": CLEAR_92861,
        "clocks_summary": {
            "availability": "NOT_EVALUABLE",
            "book_update": "NOT_EVALUABLE",
            "claimed_capture": "CLAIMED_FIELD_PRESENT_NOT_VERIFIED",
            "download": "NOT_EVALUABLE",
            "not_evaluable_n": not_evaluable_counts,
            "provider": "NOT_EVALUABLE",
            "request": "NOT_EVALUABLE",
        },
        "freeze_limitations_marked_verified": False,
        "freeze_sha256": freeze_sha,
        "historical_economic_calculation": False,
        "identity_81759_sha256": committed_sha,
        "mapped_44_pairs": sorted(
            ({"book": book, "game_id": gid} for gid, book in mapped_pairs),
            key=lambda row: (row["game_id"], row["book"]),
        ),
        "missing_400_game_ids": sorted(missing_ids),
        "ntbb_k_implemented": False,
        "owned_completion_claimed": False,
        "package": PACKAGE,
        "preserved": {
            "n_44_mapped": PIN_CSV_SELECTED_N,
            "n_proven_events": PIN_CSV_PROVIDER_EVENT_N,
            "n_jsonl_unknown_attempted": PIN_JSONL_UNKNOWN_N,
        },
        "provenance_files": provenance_files,
        "reconcile": {
            "n_187": PIN_SELECTED_187,
            "n_44": PIN_CSV_SELECTED_N,
            "n_143": PIN_JSONL_UNKNOWN_N,
            "n_96": PIN_INTERSECTION_N,
            "n_400": PIN_MISSING_N,
            "n_496": PIN_REG496_N,
            "n_23": PIN_CSV_PROVIDER_EVENT_N,
            "eq_187_44_143": PIN_SELECTED_187 == PIN_CSV_SELECTED_N + PIN_JSONL_UNKNOWN_N,
            "eq_496_96_400": PIN_REG496_N == PIN_INTERSECTION_N + PIN_MISSING_N,
            "mapped_not_in_quotes": 0,
        },
        "scientific_hold": [
            "no outcome join",
            "no real forecast",
            "no ATS/ROI on historical 2020/21 quotes",
            "no invented clock_provenance",
            "freeze#limitations remain unverified",
            "envelope clocks on 143 are NOT_EVALUABLE",
            "claimed captured_at is not verified publication/observation",
            "NTBB-K not implemented",
        ],
        "selected_96_game_ids": sorted(selected_ids),
        "sources": {
            "admissible": f"{PIN_OWNED_HISTORY}:{PIN_ADMISSIBLE_PATH}",
            "freeze": f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}",
            "identity_ledger": PIN_LEDGER_81759_PATH,
            "staged_143_projection": PIN_JSONL_143_PROJECTION_PATH,
        },
        "staged_143_projection": staged,
        "status": "PARTIAL",
        "ticket": CLEAR_92861_TICKET,
        "unavailable": unavailable,
    }


def write_jsonl_trace_ledger(repo_root: Path) -> dict[str, Any]:
    ledger = build_jsonl_trace_ledger(repo_root)
    out = repo_root / "data/ops/nfl_owned_market_v1/CLOCK_LINEAGE_LEDGER_92861.json"
    text = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    raw = text.encode("utf-8")
    out.write_bytes(raw)
    return {
        "ledger": ledger,
        "path": str(out.relative_to(repo_root)),
        "sha256": sha256_bytes(raw),
    }
