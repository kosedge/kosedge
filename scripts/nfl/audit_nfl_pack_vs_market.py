#!/usr/bin/env python3
"""Pack vs FantasyPros team identity audit.

Joins the live depth pack to the FantasyPros ADP team field (same feed as
the fantasy desk). Emits mismatches only — pack team ≠ FP team.

Reality/market > stale pack. Does not bulk-move on weak name matches.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = (
    ROOT
    / "services/model-service/src/services/nfl_season_engine/data"
    / "nfl_depth_chart_2026_w1.json"
)
ADP_HALF = ROOT / "apps/web/data/fantasy/adp-fantasypros-2026-half_ppr.json"
ADP_PPR = ROOT / "apps/web/data/fantasy/adp-fantasypros-2026-ppr.json"
ADP_STD = ROOT / "apps/web/data/fantasy/adp-fantasypros-2026-standard.json"

SKILL = ("QB", "RB", "WR", "TE")
ADP_SCOPE = 200
ADP_CLEAR = 150

# Desk-documented SoT (checksum QBs + skill overlays). FP disagreement here
# is STALE_FP, not an auto-move — unless pack itself drifted off the overlay.
DOCUMENTED_SOT_RAW: Tuple[Tuple[str, str], ...] = (
    ("Tua Tagovailoa", "ATL"),
    ("Malik Willis", "MIA"),
    ("Kyler Murray", "MIN"),
    ("Jacoby Brissett", "ARI"),
    ("Stefon Diggs", "WAS"),
    ("Chig Okonkwo", "WAS"),
    ("Terry McLaurin", "WAS"),
    ("Kenneth Walker III", "KC"),
    ("Zach Charbonnet", "SEA"),
    ("Mike Evans", "SF"),
    ("Emeka Egbuka", "TB"),
)

COMMON_LAST = {
    "johnson",
    "williams",
    "brown",
    "smith",
    "jones",
    "davis",
    "wilson",
    "moore",
    "taylor",
    "thomas",
    "white",
    "harris",
    "jackson",
    "martin",
    "thompson",
    "garcia",
    "robinson",
    "clark",
    "lewis",
    "lee",
    "walker",
    "hall",
    "allen",
    "young",
    "king",
    "wright",
    "hill",
    "scott",
    "green",
    "adams",
    "baker",
    "nelson",
    "carter",
    "mitchell",
    "roberts",
    "turner",
    "phillips",
    "campbell",
    "parker",
    "evans",
    "edwards",
    "collins",
    "stewart",
    "morris",
    "rogers",
    "reed",
    "cook",
    "morgan",
    "bell",
    "murphy",
    "bailey",
    "cooper",
    "richardson",
    "howard",
    "ward",
    "peterson",
    "gray",
    "james",
    "watson",
    "brooks",
    "kelly",
    "sanders",
    "price",
    "bennett",
    "wood",
    "barnes",
    "ross",
    "henderson",
    "coleman",
    "jenkins",
    "perry",
    "powell",
    "long",
    "patterson",
    "hughes",
    "washington",
    "butler",
    "simmons",
    "foster",
    "bryant",
    "alexander",
    "russell",
    "griffin",
    "hayes",
    "johnsonjr",
}

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

NAME_ALIASES = {
    "amonrastbrown": "amonrastbrown",
    "chigoziemokonkwo": "chigokonkwo",
    "chigokonkwo": "chigokonkwo",
}


def _canon_team(team: str) -> str:
    token = (team or "").strip().upper()
    aliases = {
        "LA": "LAR",
        "LAR": "LAR",
        "JAC": "JAX",
        "JAX": "JAX",
        "WSH": "WAS",
        "WFT": "WAS",
        "WAS": "WAS",
        "OAK": "LV",
        "LVR": "LV",
        "SD": "LAC",
        "ARZ": "ARI",
        "GNB": "GB",
        "KAN": "KC",
        "SFO": "SF",
        "NOR": "NO",
        "TAM": "TB",
        "TBB": "TB",
        "NEP": "NE",
    }
    return aliases.get(token, token)


def _norm(name: str) -> str:
    token = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    token = re.sub(r"(jr|sr|iii|ii|iv|v)$", "", token)
    return NAME_ALIASES.get(token, token)


DOCUMENTED_SOT: Dict[str, str] = {
    _norm(name): team for name, team in DOCUMENTED_SOT_RAW
}


def _tokens(name: str) -> List[str]:
    raw = re.sub(r"[^a-z0-9\s]", " ", (name or "").lower())
    return [t for t in raw.split() if t and t not in SUFFIXES]


def _core(name: str) -> str:
    return "".join(_tokens(name))


def _last(name: str) -> str:
    toks = _tokens(name)
    return toks[-1] if toks else ""


def _load_adp(path: Path, source: str) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: List[Dict[str, Any]] = []
    for p in payload.get("players") or []:
        name = str(p.get("player_name") or "").strip()
        pos = str(p.get("player_position_id") or "").strip().upper()
        team = _canon_team(str(p.get("player_team_id") or ""))
        if not name or pos not in SKILL or not team:
            continue
        adp = p.get("rank_ecr")
        if adp is None:
            adp = p.get("rank_ave")
        try:
            adp_n = float(adp)
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "fp_name": name,
                "fp_team": team,
                "fp_pos": pos,
                "adp": adp_n,
                "fp_id": str(p.get("player_id") or ""),
                "source": source,
                "norm": _norm(name),
                "core": _core(name),
                "last": _last(name),
            }
        )
    meta = {
        "fetched_at": payload.get("fetched_at"),
        "last_updated": payload.get("last_updated"),
        "count": payload.get("count"),
        "source": source,
    }
    for row in out:
        row["_meta"] = meta
    return out


def merge_adp_feeds() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    half = _load_adp(ADP_HALF, "half_ppr")
    ppr = _load_adp(ADP_PPR, "ppr")
    std = _load_adp(ADP_STD, "standard")
    by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in half:
        by_key[(row["norm"], row["fp_pos"])] = row
    for extra in ppr + std:
        key = (extra["norm"], extra["fp_pos"])
        if key not in by_key:
            by_key[key] = extra
    players = list(by_key.values())
    meta = {
        "half_n": len(half),
        "merged_n": len(players),
        "half_fetched_at": (half[0]["_meta"]["fetched_at"] if half else None),
        "half_last_updated": (half[0]["_meta"]["last_updated"] if half else None),
    }
    return players, meta


def _index_fp(players: Iterable[Dict[str, Any]]) -> Dict[str, Dict[Tuple[str, str], List[Dict[str, Any]]]]:
    by_norm: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    by_core: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for p in players:
        by_norm[(p["norm"], p["fp_pos"])].append(p)
        by_core[(p["core"], p["fp_pos"])].append(p)
    return {"norm": by_norm, "core": by_core}


def match_fp(
    name: str,
    pos: str,
    idx: Dict[str, Dict[Tuple[str, str], List[Dict[str, Any]]]],
) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """Return (fp_row, match_kind, confidence). confidence is high|weak|none."""
    pos_u = pos.upper()
    norm = _norm(name)
    core = _core(name)
    last = _last(name)
    hits = idx["norm"].get((norm, pos_u)) or []
    if len(hits) == 1:
        return hits[0], "full_name_pos", "high"
    if len(hits) > 1:
        return None, "full_name_pos_ambiguous", "weak"
    hits = idx["core"].get((core, pos_u)) or []
    if len(hits) == 1:
        conf = "weak" if last in COMMON_LAST and len(core) <= 10 else "high"
        kind = "core_name_pos"
        if conf == "weak":
            kind = "core_name_pos_common_last"
        return hits[0], kind, conf
    if len(hits) > 1:
        return None, "core_name_pos_ambiguous", "weak"
    # Unique last+pos only if last is uncommon.
    last_hits: List[Dict[str, Any]] = []
    for (ln, p), rows in idx["core"].items():
        if p != pos_u:
            continue
        for row in rows:
            if row["last"] == last:
                last_hits.append(row)
    if last and last not in COMMON_LAST and len({r["norm"] for r in last_hits}) == 1:
        return last_hits[0], "unique_last_pos", "weak"
    return None, "unmatched", "none"


def load_pack(path: Path = PACK_PATH) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []
    for r in payload.get("rows") or []:
        pos = str(r.get("position") or "").upper()
        if pos not in SKILL:
            continue
        name = str(r.get("player_name") or "").strip()
        team = _canon_team(str(r.get("team") or ""))
        if not name or not team:
            continue
        try:
            depth = int(r.get("depth_order") or 99)
        except (TypeError, ValueError):
            depth = 99
        rows.append(
            {
                "pack_name": name,
                "pack_team": team,
                "pack_pos": pos,
                "pack_depth": depth,
                "pack_id": str(r.get("player_id") or ""),
                "pack_slot": str(r.get("depth_slot") or ""),
                "norm": _norm(name),
            }
        )
    return rows


def load_csv_desk() -> Tuple[List[Dict[str, Any]], str]:
    pointer = ROOT / "data/ops/nfl-web-launch-bundle.json"
    bundle_id = ""
    if pointer.is_file():
        payload = json.loads(pointer.read_text(encoding="utf-8"))
        bundle_id = str(payload.get("bundle_id") or payload.get("active_run_id") or "")
    csv_path = ROOT / "data/ops" / bundle_id / "player_regular_season_totals.csv"
    rows: List[Dict[str, Any]] = []
    if not csv_path.is_file():
        return rows, bundle_id
    with csv_path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pos = str(r.get("position") or "").upper()
            if pos not in SKILL:
                continue
            name = str(r.get("player_name") or "").strip()
            team = _canon_team(str(r.get("team") or ""))
            if not name or not team:
                continue
            rows.append(
                {
                    "csv_name": name,
                    "csv_team": team,
                    "csv_pos": pos,
                    "norm": _norm(name),
                }
            )
    return rows, bundle_id


def classify(
    pack_team: str,
    fp_team: str,
    adp: Optional[float],
    pack_depth: int,
    match_conf: str,
    norm: str,
) -> str:
    if match_conf == "none":
        return "UNMATCHED"
    if pack_team == fp_team:
        return "OK"
    if match_conf == "weak":
        return "NAME_MATCH_WEAK"
    documented = DOCUMENTED_SOT.get(norm)
    if documented and pack_team == documented and fp_team != documented:
        return "STALE_FP"
    if adp is not None and adp <= ADP_CLEAR:
        return "CLEAR_ERROR"
    if pack_depth == 1:
        return "CLEAR_ERROR"
    if adp is not None and adp <= ADP_SCOPE:
        return "CLEAR_ERROR"
    return "NAME_MATCH_WEAK"


def audit(
    pack_path: Path = PACK_PATH,
) -> Dict[str, Any]:
    pack = load_pack(pack_path)
    fp_players, adp_meta = merge_adp_feeds()
    idx = _index_fp(fp_players)
    pack_by_norm_pos = {(r["norm"], r["pack_pos"]): r for r in pack}

    mismatches: List[Dict[str, Any]] = []
    unmatched_pack: List[Dict[str, Any]] = []
    ok_n = 0
    seen: set[Tuple[str, str]] = set()

    def consider(pack_row: Dict[str, Any], in_scope_reason: str) -> None:
        nonlocal ok_n
        key = (pack_row["norm"], pack_row["pack_pos"])
        if key in seen:
            return
        fp, kind, conf = match_fp(pack_row["pack_name"], pack_row["pack_pos"], idx)
        if fp is None:
            if pack_row["pack_depth"] == 1 or in_scope_reason.startswith("adp"):
                unmatched_pack.append(
                    {
                        **pack_row,
                        "in_scope": in_scope_reason,
                        "match_kind": kind,
                    }
                )
            return
        seen.add(key)
        cls = classify(
            pack_row["pack_team"],
            fp["fp_team"],
            fp["adp"],
            pack_row["pack_depth"],
            conf,
            pack_row["norm"],
        )
        if cls == "OK":
            ok_n += 1
            return
        mismatches.append(
            {
                "player_name": pack_row["pack_name"],
                "player_id": pack_row["pack_id"],
                "pos": pack_row["pack_pos"],
                "pack_team": pack_row["pack_team"],
                "pack_role": f"{pack_row['pack_pos']}{pack_row['pack_depth']}",
                "pack_depth": pack_row["pack_depth"],
                "fp_team": fp["fp_team"],
                "fp_name": fp["fp_name"],
                "adp": fp["adp"],
                "fp_source": fp["source"],
                "match_kind": kind,
                "match_confidence": conf,
                "class": cls,
                "in_scope": in_scope_reason,
            }
        )

    fp_by_norm_pos = {(p["norm"], p["fp_pos"]): p for p in fp_players}

    for row in pack:
        fp = fp_by_norm_pos.get((row["norm"], row["pack_pos"]))
        adp = fp["adp"] if fp else None
        starter = row["pack_depth"] == 1
        if starter:
            consider(row, "pack_starter")
        elif adp is not None and adp <= ADP_SCOPE:
            consider(row, f"adp<={int(ADP_SCOPE)}")

    # FP ADP≤150 names that exist in pack but were skipped (depth 2+ without
    # being considered) — already handled via adp<=200. Catch pack-missing stars.
    unmatched_fp: List[Dict[str, Any]] = []
    for p in fp_players:
        if p["adp"] > ADP_CLEAR:
            continue
        if (p["norm"], p["fp_pos"]) in pack_by_norm_pos:
            continue
        # Maybe pack has them at another pos or unmatched name.
        fp_hit, kind, conf = match_fp(p["fp_name"], p["fp_pos"], idx)
        pack_hit = pack_by_norm_pos.get((p["norm"], p["fp_pos"]))
        if pack_hit is None:
            # try core against pack
            core_hits = [
                r
                for r in pack
                if r["pack_pos"] == p["fp_pos"] and _core(r["pack_name"]) == p["core"]
            ]
            if len(core_hits) == 1:
                consider(core_hits[0], f"fp_adp<={int(ADP_CLEAR)}")
                continue
            unmatched_fp.append(
                {
                    "fp_name": p["fp_name"],
                    "fp_team": p["fp_team"],
                    "pos": p["fp_pos"],
                    "adp": p["adp"],
                    "reason": "not_in_pack",
                }
            )

    mismatches.sort(key=lambda r: (r["class"], r.get("adp") or 999, r["player_name"]))
    counts = {
        "ok_matched_same_team": ok_n,
        "mismatches": len(mismatches),
        "CLEAR_ERROR": sum(1 for r in mismatches if r["class"] == "CLEAR_ERROR"),
        "NAME_MATCH_WEAK": sum(1 for r in mismatches if r["class"] == "NAME_MATCH_WEAK"),
        "STALE_FP": sum(1 for r in mismatches if r["class"] == "STALE_FP"),
        "unmatched_pack_in_scope": len(unmatched_pack),
        "unmatched_fp_adp150_not_in_pack": len(unmatched_fp),
    }
    smoke = {}
    for name, want in DOCUMENTED_SOT_RAW[-4:]:
        needle = _norm(name)
        row = next((r for r in pack if r["norm"] == needle), None)
        smoke[needle] = {
            "pack_team": row["pack_team"] if row else None,
            "want": want,
            "ok": bool(row and row["pack_team"] == want),
        }

    csv_rows, bundle_id = load_csv_desk()
    csv_mismatches: List[Dict[str, Any]] = []
    for row in csv_rows:
        fp, kind, conf = match_fp(row["csv_name"], row["csv_pos"], idx)
        if fp is None or conf != "high":
            continue
        if fp["adp"] > ADP_CLEAR:
            continue
        if row["csv_team"] != fp["fp_team"]:
            csv_mismatches.append(
                {
                    "player_name": row["csv_name"],
                    "pos": row["csv_pos"],
                    "pack_team": row["csv_team"],
                    "pack_role": "csv",
                    "fp_team": fp["fp_team"],
                    "adp": fp["adp"],
                    "match_kind": kind,
                    "match_confidence": conf,
                }
            )
    counts["csv_vs_fp_adp150"] = len(csv_mismatches)
    counts["csv_bundle"] = bundle_id

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "adp_meta": adp_meta,
        "counts": counts,
        "mismatches": mismatches,
        "unmatched_pack": unmatched_pack,
        "unmatched_fp": unmatched_fp[:40],
        "csv_mismatches": csv_mismatches,
        "smoke": smoke,
    }


def _md_table(rows: List[Dict[str, Any]], cols: List[Tuple[str, str]]) -> str:
    if not rows:
        return "_None._\n"
    header = "| " + " | ".join(label for label, _ in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [header, sep]
    for row in rows:
        cells = []
        for _, key in cols:
            val = row.get(key, "")
            if isinstance(val, float):
                val = f"{val:.0f}" if val == int(val) else f"{val:.1f}"
            cells.append(str(val).replace("|", "/"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def render_markdown(report: Dict[str, Any]) -> str:
    c = report["counts"]
    smoke_lines = []
    for key, row in report["smoke"].items():
        mark = "PASS" if row["ok"] else "FAIL"
        smoke_lines.append(
            f"- `{key}` pack={row['pack_team']} want={row['want']} — **{mark}**"
        )
    by_class: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in report["mismatches"]:
        by_class[row["class"]].append(row)
    cols = [
        ("Player", "player_name"),
        ("Pos", "pos"),
        ("Pack", "pack_team"),
        ("Role", "pack_role"),
        ("FP team", "fp_team"),
        ("ADP", "adp"),
        ("Match", "match_kind"),
        ("Conf", "match_confidence"),
    ]
    parts = [
        "# NFL pack vs FantasyPros team mismatches — 2026-08-13",
        "",
        "Doctrine: **Reality/market > stale pack.** One SoT after correction.",
        "Source: FantasyPros partners ADP (same feed as the fantasy desk).",
        "This file is **mismatches only**. You review CLEAR_ERROR names and say",
        "`fix these / hold those`. That is the whole human loop.",
        "",
        "Re-run: `python3 scripts/nfl/audit_nfl_pack_vs_market.py`",
        "",
        f"Generated: `{report['generated_at_utc']}`",
        f"FP snapshot: `{report['adp_meta'].get('half_last_updated')}` "
        f"(fetched `{report['adp_meta'].get('half_fetched_at')}`, "
        f"merged n={report['adp_meta'].get('merged_n')})",
        "",
        "## Counts",
        "",
        f"- Same-team matches in scope: **{c['ok_matched_same_team']}**",
        f"- Mismatches: **{c['mismatches']}**",
        f"- CLEAR_ERROR: **{c['CLEAR_ERROR']}**",
        f"- NAME_MATCH_WEAK: **{c['NAME_MATCH_WEAK']}**",
        f"- STALE_FP (documented pack overlay / checksum QB): **{c['STALE_FP']}**",
        f"- Unmatched pack (in scope, no FP name hit): **{c['unmatched_pack_in_scope']}**",
        f"- FP ADP≤150 not in pack: **{c['unmatched_fp_adp150_not_in_pack']}**",
        f"- Fantasy CSV vs FP (ADP≤150): **{c.get('csv_vs_fp_adp150', 0)}** "
        f"(bundle `{c.get('csv_bundle') or '—'}`)",
        "",
        "## Human loop",
        "",
        (
            "**Nothing to fix.** Pack, fantasy CSV, and FantasyPros agree on team "
            "for every in-scope skill player after the Walker→KC hotfix."
            if c["CLEAR_ERROR"] == 0 and not (report.get("csv_mismatches") or [])
            else "**Review CLEAR_ERROR below.** Say which names to fix vs hold. "
            "Do not bulk-move NAME_MATCH_WEAK."
        ),
        "",
        "## Smoke (must hold)",
        "",
        *smoke_lines,
        "",
        "## CLEAR_ERROR — pack team ≠ FP team (high-confidence name)",
        "",
        "Fix these like Walker: update pack overlay, re-allocate, republish.",
        "Do not bulk-move if the name match looks wrong.",
        "",
        _md_table(by_class.get("CLEAR_ERROR") or [], cols),
        "## STALE_FP — pack has documented newer SoT; FP still elsewhere",
        "",
        "Hold unless you confirm FP is right and the overlay is the bug.",
        "",
        _md_table(by_class.get("STALE_FP") or [], cols),
        "## NAME_MATCH_WEAK — do not bulk-move",
        "",
        _md_table(by_class.get("NAME_MATCH_WEAK") or [], cols),
        "## Fantasy CSV vs FP (ADP≤150)",
        "",
        "Desk projection team ≠ FantasyPros team. Dual-map if pack already matches FP.",
        "",
        _md_table(report.get("csv_mismatches") or [], cols),
        "## Unmatched pack in scope (no unique FP name hit)",
        "",
        _md_table(
            [
                {
                    "player_name": r["pack_name"],
                    "pos": r["pack_pos"],
                    "pack_team": r["pack_team"],
                    "pack_role": f"{r['pack_pos']}{r['pack_depth']}",
                    "fp_team": "",
                    "adp": "",
                    "match_kind": r.get("match_kind"),
                    "match_confidence": "none",
                }
                for r in report["unmatched_pack"][:30]
            ],
            cols,
        ),
        "## FP ADP≤150 not found in pack (sample)",
        "",
        _md_table(
            [
                {
                    "player_name": r["fp_name"],
                    "pos": r["pos"],
                    "pack_team": "—",
                    "pack_role": "absent",
                    "fp_team": r["fp_team"],
                    "adp": r["adp"],
                    "match_kind": "not_in_pack",
                    "match_confidence": "n/a",
                }
                for r in report["unmatched_fp"][:25]
            ],
            cols,
        ),
    ]
    return "\n".join(parts).rstrip() + "\n"


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fields = [
        "player_name",
        "player_id",
        "pos",
        "pack_team",
        "pack_role",
        "pack_depth",
        "fp_team",
        "fp_name",
        "adp",
        "fp_source",
        "match_kind",
        "match_confidence",
        "class",
        "in_scope",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", type=Path, default=PACK_PATH)
    ap.add_argument(
        "--out-md",
        type=Path,
        default=ROOT / "data/ops/nfl-pack-vs-market-mismatches-20260813.md",
    )
    ap.add_argument(
        "--out-csv",
        type=Path,
        default=ROOT / "data/ops/nfl-pack-vs-market-mismatches-20260813.csv",
    )
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument(
        "--fail-on-clear-error",
        action="store_true",
        default=True,
        help="Exit 1 when CLEAR_ERROR > 0 (default on).",
    )
    ap.add_argument(
        "--no-fail-on-clear-error",
        action="store_false",
        dest="fail_on_clear_error",
    )
    args = ap.parse_args()
    report = audit(args.pack)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(render_markdown(report), encoding="utf-8")
    write_csv(args.out_csv, report["mismatches"])
    summary = {
        "md": str(args.out_md),
        "csv": str(args.out_csv),
        "counts": report["counts"],
        "smoke": report["smoke"],
        "clear_errors": [
            f"{r['player_name']} {r['pack_team']}→{r['fp_team']} adp={r['adp']:.0f}"
            for r in report["mismatches"]
            if r["class"] == "CLEAR_ERROR"
        ],
    }
    print(json.dumps(summary, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    smoke_fail = [k for k, v in report["smoke"].items() if not v["ok"]]
    if smoke_fail:
        print("SMOKE FAIL:", ", ".join(smoke_fail), file=sys.stderr)
        return 2
    n_clear = int(report["counts"].get("CLEAR_ERROR") or 0)
    if args.fail_on_clear_error and n_clear:
        print(f"CLEAR_ERROR={n_clear} (review mismatch markdown)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
