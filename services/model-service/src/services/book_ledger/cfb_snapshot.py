"""CFB slate snapshot → The Book rows (pending)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import requests

from src.services.book_ledger.cfb_trusted_market import trust_cfb_market
from src.services.book_ledger.ids import normalize_posted_at, units_for_type
from src.services.book_ledger.schema import BookRow
from src.services.book_ledger.store import BookStore, get_store
from src.services.cfb_season_engine.cfb_kei import apply_cfb_kei, tag_from_edge

log = logging.getLogger("kosedge.book_ledger.cfb")

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
_ENGINE_DATA = _SERVICE_ROOT / "src" / "services" / "cfb_season_engine" / "data"
ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
)
ESPN_SUMMARY = (
    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary"
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_kick(kickoff: str) -> Optional[datetime]:
    s = str(kickoff or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_official_slate(season: int = 2026) -> Dict[str, Any]:
    path = _ENGINE_DATA / f"cfb_official_slate_{season}.json"
    return _load_json(path)


def load_kei_board(season: int = 2026) -> Dict[str, Any]:
    path = _ENGINE_DATA / f"cfb_kei_w0_w1_{season}.json"
    return _load_json(path)


def games_for_slate_date(slate: Dict[str, Any], slate_date: str) -> List[Dict[str, Any]]:
    return [
        g
        for g in (slate.get("games") or [])
        if str(g.get("kickoff") or "").startswith(slate_date)
    ]


def fetch_espn_markets(slate_date: str) -> Dict[str, Dict[str, Any]]:
    """Map ESPN event id → spread/total from DraftKings pickcenter/odds."""
    ymd = slate_date.replace("-", "")
    url = f"{ESPN_SCOREBOARD}?dates={ymd}&limit=100"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    events = resp.json().get("events") or []
    out: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        gid = str(ev.get("id") or "")
        comp = (ev.get("competitions") or [{}])[0]
        status = ((comp.get("status") or {}).get("type") or {})
        market = _extract_espn_odds(comp.get("odds") or [])
        if market.get("spread_home") is None:
            # Live/in-progress scoreboard often drops odds — pull summary pickcenter.
            market = fetch_espn_summary_market(gid) or market
        out[gid] = {
            **market,
            "state": status.get("state"),
            "status_name": status.get("name"),
            "source": market.get("source") or "espn_scoreboard",
        }
    return out


def fetch_espn_summary_market(game_id: str) -> Dict[str, Any]:
    try:
        resp = requests.get(f"{ESPN_SUMMARY}?event={game_id}", timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("espn summary failed game_id=%s err=%s", game_id, exc)
        return {}
    pick = data.get("pickcenter") or data.get("odds") or []
    market = _extract_espn_odds(pick if isinstance(pick, list) else [])
    if market:
        market["source"] = "espn_summary_pickcenter"
    return market


def _extract_espn_odds(odds_list: List[Mapping[str, Any]]) -> Dict[str, Any]:
    if not odds_list:
        return {}
    o = odds_list[0]
    provider = o.get("provider") if isinstance(o.get("provider"), Mapping) else {}
    spread = o.get("spread")
    try:
        spread_f = float(spread) if spread is not None else None
    except (TypeError, ValueError):
        spread_f = None
    ou = o.get("overUnder")
    try:
        ou_f = float(ou) if ou is not None else None
    except (TypeError, ValueError):
        ou_f = None
    home_odds = o.get("homeTeamOdds") if isinstance(o.get("homeTeamOdds"), Mapping) else {}
    price = home_odds.get("spreadOdds")
    try:
        price_f = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_f = None
    return {
        "spread_home": spread_f,
        "total": ou_f,
        "spread_price_home": price_f,
        "details": o.get("details"),
        "provider": provider.get("name") or "espn",
        "source": "espn",
        "book_count": 1,
    }


def _side_and_line_from_edge(
    *,
    kei_spread_home: Optional[float],
    market_spread_home: Optional[float],
    edge_pts: Optional[float],
) -> Tuple[str, Optional[float]]:
    """Pick home/away side from KEI edge; line is that side's market number."""
    if market_spread_home is None:
        return "home", None
    # edge_pts = market − kei (home convention). Positive ⇒ KEI likes home more.
    if edge_pts is not None and edge_pts < 0:
        # Prefer away
        return "away", -float(market_spread_home)
    return "home", float(market_spread_home)


def build_cfb_snapshot_rows(
    *,
    slate_date: str,
    season: int = 2026,
    posted_at: Optional[str] = None,
    actor: str = "book_snapshot",
    stake_flag: str = "paper",
    include_aug30_late: bool = False,
) -> Dict[str, Any]:
    now = _utc_now()
    posted = normalize_posted_at(posted_at or now.isoformat().replace("+00:00", "Z"))
    slate = load_official_slate(season)
    kei_board = load_kei_board(season)
    kei_by = {str(g.get("game_id")): g for g in (kei_board.get("games") or [])}

    games = games_for_slate_date(slate, slate_date)
    if include_aug30_late and slate_date == "2026-08-29":
        # MEM@UNLV tips 2026-08-30T02:00Z — same gameday slate window.
        games = games + games_for_slate_date(slate, "2026-08-30")

    try:
        markets = fetch_espn_markets(slate_date)
        if include_aug30_late and slate_date == "2026-08-29":
            markets.update(fetch_espn_markets("2026-08-30"))
    except Exception as exc:  # noqa: BLE001
        log.warning("espn markets fetch failed: %s", exc)
        markets = {}

    rows: List[BookRow] = []
    meta_games: List[Dict[str, Any]] = []

    for g in games:
        gid = str(g.get("game_id"))
        home = str(g.get("home") or "")
        away = str(g.get("away") or "")
        week = g.get("week")
        kick = str(g.get("kickoff") or "")
        kick_dt = _parse_kick(kick)
        late = bool(kick_dt and now >= kick_dt)
        post_timing = "after_open" if late else "pre_kick"

        packed = kei_by.get(gid) or {}
        packed_kei = packed.get("kei") if isinstance(packed.get("kei"), Mapping) else {}
        mkt = markets.get(gid) or {}
        raw_spread = mkt.get("spread_home")

        # Rebuild KEI edge vs trusted market (do not mutate packaged model).
        trust = trust_cfb_market(
            kei=packed_kei.get("kei_spread_home") or packed.get("kei_spread_home"),
            best=raw_spread,
            open_line=raw_spread,
            book_count=int(mkt.get("book_count") or 1),
        )
        trusted_mkt = trust["market"] if trust.get("trusted") else None

        proj = {
            "week": week,
            "model_spread_home": packed.get("model_spread_home")
            or packed_kei.get("model_spread_home"),
            "model_total": packed.get("model_total") or packed_kei.get("model_total"),
            "model_home_win_prob": packed.get("model_home_win_prob")
            or packed_kei.get("model_home_win_prob"),
        }
        fbs = bool(g.get("fbs_vs_fbs", True))
        fcs_home = bool(g.get("fcs_home"))
        fcs_away = bool(g.get("fcs_away"))
        kei_payload = apply_cfb_kei(
            proj,
            market_spread_home=trusted_mkt,
            fbs_vs_fbs=fbs,
            fcs_home=fcs_home,
            fcs_away=fcs_away,
        )
        # If no packaged KEI identity (FCS), force PASS.
        if packed_kei.get("kei_spread_home") is None and proj.get("model_spread_home") is None:
            kei_payload["tag"] = "PASS"
            kei_payload["edge_pts"] = None
            kei_payload["kei_spread_home"] = None

        tag = str(kei_payload.get("tag") or "PASS").upper()
        book_type = {"PLAY": "play", "LEAN": "lean"}.get(tag, "pass")

        side, line = _side_and_line_from_edge(
            kei_spread_home=kei_payload.get("kei_spread_home"),
            market_spread_home=raw_spread if raw_spread is not None else trusted_mkt,
            edge_pts=kei_payload.get("edge_pts"),
        )
        # Pass snapshots still freeze KEI+market; default side=home for silence grade.
        if book_type == "pass" and line is None and raw_spread is not None:
            side, line = "home", float(raw_spread)

        price = mkt.get("spread_price_home")
        row = BookRow(
            book_id="",  # filled by store
            sport="cfb",
            season=season,
            week_or_slate=slate_date,
            game_id=gid,
            home=home,
            away=away,
            type=book_type,
            market="spread",
            side=side,
            line=line,
            price=float(price) if price is not None else None,
            posted_at=posted,
            kei_at_post={
                "kei_spread_home": kei_payload.get("kei_spread_home"),
                "kei_total": kei_payload.get("kei_total"),
                "edge_pts": kei_payload.get("edge_pts"),
                "tag": tag,
                "kei_version": kei_payload.get("kei_version"),
                "trusted_market": trusted_mkt,
                "trust_reason": trust.get("reason"),
            },
            market_at_post={
                "spread_home": raw_spread,
                "total": mkt.get("total"),
                "details": mkt.get("details"),
                "provider": mkt.get("provider"),
                "book_count": mkt.get("book_count"),
            },
            market_source=str(mkt.get("source") or ("missing" if raw_spread is None else "espn")),
            units=units_for_type(book_type),
            result="pending",
            stake_flag=stake_flag,
            actor=actor,
            late_post=late,
            post_timing=post_timing,
            payload={
                "kickoff": kick,
                "week": week,
                "espn_status": mkt.get("status_name"),
                "espn_state": mkt.get("state"),
                "fbs_vs_fbs": fbs,
            },
        )
        rows.append(row)
        meta_games.append(
            {
                "game_id": gid,
                "away": away,
                "home": home,
                "kickoff": kick,
                "type": book_type,
                "tag": tag,
                "late_post": late,
                "post_timing": post_timing,
                "kei_spread_home": kei_payload.get("kei_spread_home"),
                "market_spread_home": raw_spread,
                "trusted_market": trusted_mkt,
                "edge_pts": kei_payload.get("edge_pts"),
                "trust_reason": trust.get("reason"),
            }
        )

    return {
        "slate_date": slate_date,
        "season": season,
        "posted_at": posted,
        "n_games": len(rows),
        "rows": rows,
        "games": meta_games,
    }


def snapshot_cfb_slate(
    *,
    slate_date: str,
    season: int = 2026,
    store: Optional[BookStore] = None,
    actor: str = "book_snapshot",
    stake_flag: str = "paper",
    include_aug30_late: bool = False,
    posted_at: Optional[str] = None,
) -> Dict[str, Any]:
    store = store or get_store()
    # Reuse first freeze timestamp for this slate so re-runs stay idempotent.
    artifact_path = store.root / f"cfb-{slate_date}.json"
    if posted_at is None and artifact_path.exists():
        try:
            prev = json.loads(artifact_path.read_text(encoding="utf-8"))
            if prev.get("posted_at"):
                posted_at = str(prev["posted_at"])
        except (OSError, json.JSONDecodeError, TypeError):
            posted_at = None
    built = build_cfb_snapshot_rows(
        slate_date=slate_date,
        season=season,
        posted_at=posted_at,
        actor=actor,
        stake_flag=stake_flag,
        include_aug30_late=include_aug30_late,
    )
    created = 0
    reused = 0
    persisted: List[Dict[str, Any]] = []
    for row in built["rows"]:
        res = store.snapshot(row)
        persisted.append(res["row"])
        if res.get("created"):
            created += 1
        else:
            reused += 1

    counts = {
        "games": built["n_games"],
        "play": sum(1 for r in persisted if r.get("type") == "play"),
        "lean": sum(1 for r in persisted if r.get("type") == "lean"),
        "pass": sum(1 for r in persisted if r.get("type") == "pass"),
        "late_post": sum(1 for r in persisted if r.get("late_post")),
        "created": created,
        "reused": reused,
    }
    artifact = {
        "ok": True,
        "sport": "cfb",
        "slate_date": slate_date,
        "season": season,
        "posted_at": built["posted_at"],
        "counts": counts,
        "primary_metric": "clv",
        "result": "pending",
        "games": built["games"],
        "book_ids": [r.get("book_id") for r in persisted],
        "abandon_note": (
            "Old plays/leans/unit tracker abandoned — The Book is the ledger SoT."
        ),
    }
    path = store.write_slate_artifact(sport="cfb", slate=slate_date, summary=artifact)
    artifact["artifact_path"] = str(path)
    return artifact
