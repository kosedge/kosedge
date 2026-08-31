#!/usr/bin/env python3
"""CFB grading harness — freeze desk publications, grade after kick.

Infrastructure only. Does not rewrite KEI, shrink, power, or tags.

Usage:
  python3 scripts/cfb/grade_harness.py seed
  python3 scripts/cfb/grade_harness.py summary
  python3 scripts/cfb/grade_harness.py fill-w0-results   # already in seed
  python3 scripts/cfb/grade_harness.py status
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "cfb_grades_2026.jsonl"
SCHEMA = ROOT / "docs" / "CFB_GRADE_SCHEMA.md"
CARD = ROOT / "data" / "ops" / "cfb-w1-handicap-card-20260831.json"
SLATE = ROOT / "apps" / "web" / "lib" / "data" / "cfb-official-slate-2026.json"
KEI_LINES = ROOT / "apps" / "web" / "data" / "processed" / "kei_lines_cfb.json"
KEI_RAW = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
    / "cfb_kei_w0_w1_2026.json"
)
SUMMARY_MD = ROOT / "data" / "ops" / "cfb-grades-summary-2026.md"
SUMMARY_JSON = ROOT / "data" / "ops" / "cfb-grades-summary-2026.json"

SEASON = 2026
CARD_STAMP = "2026-08-31T21:38Z"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_rows(path: Path = STORE) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _append_rows(rows: Iterable[Dict[str, Any]], path: Path = STORE) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


def _row_key(r: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        r.get("season"),
        r.get("week"),
        r.get("game_id") or f"{r.get('away')}@{r.get('home')}",
        r.get("market"),
    )


def _wp_bucket(wp: Optional[float]) -> Optional[str]:
    if wp is None:
        return None
    try:
        p = float(wp)
    except (TypeError, ValueError):
        return None
    if p >= 0.90 or p <= 0.10:
        return "cupcake"
    if 0.45 <= p <= 0.55:
        return "tossup"
    if 0.60 <= p < 0.90 or 0.10 < p <= 0.40:
        return "fav_60_75"
    return "other"


def _size_note(
    *,
    market: str,
    best_kick: Optional[float],
    wp: Optional[float],
) -> Optional[str]:
    fat = False
    if market == "spread" and best_kick is not None and abs(float(best_kick)) >= 28:
        fat = True
    if wp is not None and (float(wp) >= 0.90 or float(wp) <= 0.10):
        fat = True
    return "fat-dog" if fat else None


def _parse_best_cell(best: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """Parse card Best cell → (away_signed_or_total, book, toward_token).

    Spreads look like: ``BALL +50.5 (FanDuel)``
    Totals look like: ``51.5 (DraftKings)``
    """
    if not best or best.strip() in {"—", "-", "n/a"}:
        return None, None, None
    s = best.strip()
    book = None
    m_book = re.search(r"\(([^)]+)\)\s*$", s)
    if m_book:
        book = m_book.group(1).strip()
        s = s[: m_book.start()].strip()
    # "BALL +50.5" or "+50.5" or "51.5" or "Over 57.0"
    m = re.match(
        r"^(?:(?P<side>[A-Za-z0-9\-]+)\s+)?(?P<num>[+\-]?\d+(?:\.\d+)?)$",
        s,
    )
    if not m:
        m2 = re.search(r"([+\-]?\d+(?:\.\d+)?)", s)
        if not m2:
            return None, book, None
        return float(m2.group(1)), book, None
    num = float(m.group("num"))
    side = m.group("side")
    return num, book, side


def _ats_spread_vs_line(final_home: int, final_away: int, line_home: float) -> str:
    """Did the home team cover the home-signed line?"""
    margin = final_home - final_away
    # Home covers when margin + line > 0 (line negative for home fav).
    diff = margin + float(line_home)
    if abs(diff) < 1e-9:
        return "push"
    return "cover" if diff > 0 else "miss"


def _ats_total_vs_line(final_home: int, final_away: int, line: float) -> str:
    total = final_home + final_away
    diff = total - float(line)
    if abs(diff) < 1e-9:
        return "push"
    return "cover" if diff > 0 else "miss"


def _signed_error_spread(final_home: int, final_away: int, kei: float) -> float:
    return float((final_home - final_away) + kei)


def _signed_error_total(final_home: int, final_away: int, kei: float) -> float:
    return float((final_home + final_away) - kei)


def _base_row(**kwargs: Any) -> Dict[str, Any]:
    row = {
        "season": SEASON,
        "week": None,
        "game_id": None,
        "home": None,
        "away": None,
        "market": None,
        "kei": None,
        "model_kei": None,
        "open": None,
        "best_kick": None,
        "book": None,
        "trusted": None,
        "tag": None,
        "size_note": None,
        "close": None,
        "final_home": None,
        "final_away": None,
        "ats_vs_kei": None,
        "ats_vs_tag": None,
        "clv": None,
        "signed_error_kei": None,
        "wp_bucket": None,
        "card_stamp": None,
        "source": None,
        "recorded_at": _utc_now(),
        "edge_str": None,
        "tag_side": None,
    }
    row.update(kwargs)
    return row


def _kei_index() -> Dict[Tuple[str, str, int], Dict[str, Any]]:
    """(away, home, week) → kei_lines row."""
    out: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
    if KEI_LINES.exists():
        blob = _load_json(KEI_LINES)
        for g in blob.get("games") or []:
            key = (g.get("awayAbbr"), g.get("homeAbbr"), int(g.get("week")))
            out[key] = g
    return out


def _kei_raw_index() -> Dict[Tuple[str, str, int], Dict[str, Any]]:
    out: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
    if KEI_RAW.exists():
        blob = _load_json(KEI_RAW)
        for g in blob.get("games") or []:
            key = (g.get("away"), g.get("home"), int(g.get("week")))
            out[key] = g
    return out


def _slate_index() -> Dict[Tuple[str, str, int], Dict[str, Any]]:
    out: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
    slate = _load_json(SLATE)
    for g in slate.get("games") or []:
        home = str(g.get("home") or "").replace("fcs:", "")
        away = str(g.get("away") or "").replace("fcs:", "")
        key = (away, home, int(g.get("week")))
        out[key] = g
    return out


def build_w0_rows() -> List[Dict[str, Any]]:
    slate = _slate_index()
    kei_lines = _kei_index()
    kei_raw = _kei_raw_index()
    rows: List[Dict[str, Any]] = []
    w0_games = [
        g
        for g in _load_json(SLATE).get("games") or []
        if int(g.get("week", -1)) == 0 and g.get("fbs_vs_fbs")
    ]
    assert len(w0_games) == 6, f"expected 6 W0 FBS–FBS, got {len(w0_games)}"

    for g in w0_games:
        home = str(g["home"]).replace("fcs:", "")
        away = str(g["away"]).replace("fcs:", "")
        game_id = g.get("game_id")
        final_home = g.get("home_score")
        final_away = g.get("away_score")
        assert g.get("status") == "final"
        assert final_home is not None and final_away is not None

        kl = kei_lines.get((away, home, 0)) or {}
        kr = kei_raw.get((away, home, 0)) or {}
        kobj = kr.get("kei") or {}

        kei_spread = (
            kobj.get("kei_spread_home")
            if kobj.get("kei_spread_home") is not None
            else kl.get("handicapSpreadHome")
        )
        model_spread = (
            kobj.get("model_spread_home")
            if kobj.get("model_spread_home") is not None
            else kl.get("modelSpreadHome")
        )
        kei_total = (
            kobj.get("kei_total")
            if kobj.get("kei_total") is not None
            else kl.get("handicapTotal") or kl.get("modelTotal") or kr.get("model_total")
        )
        model_total = kl.get("modelTotal") or kr.get("model_total") or kei_total
        wp = (
            kobj.get("kei_home_win_prob")
            if kobj.get("kei_home_win_prob") is not None
            else kl.get("handicapHomeWinProb") or kl.get("modelHomeWinProb")
        )

        # Spread row
        spread = _base_row(
            week=0,
            game_id=str(game_id) if game_id else None,
            home=home,
            away=away,
            market="spread",
            kei=kei_spread,
            model_kei=model_spread,
            open=None,
            best_kick=None,
            book=None,
            trusted=None,
            tag="n/a",
            size_note=None,
            final_home=int(final_home),
            final_away=int(final_away),
            wp_bucket=_wp_bucket(wp),
            source="w0_published",
            card_stamp=None,
        )
        if kei_spread is not None:
            spread["ats_vs_kei"] = _ats_spread_vs_line(
                int(final_home), int(final_away), float(kei_spread)
            )
            spread["signed_error_kei"] = round(
                _signed_error_spread(int(final_home), int(final_away), float(kei_spread)),
                4,
            )
        rows.append(spread)

        # Total row
        total = _base_row(
            week=0,
            game_id=str(game_id) if game_id else None,
            home=home,
            away=away,
            market="total",
            kei=kei_total,
            model_kei=model_total,
            open=None,
            best_kick=None,
            book=None,
            trusted=None,
            tag="n/a",
            size_note=None,
            final_home=int(final_home),
            final_away=int(final_away),
            wp_bucket=_wp_bucket(wp),
            source="w0_published",
            card_stamp=None,
        )
        if kei_total is not None:
            total["ats_vs_kei"] = _ats_total_vs_line(
                int(final_home), int(final_away), float(kei_total)
            )
            total["signed_error_kei"] = round(
                _signed_error_total(int(final_home), int(final_away), float(kei_total)),
                4,
            )
        rows.append(total)

    return rows


def build_w1_rows_from_card() -> List[Dict[str, Any]]:
    card = _load_json(CARD)
    assert card.get("sheet_ts") == CARD_STAMP, card.get("sheet_ts")
    slate = _slate_index()
    kei_lines = _kei_index()
    rows: List[Dict[str, Any]] = []

    def game_parts(game: str) -> Tuple[str, str]:
        away, home = game.split("@", 1)
        return away.strip(), home.strip()

    for r in card.get("spreads") or []:
        away, home = game_parts(r["game"])
        sg = slate.get((away, home, 1)) or {}
        kl = kei_lines.get((away, home, 1)) or {}
        best_away, book, tag_side = _parse_best_cell(str(r.get("best") or ""))
        best_home = -best_away if best_away is not None else None
        kei = r.get("kei")
        if kei is None:
            kei = kl.get("handicapSpreadHome")
        model = kl.get("modelSpreadHome")
        wp = r.get("wp")
        if wp is None:
            wp = kl.get("handicapHomeWinProb") or kl.get("modelHomeWinProb")
        trusted = r.get("trusted")
        tag = r.get("tag") or "PASS"
        rows.append(
            _base_row(
                week=1,
                game_id=str(sg.get("game_id") or kl.get("id") or "") or None,
                home=home,
                away=away,
                market="spread",
                kei=kei,
                model_kei=model,
                open=None,
                best_kick=best_home,
                book=book,
                trusted=bool(trusted) if trusted is not None else None,
                tag=tag,
                size_note=_size_note(market="spread", best_kick=best_home, wp=wp),
                wp_bucket=_wp_bucket(wp),
                source="w1_card_20260831",
                card_stamp=CARD_STAMP,
                edge_str=r.get("edge_str"),
                tag_side=tag_side,
            )
        )

    for r in card.get("totals") or []:
        away, home = game_parts(r["game"])
        sg = slate.get((away, home, 1)) or {}
        kl = kei_lines.get((away, home, 1)) or {}
        best_tot, book, _ = _parse_best_cell(str(r.get("best") or ""))
        kei = r.get("kei")
        if kei is None:
            kei = kl.get("handicapTotal") or kl.get("modelTotal")
        model = kl.get("modelTotal")
        wp = kl.get("handicapHomeWinProb") or kl.get("modelHomeWinProb")
        tag = r.get("tag") or "PASS"
        # Totals: size_note only from cupcake WP (no |mkt|≥28 on totals).
        rows.append(
            _base_row(
                week=1,
                game_id=str(sg.get("game_id") or kl.get("id") or "") or None,
                home=home,
                away=away,
                market="total",
                kei=kei,
                model_kei=model,
                open=None,
                best_kick=best_tot,
                book=book,
                trusted=True if best_tot is not None else False,
                tag=tag,
                size_note=_size_note(market="total", best_kick=None, wp=wp),
                wp_bucket=_wp_bucket(wp),
                source="w1_card_20260831",
                card_stamp=CARD_STAMP,
                edge_str=r.get("edge_str"),
                tag_side=None,
            )
        )

    return rows


def cmd_seed(*, force: bool = False) -> int:
    if not SCHEMA.exists():
        print(f"missing schema: {SCHEMA}", file=sys.stderr)
        return 2
    if STORE.exists() and STORE.stat().st_size > 0 and not force:
        print(f"store already seeded: {STORE} ({STORE.stat().st_size} bytes)")
        print("re-run with --force to wipe and reseed (append-only contract: prefer not to)")
        return 0

    if force and STORE.exists():
        STORE.unlink()

    # Touch empty store first (checklist step 1).
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text("", encoding="utf-8")

    w0 = build_w0_rows()
    w1 = build_w1_rows_from_card()
    n0 = _append_rows(w0)
    n1 = _append_rows(w1)
    rows = _read_rows()
    print("=== CFB grade harness seed ===")
    print(f"schema:  {SCHEMA}")
    print(f"store:   {STORE}")
    print(f"w0 rows: {n0} (6 games × spread+total)")
    print(f"w1 rows: {n1} (card sides+totals)")
    print(f"total:   {len(rows)}")
    tags = Counter((r.get("week"), r.get("market"), r.get("tag")) for r in rows)
    print("tag counts by (week, market, tag):")
    for k, v in sorted(tags.items()):
        print(f"  {k}: {v}")
    # Sanity: BALL@OSU PLAY
    ball = next(
        r
        for r in rows
        if r.get("away") == "BALL"
        and r.get("home") == "OSU"
        and r.get("market") == "spread"
    )
    print(
        f"BALL@OSU spread: kei={ball.get('kei')} best_kick={ball.get('best_kick')} "
        f"tag={ball.get('tag')} size_note={ball.get('size_note')}"
    )
    assert ball.get("tag") == "PLAY"
    assert abs(float(ball.get("kei")) - (-40.51)) < 1e-6
    assert ball.get("size_note") == "fat-dog"
    print("KEI files untouched (harness reads only).")
    return 0


def cmd_summary() -> int:
    rows = _read_rows()
    if not rows:
        print("empty store", file=sys.stderr)
        return 1

    by_week = Counter(r.get("week") for r in rows)
    by_market = Counter(r.get("market") for r in rows)
    by_tag = Counter(r.get("tag") for r in rows if r.get("week") == 1)

    w1_spreads = [
        r for r in rows if r.get("week") == 1 and r.get("market") == "spread"
    ]
    play_sides = [r for r in w1_spreads if r.get("tag") == "PLAY"]
    fat_plays = [r for r in play_sides if r.get("size_note") == "fat-dog"]

    # Graded subsets (have finals + ats)
    graded_kei = [r for r in rows if r.get("ats_vs_kei") in {"cover", "push", "miss"}]
    graded_tag = [r for r in rows if r.get("ats_vs_tag") in {"cover", "push", "miss"}]
    clvs = [float(r["clv"]) for r in rows if r.get("clv") is not None]
    errors = [
        float(r["signed_error_kei"])
        for r in rows
        if r.get("signed_error_kei") is not None
    ]

    def ats_rate(xs: List[Dict[str, Any]], field: str) -> Optional[float]:
        decided = [r for r in xs if r.get(field) in {"cover", "miss"}]
        if not decided:
            return None
        return sum(1 for r in decided if r.get(field) == "cover") / len(decided)

    err_by_bucket: Dict[str, List[float]] = {}
    for r in rows:
        if r.get("signed_error_kei") is None:
            continue
        b = r.get("wp_bucket") or "other"
        err_by_bucket.setdefault(b, []).append(float(r["signed_error_kei"]))

    summary = {
        "as_of": _utc_now(),
        "store": str(STORE.relative_to(ROOT)),
        "n_rows": len(rows),
        "by_week": dict(by_week),
        "by_market": dict(by_market),
        "w1_tags": dict(by_tag),
        "w1_play_sides": len(play_sides),
        "w1_fat_dog_play_sides": len(fat_plays),
        "n_ats_vs_kei_graded": len(graded_kei),
        "n_ats_vs_tag_graded": len(graded_tag),
        "ats_vs_kei_rate": ats_rate(graded_kei, "ats_vs_kei"),
        "ats_vs_tag_rate": ats_rate(graded_tag, "ats_vs_tag"),
        "mean_clv": (sum(clvs) / len(clvs)) if clvs else None,
        "n_clv": len(clvs),
        "mean_signed_error_kei": (sum(errors) / len(errors)) if errors else None,
        "n_signed_error": len(errors),
        "error_by_bucket": {
            k: {
                "n": len(v),
                "mean": (sum(v) / len(v)) if v else None,
            }
            for k, v in sorted(err_by_bucket.items())
        },
        "pre_registered_question": (
            "did tagged PLAY sides beat chance, and did fat-dog PLAY sides beat the rest?"
        ),
        "note": (
            "W1 close/final/ATS/CLV fill after Sat 9/5. "
            "W0 finals are filled; tag=n/a so ats_vs_tag stays null."
        ),
    }

    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# CFB grades summary (read-only)",
        "",
        f"**as_of:** `{summary['as_of']}`  ",
        f"**store:** `{summary['store']}`  ",
        f"**n_rows:** {summary['n_rows']}",
        "",
        "## Counts",
        "",
        f"- by week: `{summary['by_week']}`",
        f"- by market: `{summary['by_market']}`",
        f"- W1 tags: `{summary['w1_tags']}`",
        f"- W1 PLAY sides: **{summary['w1_play_sides']}** "
        f"(fat-dog PLAY sides: **{summary['w1_fat_dog_play_sides']}**)",
        "",
        "## Grades (filled where finals exist)",
        "",
        f"- ATS-vs-KEI graded: {summary['n_ats_vs_kei_graded']} · "
        f"rate={summary['ats_vs_kei_rate']}",
        f"- ATS-vs-tag graded: {summary['n_ats_vs_tag_graded']} · "
        f"rate={summary['ats_vs_tag_rate']}",
        f"- mean CLV: {summary['mean_clv']} (n={summary['n_clv']})",
        f"- mean signed_error_kei: {summary['mean_signed_error_kei']} "
        f"(n={summary['n_signed_error']})",
        f"- error by WP bucket: `{summary['error_by_bucket']}`",
        "",
        "## Pre-registered question",
        "",
        summary["pre_registered_question"],
        "",
        summary["note"],
        "",
        "KEI files unchanged. No publisher. No tag rewriter.",
        "",
    ]
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(SUMMARY_MD.read_text(encoding="utf-8"))
    print(f"wrote {SUMMARY_MD}")
    print(f"wrote {SUMMARY_JSON}")
    return 0


def cmd_status() -> int:
    rows = _read_rows()
    print(f"store: {STORE} exists={STORE.exists()} rows={len(rows)}")
    print(f"schema: {SCHEMA} exists={SCHEMA.exists()}")
    print(f"card: {CARD} exists={CARD.exists()}")
    if rows:
        print("weeks", Counter(r.get("week") for r in rows))
        print("sources", Counter(r.get("source") for r in rows))
        w1_pending = sum(
            1
            for r in rows
            if r.get("week") == 1 and r.get("final_home") is None
        )
        print(f"w1 rows pending final fill: {w1_pending}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CFB grading harness")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser("seed", help="Schema checklist: empty store + W0 + W1 card")
    p_seed.add_argument(
        "--force",
        action="store_true",
        help="Wipe store and reseed (prefer append-only; use only for rebuild)",
    )
    sub.add_parser("summary", help="Read-only summary")
    sub.add_parser("status", help="Store status")

    args = ap.parse_args()
    if args.cmd == "seed":
        return cmd_seed(force=bool(args.force))
    if args.cmd == "summary":
        return cmd_summary()
    if args.cmd == "status":
        return cmd_status()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
