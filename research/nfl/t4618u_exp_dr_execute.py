#!/usr/bin/env python3
"""t4618u Experiment D-R ONLY — honest schedule-rest on frozen G34 (CERT=0).

Authority
  DECISION_RYAN_t4618u CLEAR Exp D-R ONLY   sha8 05632ef0
  COS_ORDER_CURSOR_t4618u_EXP_DR_EXECUTE    sha8 fe01612d
  PASS_PROTOCOL                             sha8 dd686e13
  FREEZE D6=(B) four-col                    sha8 81998210
  ACK D6/D7                                 sha8 82c71d64
  ALEX STOP ERRATUM §5 STOP BOX             sha8 6bd07cc8
  FEASIBILITY v1 (frozen; §8 withdrawn)     sha8 9906430e
  H2 FROZEN                                 sha8 db2cf4b2
  G34 predictions comparator                sha8 c3248302

STOP BOX (ACK 82c71d64 / Alex 6bd07cc8 §5). RESEARCH PASS iff ALL of:
  1. Path M: m ~ a + b·mm + c·pm_DR (OLS HC1); c>0 and 95% CI excl 0
  2. vs G34 paired boot B=10000 seed 4141 percentile CI on Δ_DR excl 0
     AND point Δ_DR ≥ RESEARCH_FLOOR_vs_G34 = 0.05
  3. D4 artifacts (β_rest HC1 table incl beta_missing_ind; short-rest
     subset supportive; missingness rates from hashed emit)

Binding = pooled ≤2022 OOF F1–F9 H2. 2023 supportive only. 2024+ forbidden.
EPA secondary report-only. No 0.10 floor. FEAS §8 withdrawn.
X_rest = exactly 4 cols: drest_clip, short_h, short_a, rest_missing.
pm_DR = pm_G34 + X_rest·β_rest. Intercept-free OLS (m−pm_G34)~X_rest
on seasons < S only. HC1 diagnostic; point β used. Do not refit G34.

Does NOT: call Odds, merge #646/#647/#648, touch LOCKED_SCORING /
config_overrides, call simulate_nfl_game, touch F2 PHI@WSH, deploy,
publish, claim CERT, redesign, invent, or use 2024+.

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · sealed=1.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))
_USER_SITE = Path.home() / ".local/lib/python3.12/site-packages"
if _USER_SITE.is_dir() and str(_USER_SITE) not in sys.path:
    sys.path.insert(0, str(_USER_SITE))
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from src.services.nfl_canonical_teams import canonicalize_team  # noqa: E402

from t4602u_exp_a_ridge_joint import hc1_ci, ols_hc1  # noqa: E402

# Forbidden production surfaces — never imported.
_FORBIDDEN_IMPORTS = (
    "simulate_nfl_game",
    "LOCKED_SCORING",
    "config_overrides",
    "NflGameInputs",
)

TICKET = "t4618u"
LABEL = "RESEARCH_DIAGNOSTIC_EXP_DR"
CERT_CANDIDATE = 0
FILE_MODE = 0o444
BOOT_B = 10000
BOOT_SEED = 4141
Z95 = 1.96
RESEARCH_FLOOR = 0.05
CLIP_ABS = 7.0
SHORT_DAYS = 5.0
LAYOFF_DAYS = 21
X_COLS = ("drest_clip", "short_h", "short_a", "rest_missing")

DECISION_SHA8 = "05632ef0"
COS_ORDER_SHA8 = "fe01612d"
PASS_PROTOCOL_SHA8 = "dd686e13"
FREEZE_D6_SHA8 = "81998210"
ACK_SHA8 = "82c71d64"
STOP_ERRATUM_SHA8 = "6bd07cc8"
FEAS_SHA8 = "9906430e"
H2_SHA8 = "db2cf4b2"
COMPARATOR_SHA8 = "c3248302"

H2_SHA256 = "db2cf4b24bfa9c441f7eafea19d5c24624541f9cb7225759e9882f61cb6c6463"
GAMES_CSV_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OOS_SHA256 = "1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed"
EMIT_SHA256 = "02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2"
PRED_SHA256 = "c3248302c5efd9bb63629721679ca46eba2106d6a3a71877e3d10271a26c43cb"
SELECTED_SHA256 = "3172b23617f31e38ab990adc6c2d7b87176a8d0eace890eea3208e24e5635939"
ACK_SHA256 = "82c71d6475cccfc52a7c263ebca719c0cb59c1cf160e5ace5f32cce59e207234"
FEAS_SHA256 = "9906430ec7192b994cf84eaca1429d71bcd63d1ca02b6292b09c1ca92e444458"

N_GAMES_EXPECT = 2992
N_OOF_EXPECT = 2440
N_2023_EXPECT = 285
N_PRED_EXPECT = 2725
CFG_ID = "G34"

H2_PATH = HERE / "t4586u_exp_a_h2_manifest_freeze" / "CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json"
GAMES_PATH = HERE / "t4586u_exp_e_inputs" / "games.csv"
OOS_PATH = HERE / "t4586u_exp_e_inputs" / "historical_oos_games.csv"
PRED_PATH = HERE / "t4602u_exp_a" / "predictions.csv"
SELECTED_PATH = HERE / "t4602u_exp_a" / "selected_cell.json"
ACK_PATH = HERE / "t4605u_exp_dr_feasibility" / "CURSOR_EXP_DR_ACK_D6_D7_t4605u_v1.md"
FEAS_PATH = HERE / "t4605u_exp_dr_feasibility" / "CURSOR_EXP_DR_FEASIBILITY_t4605u_v1.md"
SCRIPT_PATH = Path(__file__).resolve()
OUT_DIR = HERE / "t4618u_exp_dr"
CACHE_DIR = Path(os.environ.get("T4618U_CACHE", "/tmp/nflverse-pbp-exp-e"))

EMIT_GIT_REF = (
    "origin/cursor/epa-wf-feature-emit-5bcd:"
    "data/ops/nfl-t4564u-epa-wf-feature-emit/"
    "nfl-epa-wf-pbp-2013-2023-t4564u-20261027T213659Z/"
    "epa_wf_features_2013_2023.csv"
)

FOLD_S = {f"F{i}": 2013 + i for i in range(1, 10)}  # F1=2014 … F9=2022

_H1_CLOSED = False
_H1_HASHES: Dict[str, str] = {}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha8(digest: str) -> str:
    return digest[:8]


def _register_hash(label: str, path: Path) -> str:
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"hash target missing or empty: {label} ({path})")
    digest = _sha256_file(path)
    _H1_HASHES[label] = digest
    print(f"[h1] {label} sha256={digest} sha8={_sha8(digest)}", flush=True)
    return digest


def _franchise(team: str) -> str:
    raw = str(team or "").strip().upper()
    return str(canonicalize_team(raw) or raw)


def _assert_no_forbidden_imports() -> None:
    for name in _FORBIDDEN_IMPORTS:
        if name in sys.modules:
            raise RuntimeError(f"forbidden import present: {name}")


def _write_sha256sums(path: Path, items: Mapping[str, str]) -> None:
    lines = [f"{digest}  {name}\n" for name, digest in sorted(items.items())]
    path.write_text("".join(lines), encoding="utf-8")


def _chmod_ro(path: Path) -> None:
    os.chmod(path, FILE_MODE)


def _prepare_write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        os.chmod(path, 0o644)


def _write_json(path: Path, obj: Any) -> str:
    _prepare_write(path)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    _chmod_ro(path)
    return digest


def _write_text(path: Path, text: str) -> str:
    _prepare_write(path)
    path.write_text(text, encoding="utf-8")
    digest = _sha256_file(path)
    _chmod_ro(path)
    return digest


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    _prepare_write(path)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fieldnames), extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})
    digest = _sha256_file(path)
    _chmod_ro(path)
    return digest


def _extract_emit(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print("[h1] git-show #646 emit CSV (cite; not a merge)", flush=True)
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", EMIT_GIT_REF])
    dest.write_bytes(raw)


def close_h1() -> Dict[str, Any]:
    """Hash-pin every D-R input BEFORE any date-diff or OLS."""
    global _H1_CLOSED
    _H1_CLOSED = False
    _H1_HASHES.clear()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    blocked: List[str] = []

    h2_sha = _register_hash("CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json", H2_PATH)
    if h2_sha != H2_SHA256:
        blocked.append(f"H2 manifest sha mismatch got={h2_sha} want={H2_SHA256}")

    games_sha = _register_hash("games.csv", GAMES_PATH)
    if games_sha != GAMES_CSV_SHA256:
        blocked.append(f"games.csv sha mismatch got={games_sha} want={GAMES_CSV_SHA256}")

    oos_sha = _register_hash("historical_oos_games.csv", OOS_PATH)
    if oos_sha != OOS_SHA256:
        blocked.append(f"oos sha mismatch got={oos_sha} want={OOS_SHA256}")

    pred_sha = _register_hash("predictions.csv", PRED_PATH)
    if pred_sha != PRED_SHA256:
        blocked.append(f"predictions.csv sha mismatch got={pred_sha} want={PRED_SHA256}")

    sel_sha = _register_hash("selected_cell.json", SELECTED_PATH)
    if sel_sha != SELECTED_SHA256:
        blocked.append(f"selected_cell.json sha mismatch got={sel_sha} want={SELECTED_SHA256}")

    ack_sha = _register_hash("CURSOR_EXP_DR_ACK_D6_D7_t4605u_v1.md", ACK_PATH)
    if ack_sha != ACK_SHA256:
        blocked.append(f"ACK sha mismatch got={ack_sha} want={ACK_SHA256}")

    feas_sha = _register_hash("CURSOR_EXP_DR_FEASIBILITY_t4605u_v1.md", FEAS_PATH)
    if feas_sha != FEAS_SHA256:
        blocked.append(f"FEAS sha mismatch got={feas_sha} want={FEAS_SHA256}")

    _register_hash("t4618u_exp_dr_execute.py", SCRIPT_PATH)

    emit_path = CACHE_DIR / "epa_wf_features_2013_2023.csv"
    _extract_emit(emit_path)
    emit_sha = _register_hash("epa_wf_features_2013_2023.csv", emit_path)
    if emit_sha != EMIT_SHA256:
        blocked.append(f"emit csv sha mismatch got={emit_sha} want={EMIT_SHA256}")

    _write_sha256sums(OUT_DIR / "SHA256SUMS.inputs", dict(_H1_HASHES))
    print(f"[h1] wrote input SHA256SUMS n={len(_H1_HASHES)} (before any input parse)", flush=True)

    if blocked:
        _H1_CLOSED = False
        return {"ok": False, "blocked_reasons": blocked, "emit_path": str(emit_path)}

    _H1_CLOSED = True
    return {"ok": True, "blocked_reasons": [], "emit_path": str(emit_path)}


def _assert_h1() -> None:
    if not _H1_CLOSED:
        raise RuntimeError("H1 not closed; refusing to parse inputs")


def _load_json(path: Path) -> Any:
    _assert_h1()
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> List[Dict[str, str]]:
    _assert_h1()
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _finite(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in {"nan", "none", "nat", "<na>"}:
        return None
    try:
        x = float(s)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    return x


def _parse_date(val: str) -> Optional[date]:
    s = str(val or "").strip()
    if not s:
        return None
    if "T" in s:
        s = s.split("T", 1)[0]
    if " " in s:
        s = s.split(" ", 1)[0]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_iso(val: str) -> Optional[datetime]:
    s = str(val or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fit_beta_rest_only(x: "Any", y: "Any") -> Dict[str, Any]:
    """Intercept-free OLS y ~ X_rest (4 cols). HC1 diagnostic; point β used."""
    import numpy as np

    xx = np.asarray(x, dtype=np.float64)
    yy = np.asarray(y, dtype=np.float64)
    if xx.ndim != 2 or xx.shape[1] != 4:
        raise RuntimeError(f"X_rest must be (n, 4); got {xx.shape}")
    if yy.size == 0:
        zeros = [0.0] * 4
        return {
            "beta": zeros,
            "se": [float("nan")] * 4,
            "ci_lo": [float("nan")] * 4,
            "ci_hi": [float("nan")] * 4,
            "n": 0,
            "k": 4,
            "empty_design": True,
        }
    fit = ols_hc1(xx, yy)
    beta = [float(v) for v in fit["beta"]]
    se = [float(v) for v in fit["se"]]
    ci = [hc1_ci(b, s, Z95) for b, s in zip(beta, se)]
    return {
        "beta": beta,
        "se": se,
        "ci_lo": [c[0] for c in ci],
        "ci_hi": [c[1] for c in ci],
        "n": int(fit["n"]),
        "k": int(fit["k"]),
        "empty_design": False,
    }


def _x_rest_row(row: Mapping[str, Any]) -> List[float]:
    return [float(row[c]) for c in X_COLS]


def _pm_dr(pm_g34: float, xrow: Sequence[float], beta: Sequence[float]) -> float:
    return float(pm_g34) + sum(float(x) * float(b) for x, b in zip(xrow, beta))


def build_rest_emit(
    games: Sequence[Mapping[str, str]],
    emit: Sequence[Mapping[str, str]],
    oos: Sequence[Mapping[str, str]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Date-diff rest from hashed nflverse_gameday. No DOW. No emit placeholder."""
    emit_by_id = {str(r["game_id"]).strip(): r for r in emit}

    oos_by_key: Dict[Tuple[int, int, str, str], Dict[str, str]] = {}
    n_oos_ge_2024 = 0
    for r in oos:
        season = int(float(r["season"]))
        if season >= 2024:
            n_oos_ge_2024 += 1
            continue
        week = int(float(r["week"]))
        key = (season, week, _franchise(r["home"]), _franchise(r["away"]))
        oos_by_key[key] = r

    n_games_ge_2024 = 0
    n_emit_ge_2024 = sum(1 for r in emit if _finite(r.get("season")) is not None and float(r["season"]) >= 2024)
    n_gameday_mismatch_emit_games = 0
    n_oos_gameday_mismatch = 0
    n_oos_miss = 0
    n_emit_miss = 0
    n_gameday_empty = 0
    panel: List[Dict[str, Any]] = []

    for g in games:
        season = int(g["season"])
        week = int(g["week"])
        if season >= 2024:
            n_games_ge_2024 += 1
            continue
        gid = str(g["game_id"]).strip()
        home = _franchise(g["home"])
        away = _franchise(g["away"])
        er = emit_by_id.get(gid)
        if er is None:
            n_emit_miss += 1
            continue
        g_day = str(g.get("nflverse_gameday") or "").strip()
        e_day = str(er.get("nflverse_gameday") or "").strip()
        if g_day != e_day:
            n_gameday_mismatch_emit_games += 1
        gd = _parse_date(g_day) or _parse_date(e_day)
        if gd is None:
            n_gameday_empty += 1
            continue
        oos_row = oos_by_key.get((season, week, home, away))
        if oos_row is None:
            n_oos_miss += 1
            continue
        oos_day = _parse_date(oos_row.get("game_date") or "")
        if oos_day is None or oos_day != gd:
            n_oos_gameday_mismatch += 1
        ko = _parse_iso(g.get("kickoff_utc") or "") or _parse_iso(er.get("kickoff_utc") or "")
        ko_ts = float(ko.timestamp()) if ko is not None else 0.0
        # Placeholder rest on emit/games is 7.0 everywhere — never a D-R feature.
        emit_ph_h = _finite(er.get("rest_days_home"))
        emit_ph_a = _finite(er.get("rest_days_away"))
        panel.append(
            {
                "season": season,
                "week": week,
                "game_id": gid,
                "home": home,
                "away": away,
                "game_date": gd.isoformat(),
                "game_date_d": gd,
                "kickoff_utc": g.get("kickoff_utc") or er.get("kickoff_utc") or "",
                "kickoff_ts": ko_ts,
                "emit_placeholder_rest_home": emit_ph_h,
                "emit_placeholder_rest_away": emit_ph_a,
            }
        )

    # Per-franchise previous panel game → calendar-day rest.
    by_team: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in panel:
        by_team[row["home"]].append(row)
        by_team[row["away"]].append(row)

    rest_map: Dict[Tuple[str, str], Optional[int]] = {}
    for team, rows in by_team.items():
        rows_sorted = sorted(rows, key=lambda r: (r["game_date_d"], r["kickoff_ts"], r["game_id"]))
        prev_date: Optional[date] = None
        for r in rows_sorted:
            rest: Optional[int]
            if prev_date is None:
                rest = None
            else:
                rest = int((r["game_date_d"] - prev_date).days)
                if rest > LAYOFF_DAYS:
                    rest = None
            rest_map[(r["game_id"], team)] = rest
            prev_date = r["game_date_d"]

    emit_rows: List[Dict[str, Any]] = []
    n_rest_nan_home = 0
    n_rest_nan_away = 0
    n_drest_nonzero = 0
    n_short_h = 0
    n_short_a = 0
    n_rest_missing = 0
    n_placeholder_used = 0

    for row in panel:
        rh = rest_map.get((row["game_id"], row["home"]))
        ra = rest_map.get((row["game_id"], row["away"]))
        home_nan = rh is None
        away_nan = ra is None
        r_h = 0.0 if home_nan else float(rh)
        r_a = 0.0 if away_nan else float(ra)
        drest = max(-CLIP_ABS, min(CLIP_ABS, r_h - r_a))
        short_h = 1.0 if (not home_nan and float(rh) <= SHORT_DAYS) else 0.0
        short_a = 1.0 if (not away_nan and float(ra) <= SHORT_DAYS) else 0.0
        rest_missing = 1.0 if (home_nan or away_nan) else 0.0
        n_rest_nan_home += int(home_nan)
        n_rest_nan_away += int(away_nan)
        n_drest_nonzero += int(drest != 0.0)
        n_short_h += int(short_h == 1.0)
        n_short_a += int(short_a == 1.0)
        n_rest_missing += int(rest_missing == 1.0)
        emit_rows.append(
            {
                "season": row["season"],
                "week": row["week"],
                "game_id": row["game_id"],
                "home": row["home"],
                "away": row["away"],
                "game_date": row["game_date"],
                "kickoff_utc": row["kickoff_utc"],
                "rest_days_home": "" if home_nan else str(int(rh)),
                "rest_days_away": "" if away_nan else str(int(ra)),
                "rest_home_nan": int(home_nan),
                "rest_away_nan": int(away_nan),
                "r_prime_home": f"{r_h:.6f}",
                "r_prime_away": f"{r_a:.6f}",
                "drest_clip": f"{drest:.6f}",
                "short_h": int(short_h),
                "short_a": int(short_a),
                "rest_missing": int(rest_missing),
                "_drest": drest,
                "_short_h": short_h,
                "_short_a": short_a,
                "_rest_missing": rest_missing,
                "_rh": None if home_nan else float(rh),
                "_ra": None if away_nan else float(ra),
            }
        )

    n = len(emit_rows)
    coverage = {
        "n_games": n,
        "n_games_expect": N_GAMES_EXPECT,
        "n_games_ge_2024": n_games_ge_2024,
        "n_emit_ge_2024": n_emit_ge_2024,
        "n_oos_dropped_ge_2024": n_oos_ge_2024,
        "n_gameday_mismatch_emit_games": n_gameday_mismatch_emit_games,
        "n_oos_gameday_mismatch": n_oos_gameday_mismatch,
        "n_oos_miss": n_oos_miss,
        "n_emit_miss": n_emit_miss,
        "n_gameday_empty": n_gameday_empty,
        "n_rest_nan_home": n_rest_nan_home,
        "n_rest_nan_away": n_rest_nan_away,
        "n_rest_missing": n_rest_missing,
        "n_drest_nonzero": n_drest_nonzero,
        "n_short_h": n_short_h,
        "n_short_a": n_short_a,
        "n_placeholder_used": n_placeholder_used,
        "rate_nan_home": (n_rest_nan_home / n) if n else None,
        "rate_nan_away": (n_rest_nan_away / n) if n else None,
        "rate_rest_missing": (n_rest_missing / n) if n else None,
        "rate_drest_nonzero": (n_drest_nonzero / n) if n else None,
        "rate_short_h": (n_short_h / n) if n else None,
        "rate_short_a": (n_short_a / n) if n else None,
        "recipe": {
            "date_sot": "nflverse_gameday",
            "layoff_nan_gt": LAYOFF_DAYS,
            "clip_abs": CLIP_ABS,
            "short_le": SHORT_DAYS,
            "r_prime_nan_to_0": True,
            "x_cols": list(X_COLS),
            "dow_heuristic": False,
            "kickoff_fractional_feature": False,
            "emit_placeholder_used": False,
            "pbp_2012_used": False,
        },
    }
    print(
        f"[rest] n={n} nan_h={n_rest_nan_home} nan_a={n_rest_nan_away} "
        f"missing={n_rest_missing} drest_nz={n_drest_nonzero} "
        f"short_h={n_short_h} short_a={n_short_a} "
        f"gameday_mm={n_gameday_mismatch_emit_games} oos_mm={n_oos_gameday_mismatch}",
        flush=True,
    )
    return emit_rows, coverage


def _mae(pred: Sequence[float], actual: Sequence[float]) -> float:
    return float(sum(abs(p - a) for p, a in zip(pred, actual)) / max(len(pred), 1))


def _gap(m: Sequence[float], pm: Sequence[float], mm: Sequence[float]) -> List[float]:
    return [abs(mi - pi) - abs(mi - mmi) for mi, pi, mmi in zip(m, pm, mm)]


def metrics_block(
    m: Sequence[float],
    mm: Sequence[float],
    pm_dr: Sequence[float],
    pm_g34: Sequence[float],
    pm_epa: Sequence[float],
    *,
    seasons: Sequence[int],
    label: str,
) -> Dict[str, Any]:
    import numpy as np

    m_l = list(m)
    mm_l = list(mm)
    dr_l = list(pm_dr)
    g34_l = list(pm_g34)
    epa_l = list(pm_epa)
    n = len(m_l)
    mae_dr = _mae(dr_l, m_l)
    mae_g34 = _mae(g34_l, m_l)
    mae_epa = _mae(epa_l, m_l)
    mae_m = _mae(mm_l, m_l)
    gap_dr = _gap(m_l, dr_l, mm_l)
    gap_g34 = _gap(m_l, g34_l, mm_l)
    delta_dr = float(sum(gap_g34) / n - sum(gap_dr) / n) if n else float("nan")
    delta_vs_epa = float(mae_epa - mae_dr) if n else float("nan")

    x = np.column_stack(
        [
            np.ones(n, dtype=np.float64),
            np.asarray(mm_l, dtype=np.float64),
            np.asarray(dr_l, dtype=np.float64),
        ]
    )
    y = np.asarray(m_l, dtype=np.float64)
    enc = ols_hc1(x, y)
    a_hat, b_hat, c_hat = (float(v) for v in enc["beta"])
    a_se, b_se, c_se = (float(v) for v in enc["se"])
    c_lo, c_hi = hc1_ci(c_hat, c_se, Z95)
    path_m = bool(c_hat > 0.0 and (c_lo > 0.0 or c_hi < 0.0) and not (c_lo <= 0.0 <= c_hi))
    # Equivalent: c>0 and CI excludes 0. With c>0 that means lo>0.
    path_m = bool(c_hat > 0.0 and c_lo > 0.0)

    rng = np.random.default_rng(BOOT_SEED)
    ga = np.asarray(gap_dr, dtype=np.float64)
    gb = np.asarray(gap_g34, dtype=np.float64)
    boot = np.empty(BOOT_B, dtype=np.float64)
    for i in range(BOOT_B):
        ix = rng.integers(0, n, size=n)
        boot[i] = float(gb[ix].mean() - ga[ix].mean())
    boot_lo = float(np.percentile(boot, 2.5))
    boot_hi = float(np.percentile(boot, 97.5))
    ci_excl0 = bool(boot_lo > 0.0 or boot_hi < 0.0)
    point_ge_floor = bool(delta_dr >= RESEARCH_FLOOR)
    vs_g34_pass = bool(ci_excl0 and point_ge_floor)

    by_season: Dict[str, Any] = {}
    beats = 0
    for s in sorted(set(seasons)):
        idx = [i for i, ss in enumerate(seasons) if ss == s]
        mae_ds = _mae([dr_l[i] for i in idx], [m_l[i] for i in idx])
        mae_gs = _mae([g34_l[i] for i in idx], [m_l[i] for i in idx])
        mae_ms = _mae([mm_l[i] for i in idx], [m_l[i] for i in idx])
        win = mae_ds < mae_ms
        beats += int(win)
        by_season[str(s)] = {
            "n": len(idx),
            "mae_DR": mae_ds,
            "mae_G34": mae_gs,
            "mae_market": mae_ms,
            "delta_DR": mae_gs - mae_ds,
            "beats_market": win,
        }

    return {
        "label": label,
        "n": n,
        "mae_DR": mae_dr,
        "mae_G34": mae_g34,
        "mae_epa": mae_epa,
        "mae_market": mae_m,
        "mae_gap_DR_vs_market": mae_dr - mae_m,
        "mae_gap_G34_vs_market": mae_g34 - mae_m,
        "delta_DR": delta_dr,
        "delta_DR_vs_epa_report_only": delta_vs_epa,
        "seasons_beating_market": beats,
        "by_season": by_season,
        "path_m": {
            "equation": "m ~ a + b*mm + c*pm_DR",
            "estimator": "OLS HC1",
            "a": a_hat,
            "b": b_hat,
            "c": c_hat,
            "a_se_hc1": a_se,
            "b_se_hc1": b_se,
            "c_se_hc1": c_se,
            "c_ci95_lo": c_lo,
            "c_ci95_hi": c_hi,
            "c_gt_0": bool(c_hat > 0.0),
            "c_ci_excludes_0": bool(c_lo > 0.0 or c_hi < 0.0),
            "pass": path_m,
        },
        "vs_g34": {
            "delta_definition": "mae_G34 - mae_DR = mean(gap_G34)-mean(gap_DR); gap_X=|m-pm_X|-|m-mm|",
            "B": BOOT_B,
            "seed": BOOT_SEED,
            "ci": "percentile 95",
            "floor": RESEARCH_FLOOR,
            "delta_point": delta_dr,
            "delta_ci95_lo": boot_lo,
            "delta_ci95_hi": boot_hi,
            "ci_excludes_0": ci_excl0,
            "point_ge_0_05": point_ge_floor,
            "pass": vs_g34_pass,
        },
        "epa_secondary_report_only": True,
        "floor_0_10_applied": False,
    }


def join_predictions(
    rest_rows: Sequence[Mapping[str, Any]],
    preds: Sequence[Mapping[str, str]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    rest_by_id = {str(r["game_id"]): r for r in rest_rows}
    joined: List[Dict[str, Any]] = []
    n_join_miss = 0
    n_not_g34 = 0
    n_pred_ge_2024 = 0
    n_fold_drift = 0
    for p in preds:
        season = int(float(p["season"]))
        if season >= 2024:
            n_pred_ge_2024 += 1
            continue
        if str(p.get("cfg_id") or "") != CFG_ID:
            n_not_g34 += 1
        gid = str(p["game_id"]).strip()
        rr = rest_by_id.get(gid)
        if rr is None:
            n_join_miss += 1
            continue
        fold = str(p.get("fold") or "")
        expect_s = FOLD_S.get(fold)
        if fold == "S2023_supportive":
            expect_s = 2023
        if expect_s is not None and int(expect_s) != season:
            n_fold_drift += 1
        joined.append(
            {
                "season": season,
                "week": int(float(p["week"])),
                "game_id": gid,
                "home": str(p["home"]),
                "away": str(p["away"]),
                "fold": fold,
                "cfg_id": str(p["cfg_id"]),
                "neutral": int(float(p.get("neutral") or 0)),
                "m": float(p["m"]),
                "mm": float(p["mm"]),
                "pm_epa": float(p["pm_epa"]),
                "pm_G34": float(p["pm_A"]),
                "drest_clip": float(rr["_drest"]),
                "short_h": float(rr["_short_h"]),
                "short_a": float(rr["_short_a"]),
                "rest_missing": float(rr["_rest_missing"]),
                "rest_days_home": rr["rest_days_home"],
                "rest_days_away": rr["rest_days_away"],
            }
        )
    return joined, {
        "n_join_miss_vs_c3248302": n_join_miss,
        "n_not_g34": n_not_g34,
        "n_pred_ge_2024": n_pred_ge_2024,
        "n_fold_drift": n_fold_drift,
        "n_pred_rows": len(preds),
        "n_joined": len(joined),
    }


def run_folds(joined: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_season: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for r in joined:
        by_season[int(r["season"])].append(r)

    beta_rows: List[Dict[str, Any]] = []
    fold_rows: List[Dict[str, Any]] = []
    scored: List[Dict[str, Any]] = []

    def _pack_beta(fold: str, S: int, train: Sequence[Mapping[str, Any]], fit: Mapping[str, Any]) -> Dict[str, Any]:
        b = fit["beta"]
        se = fit["se"]
        lo = fit["ci_lo"]
        hi = fit["ci_hi"]
        seasons = sorted({int(r["season"]) for r in train})
        return {
            "fold": fold,
            "S": S,
            "train_seasons": ",".join(str(s) for s in seasons) if seasons else "",
            "n_train": fit["n"],
            "empty_design": int(bool(fit["empty_design"])),
            "beta_rest_diff": b[0],
            "beta_rest_diff_se_hc1": se[0],
            "beta_rest_diff_ci95_lo": lo[0],
            "beta_rest_diff_ci95_hi": hi[0],
            "beta_short_home": b[1],
            "beta_short_home_se_hc1": se[1],
            "beta_short_home_ci95_lo": lo[1],
            "beta_short_home_ci95_hi": hi[1],
            "beta_short_away": b[2],
            "beta_short_away_se_hc1": se[2],
            "beta_short_away_ci95_lo": lo[2],
            "beta_short_away_ci95_hi": hi[2],
            "beta_missing_ind": b[3],
            "beta_missing_ind_se_hc1": se[3],
            "beta_missing_ind_ci95_lo": lo[3],
            "beta_missing_ind_ci95_hi": hi[3],
        }

    for fold, S in FOLD_S.items():
        train = [r for r in joined if int(r["season"]) < S]
        eval_g = [r for r in joined if int(r["season"]) == S]
        x = [_x_rest_row(r) for r in train]
        y = [float(r["m"]) - float(r["pm_G34"]) for r in train]
        fit = fit_beta_rest_only(x, y)
        beta = fit["beta"]
        mae_g34 = _mae([r["pm_G34"] for r in eval_g], [r["m"] for r in eval_g])
        pm_drs = []
        for r in eval_g:
            pdr = _pm_dr(r["pm_G34"], _x_rest_row(r), beta)
            pm_drs.append(pdr)
            scored.append({**dict(r), "pm_DR": pdr, "beta_fold": fold, "n_train": fit["n"]})
        mae_dr = _mae(pm_drs, [r["m"] for r in eval_g])
        beta_rows.append(_pack_beta(fold, S, train, fit))
        fold_rows.append(
            {
                "fold": fold,
                "S": S,
                "n_eval": len(eval_g),
                "n_train": fit["n"],
                "empty_design": int(bool(fit["empty_design"])),
                "mae_G34": mae_g34,
                "mae_DR": mae_dr,
                "delta_DR": mae_g34 - mae_dr,
                "surface": "primary_oof",
            }
        )
        print(
            f"[fold] {fold} S={S} n_train={fit['n']} n_eval={len(eval_g)} "
            f"empty={fit['empty_design']} mae_G34={mae_g34:.6f} mae_DR={mae_dr:.6f}",
            flush=True,
        )

    # 2023 supportive: β_rest frozen from ≤2022 (no 2023 in X).
    train23 = [r for r in joined if int(r["season"]) <= 2022]
    eval23 = [r for r in joined if int(r["season"]) == 2023]
    x23 = [_x_rest_row(r) for r in train23]
    y23 = [float(r["m"]) - float(r["pm_G34"]) for r in train23]
    fit23 = fit_beta_rest_only(x23, y23)
    rows23: List[Dict[str, Any]] = []
    pm23 = []
    for r in eval23:
        pdr = _pm_dr(r["pm_G34"], _x_rest_row(r), fit23["beta"])
        pm23.append(pdr)
        rows23.append({**dict(r), "pm_DR": pdr, "beta_fold": "S2023_supportive", "n_train": fit23["n"]})
    mae_g34_23 = _mae([r["pm_G34"] for r in eval23], [r["m"] for r in eval23])
    mae_dr_23 = _mae(pm23, [r["m"] for r in eval23])
    beta_rows.append(_pack_beta("S2023_supportive", 2023, train23, fit23))
    fold_rows.append(
        {
            "fold": "S2023_supportive",
            "S": 2023,
            "n_eval": len(eval23),
            "n_train": fit23["n"],
            "empty_design": int(bool(fit23["empty_design"])),
            "mae_G34": mae_g34_23,
            "mae_DR": mae_dr_23,
            "delta_DR": mae_g34_23 - mae_dr_23,
            "surface": "supportive_2023",
        }
    )
    print(
        f"[fold] S2023_supportive n_train={fit23['n']} n_eval={len(eval23)} "
        f"mae_G34={mae_g34_23:.6f} mae_DR={mae_dr_23:.6f}",
        flush=True,
    )
    return {
        "beta_rows": beta_rows,
        "fold_rows": fold_rows,
        "oof": scored,
        "rows23": rows23,
        "fit23": fit23,
    }


def short_rest_subset(rows: Sequence[Mapping[str, Any]], *, label: str) -> Dict[str, Any]:
    sub = [r for r in rows if float(r["short_h"]) == 1.0 or float(r["short_a"]) == 1.0]
    if not sub:
        return {"label": label, "n": 0, "supportive": True}
    m = metrics_block(
        [r["m"] for r in sub],
        [r["mm"] for r in sub],
        [r["pm_DR"] for r in sub],
        [r["pm_G34"] for r in sub],
        [r["pm_epa"] for r in sub],
        seasons=[int(r["season"]) for r in sub],
        label=label,
    )
    m["supportive"] = True
    m["cannot_alone_PASS"] = True
    return m


def _fmt(x: Any, nd: int = 6) -> str:
    if x is None:
        return ""
    try:
        if isinstance(x, float) and not math.isfinite(x):
            return ""
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def write_report(
    path: Path,
    *,
    forecast_ts: str,
    counts: Mapping[str, Any],
    bind: Mapping[str, Any],
    sup: Mapping[str, Any],
    short: Mapping[str, Any],
    artifact_sha8: Mapping[str, str],
) -> str:
    pm = bind["path_m"]
    vg = bind["vs_g34"]
    lines = [
        "# Experiment D-R — honest schedule-rest on frozen G34 (t4618u)",
        "",
        "**EXP D-R ONLY · CERT=0 · NFL NO-GO · F2 FROZEN · sealed=1 · #648 DRAFT · do not merge**",
        "",
        f"**RESEARCH VERDICT (STOP BOX, binding pooled ≤2022 OOF): `{counts['verdict']}`**",
        "",
        f"Path M={'PASS' if pm['pass'] else 'FAIL'} · vs G34={'PASS' if vg['pass'] else 'FAIL'} · "
        f"D4 artifacts={'PASS' if counts['d4_artifacts_pass'] else 'FAIL'} · "
        f"2023 cannot-alone-PASS · floor=0.05 · FEAS §8 withdrawn",
        "",
        f"Filed `{forecast_ts}`. Paper/file evidence only. No Odds / merge / deploy / CERT claim.",
        "",
        "## Authority",
        "",
        "| item | sha8 |",
        "|---|---|",
        f"| Ryan CLEAR t4618u | `{DECISION_SHA8}` |",
        f"| CoS execute order | `{COS_ORDER_SHA8}` |",
        f"| PASS_PROTOCOL | `{PASS_PROTOCOL_SHA8}` |",
        f"| FREEZE D6=(B) | `{FREEZE_D6_SHA8}` |",
        f"| ACK D6/D7 | `{ACK_SHA8}` |",
        f"| Alex STOP ERRATUM | `{STOP_ERRATUM_SHA8}` |",
        f"| FEAS (frozen; §8 withdrawn) | `{FEAS_SHA8}` |",
        f"| H2 FROZEN | `{H2_SHA8}` |",
        f"| G34 comparator | `{COMPARATOR_SHA8}` |",
        "",
        "**Institutional memory:** `no prior grades` for this D-R execute product. "
        "Forward-only from ACK `82c71d64` · FEAS `9906430e` · H2 `db2cf4b2` · G34 `c3248302`.",
        "",
        "## Frozen design",
        "",
        "- `X_rest` = exactly 4 columns: `drest_clip`, `short_h`, `short_a`, `rest_missing`",
        "- `pm_DR = pm_G34 + X_rest · β_rest` (intercept-free OLS on seasons `< S` only)",
        "- HC1 diagnostic; point β used. G34 β/HFA/ratings **not** refit.",
        "- Rest from `nflverse_gameday` date-diff; `>21d` → NaN; clip ±7; short ≤5.",
        "- No DOW heuristic. No emit placeholder 7.0. No 2012 PBP. No `simulate_nfl_game`.",
        "- F1 n_train=0 on `c3248302` (2013 not on comparator) → `β_rest := 0` (no rest adjustment).",
        "- Binding F1–F9 ≤2022 OOF. 2023 supportive. 2024+ forbidden.",
        "",
        "## STOP BOX (Alex 6bd07cc8 §5 / ACK 82c71d64 D7)",
        "",
        "RESEARCH PASS iff ALL of:",
        "",
        "1. Path M: `m ~ a + b·mm + c·pm_DR` (OLS HC1); c>0 and 95% CI excludes 0.",
        "2. vs G34: paired boot B=10000 seed 4141 percentile CI on Δ_DR excludes 0 "
        "AND point Δ_DR ≥ 0.05.",
        "3. D4 artifacts (β_rest HC1 incl `beta_missing_ind`; short-rest subset; missingness rates).",
        "",
        "`Δ_DR = mae_G34 − mae_DR` (market terms cancel; not market-relative).",
        "",
        "### Binding (pooled ≤2022 OOF)",
        "",
        f"- n = {bind['n']}",
        f"- MAE(DR) = {bind['mae_DR']}",
        f"- MAE(G34) = {bind['mae_G34']}",
        f"- MAE(epa, report-only) = {bind['mae_epa']}",
        f"- MAE(market) = {bind['mae_market']}",
        f"- point Δ_DR = {bind['delta_DR']}",
        f"- Path M c = {pm['c']}  HC1 se = {pm['c_se_hc1']}  CI = [{pm['c_ci95_lo']}, {pm['c_ci95_hi']}]  pass={pm['pass']}",
        f"- vs G34 Δ CI = [{vg['delta_ci95_lo']}, {vg['delta_ci95_hi']}]  point_ge_0.05={vg['point_ge_0_05']}  pass={vg['pass']}",
        "",
        "### 2023 supportive (cannot alone PASS)",
        "",
        f"- n = {sup['n']}",
        f"- MAE(DR) = {sup['mae_DR']}",
        f"- point Δ_DR = {sup['delta_DR']}",
        f"- Path M pass={sup['path_m']['pass']}  vs G34 pass={sup['vs_g34']['pass']}",
        "",
        "### D4 short-rest subset (supportive)",
        "",
        f"- n = {short.get('n', 0)}",
        f"- point Δ_DR = {short.get('delta_DR', '')}",
        "",
        "## Artifact sha8",
        "",
        "| artifact | sha8 |",
        "|---|---|",
    ]
    for name, sha8 in sorted(artifact_sha8.items()):
        lines.append(f"| `{name}` | `{sha8}` |")
    lines += [
        "",
        "## Non-claims",
        "",
        "- CERT=0. NFL NO-GO. Coming Soon ON. F2 frozen.",
        "- Research PASS ≠ market bar ≠ CERT. No Odds API. No merge of #646/#647/#648.",
        "- Stop / floor / columns / comparator were not changed post-run.",
        "- FEAS §8 DRAFT not applied. Exp A 0.10 floor not applied.",
        "",
    ]
    return _write_text(path, "\n".join(lines))


def main() -> int:
    _assert_no_forbidden_imports()
    forecast_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[exp-dr] start {forecast_ts} CERT={CERT_CANDIDATE}", flush=True)

    h1 = close_h1()
    if not h1["ok"]:
        counts = {
            "verdict": "BLOCKED",
            "blocked_reasons": h1["blocked_reasons"],
            "cert_candidate": 0,
            "ticket": TICKET,
        }
        _write_json(OUT_DIR / "counts.json", counts)
        print("[exp-dr] BLOCKED " + "; ".join(h1["blocked_reasons"]), flush=True)
        return 3

    selected = _load_json(SELECTED_PATH)
    if str(selected.get("cfg_id") or "") != CFG_ID:
        counts = {
            "verdict": "BLOCKED",
            "blocked_reasons": [f"selected_cell cfg_id={selected.get('cfg_id')} != G34"],
            "cert_candidate": 0,
            "ticket": TICKET,
        }
        _write_json(OUT_DIR / "counts.json", counts)
        print("[exp-dr] BLOCKED selected_cell not G34", flush=True)
        return 3

    games = _load_csv(GAMES_PATH)
    emit = _load_csv(Path(h1["emit_path"]))
    oos = _load_csv(OOS_PATH)
    preds = _load_csv(PRED_PATH)

    rest_rows, coverage = build_rest_emit(games, emit, oos)
    rest_fields = [
        "season",
        "week",
        "game_id",
        "home",
        "away",
        "game_date",
        "kickoff_utc",
        "rest_days_home",
        "rest_days_away",
        "rest_home_nan",
        "rest_away_nan",
        "r_prime_home",
        "r_prime_away",
        "drest_clip",
        "short_h",
        "short_a",
        "rest_missing",
    ]
    rest_sha = _write_csv(OUT_DIR / "rest_emit.csv", rest_fields, rest_rows)
    print(f"[h1] rest_emit.csv sha256={rest_sha} sha8={_sha8(rest_sha)} (hashed before OLS)", flush=True)

    fail_reasons: List[str] = []
    n_rows_ge_2024 = int(coverage["n_games_ge_2024"] + coverage["n_emit_ge_2024"])
    if n_rows_ge_2024 > 0:
        fail_reasons.append(f"n_rows_season_ge_2024={n_rows_ge_2024}")
    if coverage["n_gameday_mismatch_emit_games"] > 0:
        fail_reasons.append(f"n_gameday_mismatch_emit_games={coverage['n_gameday_mismatch_emit_games']}")
    if coverage["n_oos_gameday_mismatch"] > 0:
        fail_reasons.append(f"n_oos_gameday_mismatch={coverage['n_oos_gameday_mismatch']}")
    if coverage["n_placeholder_used"] > 0:
        fail_reasons.append("emit placeholder rest used as feature")
    if coverage["n_gameday_empty"] > 0:
        fail_reasons.append(f"n_gameday_empty={coverage['n_gameday_empty']}")

    joined, jn = join_predictions(rest_rows, preds)
    n_rows_ge_2024 += int(jn["n_pred_ge_2024"])
    if jn["n_pred_ge_2024"] > 0:
        fail_reasons.append(f"n_pred_season_ge_2024={jn['n_pred_ge_2024']}")
    if jn["n_join_miss_vs_c3248302"] > 0:
        fail_reasons.append(f"n_join_miss_vs_c3248302={jn['n_join_miss_vs_c3248302']}")
    if jn["n_not_g34"] > 0:
        fail_reasons.append(f"n_not_g34={jn['n_not_g34']}")
    if jn["n_fold_drift"] > 0:
        fail_reasons.append(f"n_fold_drift={jn['n_fold_drift']}")
    if jn["n_pred_rows"] != N_PRED_EXPECT:
        fail_reasons.append(f"n_pred_rows={jn['n_pred_rows']} want={N_PRED_EXPECT}")

    if fail_reasons:
        counts = {
            "verdict": "FAIL",
            "fail_reasons": fail_reasons,
            "n_rows_season_ge_2024": n_rows_ge_2024,
            "n_join_miss_vs_c3248302": jn["n_join_miss_vs_c3248302"],
            "n_gameday_mismatch_emit_games": coverage["n_gameday_mismatch_emit_games"],
            "cert_candidate": 0,
            "ticket": TICKET,
            **{k: coverage[k] for k in (
                "n_games",
                "n_rest_nan_home",
                "n_rest_nan_away",
                "n_drest_nonzero",
                "n_short_h",
                "n_short_a",
            )},
        }
        _write_json(OUT_DIR / "counts.json", counts)
        print("[exp-dr] FAIL " + "; ".join(fail_reasons), flush=True)
        return 2

    result = run_folds(joined)
    oof = result["oof"]
    rows23 = result["rows23"]
    if len(oof) != N_OOF_EXPECT:
        fail_reasons.append(f"n_oof_le_2022={len(oof)} want={N_OOF_EXPECT}")
    if len(rows23) != N_2023_EXPECT:
        fail_reasons.append(f"n_2023={len(rows23)} want={N_2023_EXPECT}")
    if any(int(r["season"]) >= 2023 for r in oof):
        fail_reasons.append("2023+ leaked into binding OOF")
    if any(int(r["season"]) == 2023 for r in result["beta_rows"][0:9] if False):
        pass
    # 2023 must not appear in F1–F9 train seasons.
    for br in result["beta_rows"]:
        if str(br["fold"]).startswith("F") and "2023" in str(br["train_seasons"]):
            fail_reasons.append(f"2023 in {br['fold']} train")

    bind = metrics_block(
        [r["m"] for r in oof],
        [r["mm"] for r in oof],
        [r["pm_DR"] for r in oof],
        [r["pm_G34"] for r in oof],
        [r["pm_epa"] for r in oof],
        seasons=[int(r["season"]) for r in oof],
        label="pooled_le_2022_OOF",
    )
    sup = metrics_block(
        [r["m"] for r in rows23],
        [r["mm"] for r in rows23],
        [r["pm_DR"] for r in rows23],
        [r["pm_G34"] for r in rows23],
        [r["pm_epa"] for r in rows23],
        seasons=[int(r["season"]) for r in rows23],
        label="2023_supportive",
    )
    short = short_rest_subset(oof, label="short_rest_subset_binding_supportive")
    short23 = short_rest_subset(rows23, label="short_rest_subset_2023_supportive")

    if fail_reasons:
        counts = {
            "verdict": "FAIL",
            "fail_reasons": fail_reasons,
            "n_oof_le_2022": len(oof),
            "n_2023": len(rows23),
            "n_rows_season_ge_2024": n_rows_ge_2024,
            "n_join_miss_vs_c3248302": jn["n_join_miss_vs_c3248302"],
            "n_gameday_mismatch_emit_games": coverage["n_gameday_mismatch_emit_games"],
            "cert_candidate": 0,
            "ticket": TICKET,
        }
        _write_json(OUT_DIR / "counts.json", counts)
        print("[exp-dr] FAIL " + "; ".join(fail_reasons), flush=True)
        return 2

    artifact_sha: Dict[str, str] = {"rest_emit.csv": rest_sha}

    beta_fields = [
        "fold",
        "S",
        "train_seasons",
        "n_train",
        "empty_design",
        "beta_rest_diff",
        "beta_rest_diff_se_hc1",
        "beta_rest_diff_ci95_lo",
        "beta_rest_diff_ci95_hi",
        "beta_short_home",
        "beta_short_home_se_hc1",
        "beta_short_home_ci95_lo",
        "beta_short_home_ci95_hi",
        "beta_short_away",
        "beta_short_away_se_hc1",
        "beta_short_away_ci95_lo",
        "beta_short_away_ci95_hi",
        "beta_missing_ind",
        "beta_missing_ind_se_hc1",
        "beta_missing_ind_ci95_lo",
        "beta_missing_ind_ci95_hi",
    ]
    artifact_sha["betas_rest_by_fold.csv"] = _write_csv(
        OUT_DIR / "betas_rest_by_fold.csv",
        beta_fields,
        [
            {
                **br,
                **{k: _fmt(br[k], 10) for k in br if k.startswith("beta_")},
            }
            for br in result["beta_rows"]
        ],
    )
    artifact_sha["fold_table.csv"] = _write_csv(
        OUT_DIR / "fold_table.csv",
        ["fold", "S", "n_eval", "n_train", "empty_design", "mae_G34", "mae_DR", "delta_DR", "surface"],
        [
            {
                **fr,
                "mae_G34": _fmt(fr["mae_G34"]),
                "mae_DR": _fmt(fr["mae_DR"]),
                "delta_DR": _fmt(fr["delta_DR"]),
            }
            for fr in result["fold_rows"]
        ],
    )
    pred_fields = [
        "season",
        "week",
        "game_id",
        "home",
        "away",
        "fold",
        "cfg_id",
        "neutral",
        "m",
        "mm",
        "pm_epa",
        "pm_G34",
        "pm_DR",
        "drest_clip",
        "short_h",
        "short_a",
        "rest_missing",
        "rest_days_home",
        "rest_days_away",
    ]
    pred_out = []
    for r in result["oof"] + result["rows23"]:
        pred_out.append(
            {
                **r,
                "m": _fmt(r["m"]),
                "mm": _fmt(r["mm"]),
                "pm_epa": _fmt(r["pm_epa"]),
                "pm_G34": _fmt(r["pm_G34"]),
                "pm_DR": _fmt(r["pm_DR"]),
                "drest_clip": _fmt(r["drest_clip"]),
                "short_h": int(r["short_h"]),
                "short_a": int(r["short_a"]),
                "rest_missing": int(r["rest_missing"]),
            }
        )
    artifact_sha["predictions_dr.csv"] = _write_csv(OUT_DIR / "predictions_dr.csv", pred_fields, pred_out)

    missingness = {
        "source": "hashed rest_emit from nflverse_gameday date-diff (not emit placeholder 7.0)",
        "rest_emit_sha256": rest_sha,
        "panel": {
            "n_games": coverage["n_games"],
            "n_rest_nan_home": coverage["n_rest_nan_home"],
            "n_rest_nan_away": coverage["n_rest_nan_away"],
            "n_rest_missing": coverage["n_rest_missing"],
            "n_drest_nonzero": coverage["n_drest_nonzero"],
            "n_short_h": coverage["n_short_h"],
            "n_short_a": coverage["n_short_a"],
            "rate_nan_home": coverage["rate_nan_home"],
            "rate_nan_away": coverage["rate_nan_away"],
            "rate_rest_missing": coverage["rate_rest_missing"],
            "rate_drest_nonzero": coverage["rate_drest_nonzero"],
            "rate_short_h": coverage["rate_short_h"],
            "rate_short_a": coverage["rate_short_a"],
        },
        "binding_oof": {
            "n": len(oof),
            "n_rest_missing": sum(1 for r in oof if float(r["rest_missing"]) == 1.0),
            "n_short_h": sum(1 for r in oof if float(r["short_h"]) == 1.0),
            "n_short_a": sum(1 for r in oof if float(r["short_a"]) == 1.0),
            "n_drest_nonzero": sum(1 for r in oof if float(r["drest_clip"]) != 0.0),
        },
        "supportive_2023": {
            "n": len(rows23),
            "n_rest_missing": sum(1 for r in rows23 if float(r["rest_missing"]) == 1.0),
            "n_short_h": sum(1 for r in rows23 if float(r["short_h"]) == 1.0),
            "n_short_a": sum(1 for r in rows23 if float(r["short_a"]) == 1.0),
        },
        "recipe": coverage["recipe"],
    }
    artifact_sha["missingness.json"] = _write_json(OUT_DIR / "missingness.json", missingness)
    artifact_sha["short_rest_subset.json"] = _write_json(
        OUT_DIR / "short_rest_subset.json",
        {"binding": short, "supportive_2023": short23, "cannot_alone_PASS": True},
    )
    artifact_sha["metrics_binding.json"] = _write_json(OUT_DIR / "metrics_binding.json", bind)
    artifact_sha["metrics_2023.json"] = _write_json(OUT_DIR / "metrics_2023.json", sup)

    d4_ok = bool(
        "beta_missing_ind" in beta_fields
        and (OUT_DIR / "betas_rest_by_fold.csv").is_file()
        and (OUT_DIR / "short_rest_subset.json").is_file()
        and (OUT_DIR / "missingness.json").is_file()
        and missingness["panel"]["n_games"] == coverage["n_games"]
    )
    path_m_pass = bool(bind["path_m"]["pass"])
    vs_g34_pass = bool(bind["vs_g34"]["pass"])
    # Binding decides. 2023 cannot alone PASS. STOP BOX = ALL conjuncts.
    verdict = "PASS" if (path_m_pass and vs_g34_pass and d4_ok) else "FAIL"

    stop_rule = {
        "authority": "Alex 6bd07cc8 §5 STOP BOX; ACK 82c71d64 D7; FEAS 9906430e §8 withdrawn",
        "void_if_changed_post_run": True,
        "binding_surface": "pooled_le_2022_OOF",
        "supportive_2023_cannot_alone_PASS": True,
        "x_rest_cols": list(X_COLS),
        "equation": "pm_DR = pm_G34 + X_rest · beta_rest",
        "fit": "intercept-free OLS (m-pm_G34)~X_rest on seasons < S; HC1 diagnostic",
        "B": BOOT_B,
        "seed": BOOT_SEED,
        "research_floor_vs_g34": RESEARCH_FLOOR,
        "floor_0_10_applied": False,
        "feas_section_8_applied": False,
        "path_m_mandatory": True,
        "epa_secondary_report_only": True,
        "binding": bind,
        "supportive_2023": sup,
        "d4_artifacts_pass": d4_ok,
        "verdict_binding": verdict,
        "conjuncts": {
            "path_m": path_m_pass,
            "vs_g34": vs_g34_pass,
            "d4_artifacts": d4_ok,
        },
    }
    artifact_sha["stop_rule.json"] = _write_json(OUT_DIR / "stop_rule.json", stop_rule)

    counts = {
        "authority": {
            "decision_sha8": DECISION_SHA8,
            "cos_order_sha8": COS_ORDER_SHA8,
            "pass_protocol_sha8": PASS_PROTOCOL_SHA8,
            "freeze_d6_sha8": FREEZE_D6_SHA8,
            "ack_sha8": ACK_SHA8,
            "stop_erratum_sha8": STOP_ERRATUM_SHA8,
            "feas_sha8": FEAS_SHA8,
            "h2_sha8": H2_SHA8,
            "comparator_sha8": COMPARATOR_SHA8,
        },
        "ticket": TICKET,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "coming_soon": True,
        "nfl_nogo": True,
        "f2_frozen": True,
        "simulate_nfl_game_called": False,
        "odds_api_called": False,
        "locked_scoring_touched": False,
        "n_games": coverage["n_games"],
        "n_games_expect": N_GAMES_EXPECT,
        "n_oof_le_2022": bind["n"],
        "n_2023": sup["n"],
        "n_rows_season_ge_2024": n_rows_ge_2024,
        "n_oos_dropped_ge_2024": coverage["n_oos_dropped_ge_2024"],
        "n_join_miss_vs_c3248302": jn["n_join_miss_vs_c3248302"],
        "n_gameday_mismatch_emit_games": coverage["n_gameday_mismatch_emit_games"],
        "n_oos_gameday_mismatch": coverage["n_oos_gameday_mismatch"],
        "n_rest_nan_home": coverage["n_rest_nan_home"],
        "n_rest_nan_away": coverage["n_rest_nan_away"],
        "n_rest_missing": coverage["n_rest_missing"],
        "n_drest_nonzero": coverage["n_drest_nonzero"],
        "n_short_h": coverage["n_short_h"],
        "n_short_a": coverage["n_short_a"],
        "selected_cfg_id": CFG_ID,
        "verdict": verdict,
        "path_m_pass": path_m_pass,
        "vs_g34_pass": vs_g34_pass,
        "d4_artifacts_pass": d4_ok,
        "delta_DR_binding": bind["delta_DR"],
        "research_floor_vs_g34": RESEARCH_FLOOR,
        "seasons_beating_market_binding": bind["seasons_beating_market"],
        "h2_sha256": H2_SHA256,
        "games_csv_sha256": GAMES_CSV_SHA256,
        "oos_sha256": OOS_SHA256,
        "emit_sha256": EMIT_SHA256,
        "predictions_sha256": PRED_SHA256,
        "rest_emit_sha256": rest_sha,
        "bootstrap_B": BOOT_B,
        "bootstrap_seed": BOOT_SEED,
        "x_rest_cols": list(X_COLS),
        "f1_empty_design": bool(result["beta_rows"][0]["empty_design"]),
        "cert_note": (
            "Research PASS ≠ market bar ≠ CERT. Future CERT still needs "
            "mae_DR ≤ mae_market with uncertainty and/or seasons_beating_market>0 "
            "plus IMV/Ryan CLEAR. Not claimed here."
        ),
    }
    artifact_sha["counts.json"] = _write_json(OUT_DIR / "counts.json", counts)

    sha8_table = {name: _sha8(sha) for name, sha in artifact_sha.items()}
    report_sha = write_report(
        OUT_DIR / "REPORT.md",
        forecast_ts=forecast_ts,
        counts=counts,
        bind=bind,
        sup=sup,
        short=short,
        artifact_sha8=sha8_table,
    )
    artifact_sha["REPORT.md"] = report_sha
    sha8_table["REPORT.md"] = _sha8(report_sha)
    artifact_sha["artifact_sha8.json"] = _write_json(OUT_DIR / "artifact_sha8.json", sha8_table)

    manifest_out = {
        "run_id": f"nfl-exp-dr-{TICKET}-{forecast_ts.replace(':', '').replace('-', '')}",
        "ticket": TICKET,
        "forecast_ts_utc": forecast_ts,
        "verdict": verdict,
        "authority": counts["authority"],
        "h1_hashes": dict(_H1_HASHES),
        "artifact_sha256": artifact_sha,
        "cert_candidate": 0,
        "simulate_nfl_game_called": False,
        "stop_rule_unchanged": True,
        "x_rest_cols": list(X_COLS),
    }
    artifact_sha["manifest.json"] = _write_json(OUT_DIR / "manifest.json", manifest_out)
    sha8_table["manifest.json"] = _sha8(artifact_sha["manifest.json"])
    os.chmod(OUT_DIR / "artifact_sha8.json", 0o644)
    artifact_sha["artifact_sha8.json"] = _write_json(OUT_DIR / "artifact_sha8.json", sha8_table)

    all_sums = dict(_H1_HASHES)
    all_sums["outputs/rest_emit.csv"] = rest_sha
    all_sums.update({f"outputs/{k}": v for k, v in artifact_sha.items()})
    _write_sha256sums(OUT_DIR / "SHA256SUMS", all_sums)
    os.chmod(OUT_DIR / "SHA256SUMS", FILE_MODE)

    _assert_no_forbidden_imports()
    print(
        f"[exp-dr] verdict={verdict} path_m={path_m_pass} vs_g34={vs_g34_pass} "
        f"d4={d4_ok} delta={bind['delta_DR']:.4f} out={OUT_DIR}",
        flush=True,
    )
    return 0 if verdict in {"PASS", "FAIL"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
