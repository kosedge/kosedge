"""2022 Odds-API / warehouse closing-line recovery + join audit.

Research only. Does not score frozen 1.40, does not recalibrate, does not
change cfb-qb-feature-v1 / MATCHUP_RESPONSE / production compose.

Close rule (already coded in odds_lake.reduce_open_close):
  last snapshot with captured_at strictly before kickoff; DraftKings then FanDuel.
  Open = first legal snap. Post-kick and same-timestamp-as-kickoff are dropped.

Join key: (game_date, normalize_name(home), normalize_name(away)).
Identity: cfb_warehouse.identity.resolve_team_code.
Conflicts are reason-coded; this module does not silently pick among them.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.identity import known_engine_codes, resolve_team_code
from src.services.cfb_warehouse.leakage import (
    LEAKAGE_RULE,
    assert_available_before_kickoff,
    is_available_before_kickoff,
)
from src.services.cfb_warehouse.odds_lake import (
    _adjacent_dates,
    join_key,
    normalize_name,
    reduce_open_close,
)
from src.services.cfb_warehouse.paths import HD_ODDS_CFB, REPO_ODDS_CFB, hd_mounted

_HERE = Path(__file__).resolve()
_MONOREPO = next(
    (
        p
        for p in _HERE.parents
        if (p / "apps" / "web").is_dir()
        and (p / "services" / "model-service").is_dir()
        and (p / "data" / "ops").is_dir()
    ),
    Path("/workspace"),
)

SEASON = 2022
TRAIN0_WEEKS = frozenset(range(1, 15))
TRAIN0_GATE = 700
LAKE_DATE_MIN = "2022-08-01"
LAKE_DATE_MAX = "2023-01-15"
STALE_HOURS = 48.0
BOOK_DISAGREE_PTS = 0.5
SDV_VS_LAKE_PTS = 0.5

# Documented 2026-08-13 warehouse export (not this VM).
DOCUMENTED = {
    "inventory": "data/ops/cfb-historical-warehouse-v1-20260812-inventory.json",
    "writeup": "data/ops/cfb-historical-warehouse-v1-20260812.md",
    "export_as_of": "2026-08-13",
    "source": "odds_snapshots postgres (the-odds-api-historical-enterprise)",
    "lake_rows_2022": 28322,
    "warehouse_games_2022": 900,
    "close_spread_2022": 838,
    "open_spread_2022": 717,
    "lake_primary_2022": 717,
    "fcs_flagged_2022": 119,
}

LAYER_A_2022 = (
    _MONOREPO
    / "services/model-service/src/services/cfb_season_engine/data/cfb_qb_layer_a"
    / "season_2022.json"
)
SDV_CACHE = _MONOREPO / "data/cfb/raw/sdv"

REASON = {
    "LAKE_NOT_MOUNTED": "owned 2022 snapshots-2022.parquet / postgres export not available",
    "NO_LAKE_MATCH": "no (date, home, away) lake key for this game",
    "NO_PREGAME_SNAP": "lake rows existed but none were strictly before kickoff",
    "POST_KICK_ONLY": "every lake snap was at/after kickoff",
    "IDENTITY_UNMAPPED_HOME": "home name/abbr did not resolve to an engine code",
    "IDENTITY_UNMAPPED_AWAY": "away name/abbr did not resolve to an engine code",
    "FCS_HOME": "home side is FCS / unmapped (espn:{id})",
    "FCS_AWAY": "away side is FCS / unmapped (espn:{id})",
    "FCS_BOTH": "both sides FCS / unmapped",
    "NO_ACTUAL": "final home/away scores missing",
    "WEEK_OUT_OF_TRAIN0": "week not in Train-0 window 1–14",
    "LAYER_A_MISSING_HOME": "home engine code absent from frozen 2022 Layer A",
    "LAYER_A_MISSING_AWAY": "away engine code absent from frozen 2022 Layer A",
    "DUPLICATE_GAME_ID": "same ESPN game_id appeared more than once",
    "CONFLICT_MULTI_GAME": "one lake key matched multiple warehouse games",
    "CONFLICT_MULTI_LAKE": "one game matched multiple distinct lake keys with disagreeing closes",
    "CONFLICT_DATE_SKEW": "both ±1 calendar-day lake keys exist; refused silent pick",
    "ORIENTATION_FLIP_CANDIDATE": "flipped home/away names exist on the same date; refused silent flip",
    "DATE_SKEW": "joined via unique ±1 calendar-day retry (UTC vs US evening)",
    "STALE_SPARSE": "single legal snap captured more than 48h before kickoff",
    "STALE_REPEATED_LINE": "identical close + captured_at reused across many events",
    "MISSING_KICKOFF": "kickoff timestamp unprovable; close rejected",
    "SEALED_YEAR": "row season is 2025+ (must not enter this recovery)",
    "SDV_FILL_ONLY": "no lake close; SDV espn_cfb_betting fill only",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _hours_before(kickoff: Any, captured: Any) -> Optional[float]:
    kick = _parse_dt(kickoff)
    cap = _parse_dt(captured)
    if kick is None or cap is None:
        return None
    return (kick - cap).total_seconds() / 3600.0


def _is_test_dsn(dsn: str) -> bool:
    text = (dsn or "").lower()
    return "localhost" in text or "127.0.0.1" in text or "/test" in text


def locate_lake_sources() -> Dict[str, Any]:
    """Find the owned 2022 Odds-API lake without inventing or live-densifying."""
    tried: List[Dict[str, Any]] = []
    hd_path = HD_ODDS_CFB / "snapshots-2022.parquet"
    repo_path = REPO_ODDS_CFB / "snapshots-2022.parquet"
    tried.append(
        {
            "id": "hd_parquet",
            "path": str(hd_path),
            "present": hd_path.is_file(),
            "hd_mounted": hd_mounted(),
            "provenance": "2026-08-13 warehouse export on /Volumes/KosEdgeData",
        }
    )
    monorepo_path = _MONOREPO / "data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet"
    tried.append(
        {
            "id": "repo_parquet",
            "path": str(repo_path),
            "present": repo_path.is_file(),
            "provenance": "gitignored data/cfb/warehouse/clean/odds_cfb fallback (paths.REPO_ODDS_CFB)",
        }
    )
    tried.append(
        {
            "id": "monorepo_parquet",
            "path": str(monorepo_path),
            "present": monorepo_path.is_file(),
            "provenance": "monorepo data/cfb/warehouse/clean/odds_cfb (this VM)",
        }
    )
    raw_dsn = (os.environ.get("DATABASE_URL") or "").strip()
    dsn_usable = bool(raw_dsn) and not _is_test_dsn(raw_dsn)
    tried.append(
        {
            "id": "postgres_export",
            "present": dsn_usable,
            "dsn_set": bool(raw_dsn),
            "dsn_usable": dsn_usable,
            "provenance": "odds_snapshots WHERE leagues.code='cfb' (export_odds_lake SQL)",
            "note": "LOCAL_DSN / test DSN are not used; no silent 127.0.0.1 hang",
        }
    )
    tried.append(
        {
            "id": "odds_api_live_historical",
            "present": False,
            "skipped": True,
            "reason": "do not burn The Odds API historical credits in this assignment",
        }
    )
    chosen = None
    for row in tried:
        if row.get("present") and not row.get("skipped"):
            chosen = row["id"]
            break
    return {
        "chosen": chosen,
        "mounted": chosen is not None,
        "tried": tried,
        "documented": DOCUMENTED,
        "timestamp_semantics": {
            "captured_at": "Odds API snapshot time persisted on ingest (UTC)",
            "open": "first legal pre-kick snap for preferred book/market",
            "intermediate": "legal snaps strictly between open and close",
            "close": "last legal pre-kick snap; same timestamp as kickoff is illegal",
            "available_at": "equals close_captured_at",
            "kickoff": "ESPN schedule game_date / start (warehouse games.kickoff)",
            "rule": LEAKAGE_RULE,
        },
    }


def load_lake_from_parquet(path: Path) -> List[Dict[str, Any]]:
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    return table.to_pylist()


def export_lake_from_postgres() -> List[Dict[str, Any]]:
    """Export CFB snaps and keep the 2022 window only. Requires a real DATABASE_URL."""
    from src.services.cfb_warehouse.odds_lake import export_odds_lake, load_odds_lake

    export_odds_lake(prefer_hd=False)
    return load_odds_lake(prefer_hd=False)


def filter_2022_lake(snaps: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in snaps:
        season = row.get("season")
        try:
            season_i = int(season) if season not in (None, "") else None
        except (TypeError, ValueError):
            season_i = None
        day = str(row.get("game_date") or "")[:10]
        if season_i == SEASON or (LAKE_DATE_MIN <= day <= LAKE_DATE_MAX):
            if season_i is not None and season_i >= 2025:
                continue
            out.append(dict(row))
    return out


def load_2022_lake() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    loc = locate_lake_sources()
    snaps: List[Dict[str, Any]] = []
    if loc["chosen"] == "hd_parquet":
        snaps = load_lake_from_parquet(HD_ODDS_CFB / "snapshots-2022.parquet")
    elif loc["chosen"] == "repo_parquet":
        snaps = load_lake_from_parquet(REPO_ODDS_CFB / "snapshots-2022.parquet")
    elif loc["chosen"] == "monorepo_parquet":
        snaps = load_lake_from_parquet(
            _MONOREPO / "data/cfb/warehouse/clean/odds_cfb/snapshots-2022.parquet"
        )
    elif loc["chosen"] == "postgres_export":
        snaps = export_lake_from_postgres()
    filtered = filter_2022_lake(snaps)
    loc["raw_rows_loaded"] = len(snaps)
    loc["raw_rows_2022_window"] = len(filtered)
    return filtered, loc


def load_layer_a_2022_codes() -> Tuple[set[str], Dict[str, Any]]:
    payload = json.loads(LAYER_A_2022.read_text(encoding="utf-8"))
    if int(payload.get("prediction_season") or 0) != SEASON:
        raise ValueError("frozen Layer A artifact is not 2022")
    if payload.get("qb_feature_contract_version") != "cfb-qb-feature-v1":
        raise ValueError("Layer A contract version drifted")
    teams = payload.get("teams") or {}
    return set(teams), {
        "n": len(teams),
        "contract": payload.get("qb_feature_contract_version"),
        "path": str(LAYER_A_2022.relative_to(_MONOREPO)),
        "as_of": payload.get("as_of"),
    }


def load_2022_game_universe(
    *,
    cache_dir: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    from src.services.cfb_warehouse.ingest import ingest_season

    cache = cache_dir or SDV_CACHE
    known = known_engine_codes()
    games, closes, _snaps, skipped = ingest_season(
        SEASON, cache_dir=cache, known=known
    )
    sealed = [g for g in games if int(g.get("season") or 0) >= 2025]
    if sealed:
        raise RuntimeError("2025+ leaked into 2022 game universe")
    return games, closes, {
        "n_games": len(games),
        "n_sdv_closes": len(closes),
        "skipped": skipped,
        "source": "sportsdataverse espn_cfb_betting + team_box + linescores + schedules",
        "cache_dir": str(cache),
    }


def _index_lake(
    lake_snaps: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    by_key: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in lake_snaps:
        by_key[join_key(row.get("game_date"), str(row.get("home") or ""), str(row.get("away") or ""))].append(
            dict(row)
        )
    return by_key


def _event_keys(lake_snaps: Sequence[Mapping[str, Any]]) -> List[Tuple[str, str, str]]:
    return sorted({join_key(r.get("game_date"), str(r.get("home") or ""), str(r.get("away") or "")) for r in lake_snaps})


def resolve_lake_snaps_for_game(
    game: Mapping[str, Any],
    by_key: Mapping[Tuple[str, str, str], Sequence[Mapping[str, Any]]],
) -> Dict[str, Any]:
    """Deterministic lake attach. Refuses silent conflict picks."""
    reasons: List[str] = []
    key = join_key(
        game.get("game_date"),
        str(game.get("home_name") or ""),
        str(game.get("away_name") or ""),
    )
    snaps = list(by_key.get(key) or [])
    match_kind = "exact" if snaps else None

    flipped = join_key(
        game.get("game_date"),
        str(game.get("away_name") or ""),
        str(game.get("home_name") or ""),
    )
    flipped_snaps = list(by_key.get(flipped) or []) if flipped != key else []
    if flipped_snaps and not snaps:
        reasons.append("ORIENTATION_FLIP_CANDIDATE")
        return {
            "snaps": [],
            "match_kind": None,
            "reasons": reasons,
            "lake_key": None,
            "flip_key": list(flipped),
        }

    if not snaps and game.get("game_date"):
        day = str(game.get("game_date"))[:10]
        hits = []
        for alt in _adjacent_dates(day):
            alt_key = (alt, key[1], key[2])
            if alt_key in by_key:
                hits.append(alt_key)
        if len(hits) > 1:
            reasons.append("CONFLICT_DATE_SKEW")
            return {
                "snaps": [],
                "match_kind": None,
                "reasons": reasons,
                "lake_key": None,
                "skew_keys": [list(h) for h in hits],
            }
        if len(hits) == 1:
            snaps = list(by_key[hits[0]])
            match_kind = "date_skew"
            reasons.append("DATE_SKEW")
            key = hits[0]

    if not snaps:
        reasons.append("NO_LAKE_MATCH")
        return {"snaps": [], "match_kind": None, "reasons": reasons, "lake_key": None}

    return {
        "snaps": snaps,
        "match_kind": match_kind,
        "reasons": reasons,
        "lake_key": list(key),
        "flip_present": bool(flipped_snaps),
    }


def _market_book_values(
    snaps: Sequence[Mapping[str, Any]],
    *,
    market: str,
    field: str,
    kickoff: Any,
    game_date: Any,
) -> Dict[str, Any]:
    legal = [
        row
        for row in snaps
        if str(row.get("market") or "") == market
        and is_available_before_kickoff(
            available_at=row.get("captured_at"),
            kickoff=kickoff,
            game_date=game_date,
        )
    ]
    by_book: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in legal:
        by_book[str(row.get("book") or "")].append(row)
    last_by_book = {}
    for book, rows in by_book.items():
        ordered = sorted(rows, key=lambda r: str(r.get("captured_at") or ""))
        last_by_book[book] = ordered[-1].get(field) if ordered else None
    return {"legal_n": len(legal), "last_by_book": last_by_book}


def classify_observation(snaps: Sequence[Mapping[str, Any]], reduced: Mapping[str, Any]) -> Dict[str, Any]:
    """Label opener / intermediate / close among legal snaps for the chosen book."""
    book = str(reduced.get("book") or "")
    legal = [
        r
        for r in snaps
        if str(r.get("book") or "") == book and str(r.get("market") or "") == "spread"
    ]
    ordered = sorted(legal, key=lambda r: str(r.get("captured_at") or ""))
    n = len(ordered)
    return {
        "book": book,
        "n_book_snaps": n,
        "opener": str(ordered[0].get("captured_at")) if n else None,
        "closer": str(ordered[-1].get("captured_at")) if n else None,
        "n_intermediate": max(0, n - 2),
    }


def detect_stale_repeated(
    joined: Sequence[Mapping[str, Any]],
) -> Dict[str, int]:
    counts: Counter[Tuple[Any, Any]] = Counter()
    for row in joined:
        if row.get("close_source") != "odds_api_lake":
            continue
        counts[(row.get("close_spread_home"), row.get("close_captured_at"))] += 1
    flagged = 0
    for row in joined:
        key = (row.get("close_spread_home"), row.get("close_captured_at"))
        if counts.get(key, 0) >= 8 and row.get("close_source") == "odds_api_lake":
            reasons = list(row.get("reason_codes") or [])
            if "STALE_REPEATED_LINE" not in reasons:
                reasons.append("STALE_REPEATED_LINE")
                row["reason_codes"] = reasons  # type: ignore[index]
            flagged += 1
    return {"repeated_line_rows": flagged}


def _sdv_close_map(sdv_closes: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(c.get("game_id")): dict(c) for c in sdv_closes}


def join_2022_closes(
    games: Sequence[Mapping[str, Any]],
    sdv_closes: Sequence[Mapping[str, Any]],
    lake_snaps: Sequence[Mapping[str, Any]],
    *,
    layer_a_codes: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    layer_codes = set(layer_a_codes or [])
    by_key = _index_lake(lake_snaps)
    sdv_by_id = _sdv_close_map(sdv_closes)

    game_ids = [str(g.get("game_id") or "") for g in games]
    dup_ids = {gid for gid, n in Counter(game_ids).items() if gid and n > 1}

    key_to_games: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    attach_cache: Dict[str, Dict[str, Any]] = {}
    for game in games:
        attach = resolve_lake_snaps_for_game(game, by_key)
        attach_cache[str(game.get("game_id"))] = attach
        lake_key = attach.get("lake_key")
        if lake_key:
            key_to_games[tuple(lake_key)].append(str(game.get("game_id")))
    multi_game_keys = {k for k, ids in key_to_games.items() if len(set(ids)) > 1}

    joined: List[Dict[str, Any]] = []
    leakage_failures: List[Dict[str, Any]] = []
    orientation_failures: List[Dict[str, Any]] = []

    for game in games:
        gid = str(game.get("game_id") or "")
        reasons: List[str] = []
        week = int(game.get("week") or 0)
        season = int(game.get("season") or 0)
        if season >= 2025:
            reasons.append("SEALED_YEAR")

        home_id = str(game.get("home_team_id") or "")
        away_id = str(game.get("away_team_id") or "")
        fcs_home = bool(game.get("fcs_home"))
        fcs_away = bool(game.get("fcs_away"))
        if fcs_home and fcs_away:
            reasons.append("FCS_BOTH")
        elif fcs_home:
            reasons.append("FCS_HOME")
        elif fcs_away:
            reasons.append("FCS_AWAY")

        if not fcs_home and resolve_team_code(name=str(game.get("home_name") or ""), known_codes=known_engine_codes()) is None:
            if home_id.startswith("espn:"):
                reasons.append("IDENTITY_UNMAPPED_HOME")
        if not fcs_away and resolve_team_code(name=str(game.get("away_name") or ""), known_codes=known_engine_codes()) is None:
            if away_id.startswith("espn:"):
                reasons.append("IDENTITY_UNMAPPED_AWAY")

        if gid in dup_ids:
            reasons.append("DUPLICATE_GAME_ID")

        hs, aws = game.get("home_score"), game.get("away_score")
        actual_ok = hs is not None and aws is not None
        if not actual_ok:
            reasons.append("NO_ACTUAL")

        if week not in TRAIN0_WEEKS:
            reasons.append("WEEK_OUT_OF_TRAIN0")

        if layer_codes:
            if (not fcs_home) and home_id not in layer_codes:
                reasons.append("LAYER_A_MISSING_HOME")
            if (not fcs_away) and away_id not in layer_codes:
                reasons.append("LAYER_A_MISSING_AWAY")

        attach = attach_cache[gid]
        reasons.extend(attach.get("reasons") or [])
        snaps = list(attach.get("snaps") or [])
        lake_key = attach.get("lake_key")
        if lake_key and tuple(lake_key) in multi_game_keys:
            reasons.append("CONFLICT_MULTI_GAME")
            snaps = []

        kickoff = game.get("kickoff")
        game_date = game.get("game_date")
        reduced: Dict[str, Any] = {}
        if snaps:
            post_only = bool(snaps) and not any(
                is_available_before_kickoff(
                    available_at=r.get("captured_at"),
                    kickoff=kickoff,
                    game_date=game_date,
                )
                for r in snaps
            )
            if not kickoff and not game_date:
                reasons.append("MISSING_KICKOFF")
            elif post_only:
                reasons.append("POST_KICK_ONLY")
            reduced = reduce_open_close(snaps, kickoff=kickoff, game_date=game_date)
            if snaps and not reduced and "POST_KICK_ONLY" not in reasons and "MISSING_KICKOFF" not in reasons:
                reasons.append("NO_PREGAME_SNAP")

        sdv = sdv_by_id.get(gid) or {}
        close_spread = reduced.get("close_spread_home")
        close_total = reduced.get("close_total")
        close_source = "odds_api_lake" if reduced else None
        if close_spread is None and sdv.get("close_spread_home") is not None:
            close_spread = sdv.get("close_spread_home")
            close_source = "sportsdataverse_espn_cfb_betting"
            reasons.append("SDV_FILL_ONLY")
        if close_total is None and sdv.get("close_total") is not None:
            close_total = sdv.get("close_total")
            if close_source is None:
                close_source = "sportsdataverse_espn_cfb_betting"
                if "SDV_FILL_ONLY" not in reasons:
                    reasons.append("SDV_FILL_ONLY")

        raw_lake_spread = None
        raw_lake_total = None
        if reduced:
            raw_lake_spread = reduced.get("close_spread_home")
            raw_lake_total = reduced.get("close_total")
            books = _market_book_values(
                snaps, market="spread", field="spread_home", kickoff=kickoff, game_date=game_date
            )
            last_by_book = books.get("last_by_book") or {}
            if (
                last_by_book.get("draftkings") is not None
                and last_by_book.get("fanduel") is not None
            ):
                try:
                    if abs(float(last_by_book["draftkings"]) - float(last_by_book["fanduel"])) > BOOK_DISAGREE_PTS:
                        # Preference is deterministic (DK). Record, do not drop.
                        reasons.append("BOOK_DISAGREE_INFORMATIONAL")
                except (TypeError, ValueError):
                    pass
            if reduced.get("close_captured_at"):
                hours = _hours_before(kickoff, reduced.get("close_captured_at"))
                if hours is not None and hours > STALE_HOURS and int(reduced.get("n_lake_snaps") or 0) <= 1:
                    reasons.append("STALE_SPARSE")
            if kickoff and reduced.get("close_captured_at"):
                try:
                    assert_available_before_kickoff(
                        available_at=reduced.get("close_captured_at"),
                        kickoff=kickoff,
                        game_date=game_date,
                        feature_name=f"lake_close:{gid}",
                    )
                except ValueError as exc:
                    leakage_failures.append({"game_id": gid, "error": str(exc)})
                    reasons.append("POST_KICK_ONLY")
                    close_spread = None
                    close_total = None
                    close_source = None

        if (
            raw_lake_spread is not None
            and sdv.get("close_spread_home") is not None
        ):
            try:
                if abs(float(raw_lake_spread) - float(sdv["close_spread_home"])) > SDV_VS_LAKE_PTS:
                    reasons.append("SDV_LAKE_SPREAD_DISAGREE")
            except (TypeError, ValueError):
                pass

        # Home-favorite convention: negative spread_home = home favored.
        if close_spread is not None:
            try:
                sp = float(close_spread)
                if actual_ok and abs(sp) >= 21:
                    # Extreme favorite should usually be the eventual winner; flag, don't drop.
                    home_won = int(hs) > int(aws)
                    if (sp < 0 and not home_won) or (sp > 0 and home_won):
                        orientation_failures.append(
                            {
                                "game_id": gid,
                                "close_spread_home": sp,
                                "home_score": hs,
                                "away_score": aws,
                                "note": "large favorite lost — possible but recorded",
                            }
                        )
            except (TypeError, ValueError):
                pass

        conflict = any(
            r in reasons
            for r in (
                "CONFLICT_MULTI_GAME",
                "CONFLICT_MULTI_LAKE",
                "CONFLICT_DATE_SKEW",
                "ORIENTATION_FLIP_CANDIDATE",
                "DUPLICATE_GAME_ID",
            )
        )
        valid_pregame = (
            close_spread is not None
            and close_source == "odds_api_lake"
            and not conflict
            and "POST_KICK_ONLY" not in reasons
            and "NO_PREGAME_SNAP" not in reasons
            and "MISSING_KICKOFF" not in reasons
        )
        identity_matched = (not fcs_home) and (not fcs_away) and home_id and away_id and home_id != away_id
        fbs_fbs = identity_matched and not home_id.startswith("espn:") and not away_id.startswith("espn:")
        layer_ok = (not layer_codes) or (
            home_id in layer_codes and away_id in layer_codes
        )
        train0 = (
            valid_pregame
            and fbs_fbs
            and actual_ok
            and week in TRAIN0_WEEKS
            and layer_ok
            and "SEALED_YEAR" not in reasons
            and not conflict
        )
        # Warehouse-style evaluation also allows documented SDV fill.
        train0_with_fill = (
            close_spread is not None
            and fbs_fbs
            and actual_ok
            and week in TRAIN0_WEEKS
            and layer_ok
            and "SEALED_YEAR" not in reasons
            and not conflict
            and "POST_KICK_ONLY" not in reasons
        )

        obs = classify_observation(snaps, reduced) if reduced else {}
        row = {
            "game_id": gid,
            "season": season,
            "week": week,
            "game_date": game.get("game_date"),
            "kickoff": kickoff,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_name_raw": game.get("home_name"),
            "away_name_raw": game.get("away_name"),
            "home_name_norm": normalize_name(str(game.get("home_name") or "")),
            "away_name_norm": normalize_name(str(game.get("away_name") or "")),
            "fcs_home": fcs_home,
            "fcs_away": fcs_away,
            "fbs_fbs": fbs_fbs,
            "home_score": hs,
            "away_score": aws,
            "actual_total": (int(hs) + int(aws)) if actual_ok else None,
            "actual_margin_home": (int(hs) - int(aws)) if actual_ok else None,
            "raw_sdv_spread": sdv.get("close_spread_home"),
            "raw_sdv_total": sdv.get("close_total"),
            "raw_lake_spread": raw_lake_spread,
            "raw_lake_total": raw_lake_total,
            "close_spread_home": close_spread,
            "close_total": close_total,
            "open_spread_home": reduced.get("open_spread_home"),
            "open_total": reduced.get("open_total"),
            "close_source": close_source,
            "book": reduced.get("book") or sdv.get("book"),
            "line_fidelity": reduced.get("line_fidelity") or sdv.get("line_fidelity"),
            "open_captured_at": reduced.get("open_captured_at"),
            "close_captured_at": reduced.get("close_captured_at"),
            "available_at": reduced.get("available_at") or reduced.get("close_captured_at"),
            "n_lake_snaps": reduced.get("n_lake_snaps") or 0,
            "match_kind": attach.get("match_kind"),
            "lake_key": lake_key,
            "observation": obs,
            "reason_codes": sorted(set(reasons)),
            "conflict": conflict,
            "valid_pregame_lake_close": valid_pregame,
            "identity_matched": identity_matched,
            "actual_available": actual_ok,
            "layer_a_both": layer_ok,
            "train0_lake": train0,
            "train0_lake_or_sdv_fill": train0_with_fill,
            "spread_available": close_spread is not None,
            "total_available": close_total is not None,
        }
        joined.append(row)

    detect_stale_repeated(joined)

    lake_events = _event_keys(lake_snaps)
    matched_keys = {
        tuple(r["lake_key"])
        for r in joined
        if r.get("lake_key")
    }
    unmatched_lake = [list(k) for k in lake_events if k not in matched_keys]

    def _count(pred) -> int:
        return sum(1 for r in joined if pred(r))

    reason_counts = Counter()
    for r in joined:
        reason_counts.update(r.get("reason_codes") or [])

    unmatched_games = [r for r in joined if not r.get("valid_pregame_lake_close")]
    unmatched_game_reasons = Counter()
    for r in unmatched_games:
        codes = [c for c in (r.get("reason_codes") or []) if c != "BOOK_DISAGREE_INFORMATIONAL"]
        unmatched_game_reasons.update(codes or ["NO_LAKE_MATCH"])

    funnel = {
        "raw_events": len(lake_events),
        "raw_snaps": len(lake_snaps),
        "valid_pregame_closes": _count(lambda r: r["valid_pregame_lake_close"]),
        "identity_matched": _count(
            lambda r: r["valid_pregame_lake_close"] and r["identity_matched"]
        ),
        "fbs_fbs": _count(lambda r: r["valid_pregame_lake_close"] and r["fbs_fbs"]),
        "actual_available": _count(
            lambda r: r["valid_pregame_lake_close"] and r["fbs_fbs"] and r["actual_available"]
        ),
        "close_actual_eval_universe_all_weeks": _count(
            lambda r: r["valid_pregame_lake_close"]
            and r["fbs_fbs"]
            and r["actual_available"]
            and r["layer_a_both"]
        ),
        "train0_close_actual_lake": _count(lambda r: r["train0_lake"]),
        "train0_close_actual_lake_or_sdv_fill": _count(lambda r: r["train0_lake_or_sdv_fill"]),
    }
    availability = {
        "spread_available_joined": _count(lambda r: r["spread_available"]),
        "total_available_joined": _count(lambda r: r["total_available"]),
        "spread_and_total": _count(lambda r: r["spread_available"] and r["total_available"]),
        "spread_only": _count(lambda r: r["spread_available"] and not r["total_available"]),
        "total_only": _count(lambda r: r["total_available"] and not r["spread_available"]),
        "train0_spread_lake": _count(lambda r: r["train0_lake"] and r["spread_available"]),
        "train0_total_lake": _count(
            lambda r: r["train0_lake"] and r["total_available"]
        ),
        "train0_spread_fill": _count(
            lambda r: r["train0_lake_or_sdv_fill"] and r["spread_available"]
        ),
        "train0_total_fill": _count(
            lambda r: r["train0_lake_or_sdv_fill"] and r["total_available"]
        ),
    }
    duplicates = {
        "duplicate_game_ids": len(dup_ids),
        "conflict_multi_game": _count(lambda r: "CONFLICT_MULTI_GAME" in r["reason_codes"]),
        "conflict_date_skew": _count(lambda r: "CONFLICT_DATE_SKEW" in r["reason_codes"]),
        "orientation_flip_candidates": _count(
            lambda r: "ORIENTATION_FLIP_CANDIDATE" in r["reason_codes"]
        ),
        "sdv_lake_spread_disagree": _count(
            lambda r: "SDV_LAKE_SPREAD_DISAGREE" in r["reason_codes"]
        ),
    }

    coverage = _source_coverage(lake_snaps, joined)
    samples = _representative_rows(joined)

    train0_n = funnel["train0_close_actual_lake"]
    train0_fill_n = funnel["train0_close_actual_lake_or_sdv_fill"]
    lake_mounted = bool(lake_snaps)
    gate_clears = lake_mounted and train0_n >= TRAIN0_GATE
    # Warehouse 838 definition includes SDV fill. Only honor fill for GO if lake is mounted.
    gate_clears_fill = lake_mounted and train0_fill_n >= TRAIN0_GATE

    decision = "GO TO FROZEN 1.40 SCORING" if (gate_clears or gate_clears_fill) else "STOP"
    return {
        "funnel": funnel,
        "availability": availability,
        "duplicates": duplicates,
        "reason_counts": dict(reason_counts),
        "unmatched_game_reason_counts": dict(unmatched_game_reasons),
        "unmatched_lake_events": len(unmatched_lake),
        "unmatched_lake_event_samples": unmatched_lake[:12],
        "fcs_exclusions": {
            "fcs_home": _count(lambda r: "FCS_HOME" in r["reason_codes"]),
            "fcs_away": _count(lambda r: "FCS_AWAY" in r["reason_codes"]),
            "fcs_both": _count(lambda r: "FCS_BOTH" in r["reason_codes"]),
            "fcs_any": _count(lambda r: r.get("fcs_home") or r.get("fcs_away")),
        },
        "leakage": {
            "rule": LEAKAGE_RULE,
            "failures": leakage_failures,
            "n_failures": len(leakage_failures),
            "ok": len(leakage_failures) == 0,
        },
        "orientation": {
            "convention": "negative close_spread_home = home favored",
            "large_favorite_losses": orientation_failures[:8],
            "n_large_favorite_losses": len(orientation_failures),
        },
        "coverage": coverage,
        "representative_rows": samples,
        "joined_n": len(joined),
        "sdv_fill_breakdown": {
            "sdv_rows_with_spread": _count(lambda r: r.get("raw_sdv_spread") is not None),
            "sdv_fbs_fbs": _count(
                lambda r: r.get("raw_sdv_spread") is not None and r.get("fbs_fbs")
            ),
            "sdv_fbs_fbs_w1_14_actual": _count(
                lambda r: r.get("raw_sdv_spread") is not None
                and r.get("fbs_fbs")
                and r.get("actual_available")
                and r.get("week") in TRAIN0_WEEKS
            ),
            "sdv_fbs_fbs_w1_14_actual_layer_a": _count(
                lambda r: r.get("train0_lake_or_sdv_fill")
            ),
            "sdv_fcs_any": _count(
                lambda r: r.get("raw_sdv_spread") is not None
                and (r.get("fcs_home") or r.get("fcs_away"))
            ),
        },
        "train0_n_lake": train0_n,
        "train0_n_lake_or_fill": train0_fill_n,
        "gate": TRAIN0_GATE,
        "lake_mounted": lake_mounted,
        "decision": decision,
        "score_frozen_140": False,
        "recalibrate": False,
        "joined": joined,
    }


def _source_coverage(
    lake_snaps: Sequence[Mapping[str, Any]],
    joined: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    dates = sorted({str(r.get("game_date") or "")[:10] for r in lake_snaps if r.get("game_date")})
    books = Counter(str(r.get("book") or "") for r in lake_snaps)
    sources = Counter(str(r.get("source") or "") for r in lake_snaps)
    captured = [_parse_dt(r.get("captured_at")) for r in lake_snaps]
    captured_ok = [d for d in captured if d is not None]
    return {
        "lake_date_min": dates[0] if dates else None,
        "lake_date_max": dates[-1] if dates else None,
        "n_distinct_lake_dates": len(dates),
        "books": dict(books),
        "sources": dict(sources),
        "captured_at_min": min(captured_ok).isoformat() if captured_ok else None,
        "captured_at_max": max(captured_ok).isoformat() if captured_ok else None,
        "joined_close_sources": dict(Counter(str(r.get("close_source") or "none") for r in joined)),
    }


def _representative_rows(joined: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    picks: List[Dict[str, Any]] = []
    wanted = [
        lambda r: r.get("train0_lake"),
        lambda r: r.get("train0_lake_or_sdv_fill") and r.get("close_source") == "sportsdataverse_espn_cfb_betting",
        lambda r: "FCS_AWAY" in (r.get("reason_codes") or []) or "FCS_HOME" in (r.get("reason_codes") or []),
        lambda r: "NO_LAKE_MATCH" in (r.get("reason_codes") or []),
        lambda r: "DATE_SKEW" in (r.get("reason_codes") or []),
        lambda r: "ORIENTATION_FLIP_CANDIDATE" in (r.get("reason_codes") or []),
    ]
    seen = set()
    for pred in wanted:
        for row in joined:
            if row["game_id"] in seen:
                continue
            if pred(row):
                picks.append(_sample_row(row))
                seen.add(row["game_id"])
                break
    for row in joined:
        if len(picks) >= 10:
            break
        if row["game_id"] not in seen and row.get("fbs_fbs"):
            picks.append(_sample_row(row))
            seen.add(row["game_id"])
    return picks


def _sample_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "game_id",
        "week",
        "game_date",
        "kickoff",
        "home_team_id",
        "away_team_id",
        "home_name_raw",
        "away_name_raw",
        "home_score",
        "away_score",
        "raw_sdv_spread",
        "raw_sdv_total",
        "raw_lake_spread",
        "raw_lake_total",
        "close_spread_home",
        "close_total",
        "open_spread_home",
        "close_source",
        "book",
        "close_captured_at",
        "n_lake_snaps",
        "match_kind",
        "reason_codes",
        "train0_lake",
        "train0_lake_or_sdv_fill",
        "fbs_fbs",
    )
    return {k: row.get(k) for k in keys}


def gate_memo(audit: Mapping[str, Any], loc: Mapping[str, Any]) -> Dict[str, Any]:
    train0 = int(audit.get("train0_n_lake") or 0)
    fill = int(audit.get("train0_n_lake_or_fill") or 0)
    mounted = bool(audit.get("lake_mounted"))
    documented = DOCUMENTED
    expected_if_mounted = None
    if documented["warehouse_games_2022"]:
        # Rough: 838/900 of warehouse games had a close; Train-0 actuals-only is measured separately.
        expected_if_mounted = {
            "documented_close_spread_all_2022": documented["close_spread_2022"],
            "documented_lake_primary": documented["lake_primary_2022"],
            "note": (
                "If the 2026-08-13 lake is remounted, warehouse coverage implies "
                "Train-0 close+actual is likely ≥700 (838/900 of 900 games had a close; "
                "Layer A actuals-only FBS–FBS W1–14 2022 = 780)."
            ),
        }
    retain_gate = {
        "recommendation": "RETAIN_CLOSE_ACTUAL_GATE",
        "do_not_switch_to_actuals_only": True,
        "why": [
            "The owned Odds-API lake is documented at 28,322 2022 snaps / 838 closes / 717 lake-primary.",
            "The miss on this VM is mount/export, not a proof that 2022 closes never existed.",
            "Actuals-only 2022 FBS–FBS W1–14 is already 780 — labels exist; the hole is the market tape.",
            "Switching the protocol to actuals-only would train 1.40 without the feature it is judged against.",
        ],
        "formal_actuals_only_would_require": (
            "an explicit protocol amendment; this recovery does not make that change"
        ),
    }
    return {
        "decision": audit.get("decision"),
        "train0_n_lake": train0,
        "train0_n_lake_or_fill": fill,
        "gate": TRAIN0_GATE,
        "lake_mounted": mounted,
        "locate": {k: loc.get(k) for k in ("chosen", "mounted", "tried", "documented") if k in loc},
        "expected_if_mounted": expected_if_mounted,
        "methodology": retain_gate,
        "next_if_go": "score frozen MATCHUP_RESPONSE=1.40 on this reconstructed universe; do not recalibrate yet",
        "next_if_stop": "remount /Volumes/KosEdgeData/clean/odds/cfb/snapshots-2022.parquet or export from the postgres that held the 2026-08-13 lake; do not live-densify; do not score",
        "score_frozen_140": False,
        "recalibrate": False,
        "opened_2025": False,
        "cfb_public": False,
        "play": False,
    }
