"""Source-aware provider-event → freeze game_id join (IDENTITY 81759). CERT=0.

Namespaces differ: provider_event_id ≠ canonical NFL game_id.
Literal overlap 0 is expected and is not a failed join.

Join key: exact full-name → freeze source abbr + exact commence==kickoff
+ NFL season (month>=3) + REG membership on freeze selected games.
No time tolerance. No ambiguous LA/NY/Washington short-name fallback.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.services.nfl_owned_market_v1.clock_lineage import (
    FREEZE_LIMITATIONS_LOCATOR,
    build_clock_lineage_ledger,
)
from src.services.nfl_owned_market_v1.constants import (
    CERT,
    PACKAGE,
    PIN_ADMISSIBLE_PATH,
    PIN_CSV_PROVIDER_EVENT_N,
    PIN_CSV_PROVIDER_IDENTITIES_PATH,
    PIN_CSV_PROVIDER_IDENTITIES_SHA256,
    PIN_CSV_SELECTED_N,
    PIN_FREEZE_PATH,
    PIN_JSONL_UNKNOWN_N,
    PIN_OWNED_HISTORY,
)
from src.services.nfl_owned_market_v1.hashing import sha256_bytes
from src.services.nfl_owned_market_v1.owned_readiness import git_root
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse

# Exact provider full names only. Tokens are those on freeze/ADMISSIBLE
# selected records (LA=Rams, LAC=Chargers). Short "LA"/"NY"/"Washington" refused.
PROVIDER_FULL_TO_FREEZE_ABBR: dict[str, str] = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Football Team": "WAS",
}

AMBIGUOUS_SHORT_NAMES = frozenset(
    {"LA", "Los Angeles", "NY", "New York", "Washington", "LAR"}
)


def nfl_reg_season(iso_utc: str) -> int:
    text = iso_utc.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text).astimezone(timezone.utc)
    return dt.year if dt.month >= 3 else dt.year - 1


def verify_provider_identities(path: Path) -> bytes:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PIN_CSV_PROVIDER_IDENTITIES_SHA256:
        raise OwnedMarketRefuse(
            f"{path} sha256 {digest} != pinned {PIN_CSV_PROVIDER_IDENTITIES_SHA256}"
        )
    return raw


def _git_show_bytes(root: Path, commit: str, rel: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{rel}"],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise OwnedMarketRefuse(f"git show {commit}:{rel} failed")
    return proc.stdout


def _require_full_name(name: str, *, field: str) -> str:
    token = str(name or "").strip()
    if token in AMBIGUOUS_SHORT_NAMES:
        raise OwnedMarketRefuse(f"{field} ambiguous short name refused: {token!r}")
    abbr = PROVIDER_FULL_TO_FREEZE_ABBR.get(token)
    if abbr is None:
        raise OwnedMarketRefuse(f"{field} unmapped full name: {token!r}")
    return abbr


def load_freeze_identity_index(repo_root: Path) -> dict[tuple[Any, ...], set[str]]:
    root = git_root(repo_root)
    freeze = json.loads(_git_show_bytes(root, PIN_OWNED_HISTORY, PIN_FREEZE_PATH))
    selected = set(freeze["intersection"]["game_ids"])
    raw = _git_show_bytes(root, PIN_OWNED_HISTORY, PIN_ADMISSIBLE_PATH)
    index: dict[tuple[Any, ...], set[str]] = defaultdict(set)
    for line in raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        gid = row.get("game_id")
        if gid not in selected:
            continue
        key = (
            int(row["season"]),
            str(row["home_abbr"]),
            str(row["away_abbr"]),
            str(row["kickoff_utc"]),
        )
        index[key].add(str(gid))
    return index


def join_provider_events(repo_root: Path) -> dict[str, Any]:
    staged = repo_root / PIN_CSV_PROVIDER_IDENTITIES_PATH
    doc = json.loads(verify_provider_identities(staged).decode("utf-8"))
    rows = doc.get("rows") or []
    if len(rows) != PIN_CSV_PROVIDER_EVENT_N:
        raise OwnedMarketRefuse(f"provider events {len(rows)} != {PIN_CSV_PROVIDER_EVENT_N}")
    ids = [r.get("provider_event_id") for r in rows]
    if len(set(ids)) != len(ids):
        raise OwnedMarketRefuse("provider_event_id not unique in staged identities")

    index = load_freeze_identity_index(repo_root)
    proven: list[dict[str, Any]] = []
    holds: list[dict[str, Any]] = []
    used_gid: set[str] = set()
    used_eid: set[str] = set()

    for row in rows:
        eid = str(row.get("provider_event_id") or "")
        try:
            home = _require_full_name(row.get("provider_home_team"), field="provider_home_team")
            away = _require_full_name(row.get("provider_away_team"), field="provider_away_team")
        except OwnedMarketRefuse as exc:
            holds.append({"provider_event_id": eid, "status": "HOLD", "reason": str(exc)})
            continue
        kickoff = str(row.get("commence_time") or "")
        season = nfl_reg_season(kickoff)
        key = (season, home, away, kickoff)
        gids = index.get(key, set())
        if len(gids) == 0:
            holds.append(
                {
                    "provider_event_id": eid,
                    "status": "HOLD",
                    "reason": "no exact season+home+away+kickoff match on freeze selected REG games",
                    "join_key": {
                        "season": season,
                        "home_abbr": home,
                        "away_abbr": away,
                        "kickoff_utc": kickoff,
                    },
                }
            )
            continue
        if len(gids) > 1:
            holds.append(
                {
                    "provider_event_id": eid,
                    "status": "HOLD",
                    "reason": "ambiguous: multiple freeze game_ids for exact key",
                    "game_ids": sorted(gids),
                }
            )
            continue
        gid = next(iter(gids))
        if gid in used_gid or eid in used_eid:
            holds.append(
                {
                    "provider_event_id": eid,
                    "status": "HOLD",
                    "reason": "uniqueness violation",
                    "game_id": gid,
                }
            )
            continue
        used_gid.add(gid)
        used_eid.add(eid)
        proven.append(
            {
                "away_abbr": away,
                "game_id": gid,
                "home_abbr": home,
                "kickoff_utc": kickoff,
                "provider_away_team": row.get("provider_away_team"),
                "provider_event_id": eid,
                "provider_home_team": row.get("provider_home_team"),
                "season": season,
                "season_type": "REG",
                "source_file": row.get("source_file"),
                "source_sha256": row.get("source_sha256"),
                "status": "PROVEN",
            }
        )

    if len(used_gid) != len(used_eid):
        raise OwnedMarketRefuse("bijection broken")
    return {
        "holds": holds,
        "n_hold": len(holds),
        "n_proven": len(proven),
        "n_provider_events": PIN_CSV_PROVIDER_EVENT_N,
        "namespace_note": "provider_event_id and canonical game_id are different namespaces; literal overlap 0 is not a failed join",
        "proven": proven,
        "uniqueness": {
            "provider_event_ids_unique": len(used_eid) == len(proven),
            "game_ids_unique": len(used_gid) == len(proven),
            "bijection": len(used_eid) == len(used_gid) == len(proven),
            "time_tolerance_seconds": 0,
            "ambiguous_abbreviation_fallback": False,
        },
    }


def build_identity_ledger(repo_root: Path) -> dict[str, Any]:
    clock = build_clock_lineage_ledger(repo_root)
    joined = join_provider_events(repo_root)
    eid_to = {row["provider_event_id"]: row for row in joined["proven"]}
    subset = []
    n_mapped = 0
    n_hold = 0
    for row in clock["subset"]:
        hit = eid_to.get(row["event_id"])
        extra = dict(row)
        if hit:
            extra["identity_status"] = "PROVEN"
            extra["game_id"] = hit["game_id"]
            extra["season"] = hit["season"]
            extra["season_type"] = "REG"
            extra["home_abbr"] = hit["home_abbr"]
            extra["away_abbr"] = hit["away_abbr"]
            extra["kickoff_utc"] = hit["kickoff_utc"]
            n_mapped += 1
        else:
            extra["identity_status"] = "HOLD"
            extra["game_id"] = None
            hold = next(
                (h for h in joined["holds"] if h.get("provider_event_id") == row["event_id"]),
                {"reason": "provider event not proven to a freeze game_id"},
            )
            extra["hold_reason"] = hold.get("reason")
            n_hold += 1
        subset.append(extra)
    if n_mapped + n_hold != PIN_CSV_SELECTED_N:
        raise OwnedMarketRefuse("44 subset identity annotation length mismatch")

    identity_gaps: list[dict[str, Any]] = []
    if joined["n_hold"]:
        identity_gaps.append(
            {
                "field": "provider_event_id → freeze game_id",
                "locator": PIN_CSV_PROVIDER_IDENTITIES_PATH,
                "n": joined["n_hold"],
                "reason": "exact season+home+away+kickoff produced no unique freeze selected match",
                "status": "HOLD",
            }
        )
    if n_hold:
        identity_gaps.append(
            {
                "field": "44 CSV associations without freeze game_id",
                "locator": "CLOCK_LINEAGE_LEDGER subset identity_status=HOLD",
                "n": n_hold,
                "reason": "book rows inherit HOLD from unmapped provider events",
                "status": "HOLD",
            }
        )
    unresolved = list(clock["unresolved"]) + identity_gaps
    return {
        "cert": CERT,
        "clock_parent_n_selected": PIN_CSV_SELECTED_N,
        "freeze_limitations_marked_verified": False,
        "identity": joined,
        "n_44_hold": n_hold,
        "n_44_mapped": n_mapped,
        "n_jsonl_unknown_preserved": PIN_JSONL_UNKNOWN_N,
        "owned_completion_claimed": False,
        "package": PACKAGE,
        "provider_historical_timestamp_is_contemporaneous_model_availability": False,
        "provider_identities_path": PIN_CSV_PROVIDER_IDENTITIES_PATH,
        "provider_identities_sha256": PIN_CSV_PROVIDER_IDENTITIES_SHA256,
        "provider_identities_sha256_match": True,
        "remaining_field_reasons": clock["remaining_field_reasons"]
        + [
            {
                "n": joined["n_hold"],
                "object": "provider events without unique freeze game_id",
                "reason": "HOLD — exact key miss; no time tolerance applied",
            }
        ],
        "scientific_hold": clock["scientific_hold"]
        + ["identity success is not price/export lineage or causal availability"],
        "subset": subset,
        "ticket": "t5329u",
        "unresolved": unresolved,
    }


def write_identity_ledger(repo_root: Path) -> dict[str, Any]:
    ledger = build_identity_ledger(repo_root)
    out = repo_root / "data/ops/nfl_owned_market_v1/CLOCK_LINEAGE_LEDGER_81759.json"
    text = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    raw = text.encode("utf-8")
    out.write_bytes(raw)
    return {"ledger": ledger, "path": str(out.relative_to(repo_root)), "sha256": sha256_bytes(raw)}
