#!/usr/bin/env python3
"""t4602u Experiment A ONLY — 54-cell ridge-joint fold validation (CERT=0).

Authority
  DECISION_RYAN_t4602u CLEAR Exp A ONLY     sha8 1992ea62
  COS_ORDER_CURSOR_t4602u_EXP_A_EXECUTE     sha8 3e500d55
  IMV PREFLIGHT LOOK (full §4 emit)         sha8 a5083123
  H2 FROZEN manifest                        sha8 db2cf4b2
  Exp E IMV_PASS                            sha8 3d79c41b
  PASS_PROTOCOL v2                          sha8 60c18a4c
  Alex SPEC §4                              sha8 ddffb72e
  ESTIMATOR addendum                        sha8 84a28a05
  Cursor ACK                                sha8 6fcc0af6
  FEASIBILITY v1.1                          sha8 15ee3a1b

Does NOT: call Odds, merge #646/#647/#648, touch LOCKED_SCORING /
config_overrides, call simulate_nfl_game, touch F2 PHI@WSH, deploy, publish,
claim CERT, redesign, or use 2024+.

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
from datetime import datetime, timezone
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

from t4602u_exp_a_ridge_joint import (  # noqa: E402
    CANONICAL_TEAMS,
    ESTIMATOR_ID,
    N0_BASE,
    N_TEAMS,
    TEAM_INDEX,
    RidgeParams,
    fit_beta_fold,
    fit_joint,
    predict_margin_a,
    rating_diff_home,
    select_cell,
    self_check,
    shrink_offseason,
    week_weight,
    ols_hc1,
    hc1_ci,
)

# Forbidden production surfaces — never imported.
_FORBIDDEN_IMPORTS = (
    "simulate_nfl_game",
    "LOCKED_SCORING",
    "config_overrides",
    "NflGameInputs",
)

TICKET = "t4602u"
LABEL = "RESEARCH_DIAGNOSTIC_EXP_A"
CERT_CANDIDATE = 0
FILE_MODE = 0o444
BOOT_B = 10000
BOOT_SEED = 4141
Z95 = 1.96
EPS = 1e-9

DECISION_SHA8 = "1992ea62"
COS_ORDER_SHA8 = "3e500d55"
IMV_LOOK_SHA8 = "a5083123"
H2_SHA256 = "db2cf4b24bfa9c441f7eafea19d5c24624541f9cb7225759e9882f61cb6c6463"
H2_SHA8 = "db2cf4b2"
IMV_PASS_E = "3d79c41b"
H1_ADDENDUM = "5d426ae9"
H1_SUMS_SHA256 = "97774e08985cba90f23196857807b3e69144630867bc9d000007cfa4e93bc8da"
TIP_E_H1 = "0940a28941959c77d510c05e9e56198a08812869"
COUNTS_E_SHA256 = "b0365365251400715144ff5fdb3ddeae68024a33efccade044249e2e1fceeec2"
GAMES_CSV_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OOS_SHA256 = "1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed"
EMIT_SHA256 = "02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2"
N_GAMES_EXPECT = 2992
PBP_SEASONS = list(range(2012, 2024))

PBP_SHA256 = {
    2012: "447b90789104aac70427ec9d3b51df7247234029d0ecabd269279369b1cc6278",
    2013: "f454605a1983b3946baf0ffadf3a0b9f5e04735c4b84732e0483f2049a780d00",
    2014: "54c01408d8f0ff9e013a4ea51428b91d610101f72545d082e932f5710e2fb4f7",
    2015: "01b5ae7d06633a2e66b418404461a3d4ff055ad2f3a87d453cebcc8d3fda7ed9",
    2016: "95eba04e2145e3c1c8ca502f2a3a76cfb0a5990680c3fb480f02a74a45f54a3b",
    2017: "84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710",
    2018: "2e6f2dce7c7ebd46e985cabe0c17eb72b39a77f98cb4478409294f50b5820150",
    2019: "60c3067017db2d28a78f66a79b657268be8578d9a5288e6a827efdcd7fe42540",
    2020: "8889f5d8782b5c5dce3c3644acdc0322b228a7e9cb13fa36cbac250e260e9f60",
    2021: "333ad34378e5339d5172717cc83378e908daf02c8699416ab3e17c2ec10f78d8",
    2022: "931121d8897779d7944e2a293e92ed8799c8e5cceef84096ac42339003fedc09",
    2023: "bd3484731408def6b0ec93225bba2bd7b2c65769ca707a2b9444d891abdc6776",
}

H2_PATH = HERE / "t4586u_exp_a_h2_manifest_freeze" / "CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json"
H1_SUMS_PATH = HERE / "t4586u_exp_e_kickoff_asof" / "SHA256SUMS"
GAMES_PATH = HERE / "t4586u_exp_e_inputs" / "games.csv"
OOS_PATH = HERE / "t4586u_exp_e_inputs" / "historical_oos_games.csv"
OUT_DIR = HERE / "t4602u_exp_a"
CACHE_DIR = Path(os.environ.get("T4602U_CACHE", "/tmp/nflverse-pbp-exp-e"))

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


def _write_json(path: Path, obj: Any) -> str:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    _chmod_ro(path)
    return digest


def _write_text(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    digest = _sha256_file(path)
    _chmod_ro(path)
    return digest


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
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
    print(f"[h1] git-show #646 emit CSV (cite; not a merge)", flush=True)
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", EMIT_GIT_REF])
    dest.write_bytes(raw)


def close_h1() -> Dict[str, Any]:
    """Hash-pin every Exp A input BEFORE any parquet/CSV parse of those bytes."""
    global _H1_CLOSED
    _H1_CLOSED = False
    _H1_HASHES.clear()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    blocked: List[str] = []

    h2_sha = _register_hash("CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json", H2_PATH)
    if h2_sha != H2_SHA256:
        blocked.append(f"H2 manifest sha mismatch got={h2_sha} want={H2_SHA256}")

    h1_sums_sha = _register_hash("exp_e_h1_SHA256SUMS", H1_SUMS_PATH)
    if h1_sums_sha != H1_SUMS_SHA256:
        blocked.append(f"H1 SHA256SUMS mismatch got={h1_sums_sha} want={H1_SUMS_SHA256}")

    games_sha = _register_hash("games.csv", GAMES_PATH)
    if games_sha != GAMES_CSV_SHA256:
        blocked.append(f"games.csv sha mismatch got={games_sha} want={GAMES_CSV_SHA256}")

    oos_sha = _register_hash("historical_oos_games.csv", OOS_PATH)
    if oos_sha != OOS_SHA256:
        blocked.append(f"oos sha mismatch got={oos_sha} want={OOS_SHA256}")

    emit_path = CACHE_DIR / "epa_wf_features_2013_2023.csv"
    _extract_emit(emit_path)
    emit_sha = _register_hash("epa_wf_features_2013_2023.csv", emit_path)
    if emit_sha != EMIT_SHA256:
        blocked.append(f"emit csv sha mismatch got={emit_sha} want={EMIT_SHA256}")

    pbp_map: Dict[str, str] = {}
    for season in PBP_SEASONS:
        dest = CACHE_DIR / f"play_by_play_{season}.parquet"
        digest = _register_hash(f"play_by_play_{season}.parquet", dest)
        pbp_map[str(season)] = digest
        want = PBP_SHA256[season]
        if digest != want:
            blocked.append(f"pbp {season} sha mismatch got={digest} want={want}")

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


def load_panel(emit_path: Path) -> Tuple[List[Dict[str, Any]], int]:
    """Join games.csv + emit 02f6b2e2 + OOS 1ee90fac. Drop 2024+ (count them)."""
    games = _load_csv(GAMES_PATH)
    emit = _load_csv(Path(emit_path))
    oos = _load_csv(OOS_PATH)

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
    panel: List[Dict[str, Any]] = []
    missing = {"emit": 0, "oos": 0, "epa": 0, "score": 0, "market": 0, "kickoff": 0}
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
            missing["emit"] += 1
            continue
        oos_row = oos_by_key.get((season, week, home, away))
        if oos_row is None:
            missing["oos"] += 1
            continue
        epa_spread = _finite(er.get("epa_trailing_spread_home"))
        hs = _finite(oos_row.get("home_score"))
        aws = _finite(oos_row.get("away_score"))
        mkt = _finite(oos_row.get("market_spread_home"))
        ko = _parse_iso(g.get("kickoff_utc") or "")
        if epa_spread is None:
            missing["epa"] += 1
            continue
        if hs is None or aws is None:
            missing["score"] += 1
            continue
        if mkt is None:
            missing["market"] += 1
            continue
        if ko is None:
            missing["kickoff"] += 1
            continue
        loc = str(g.get("nflverse_location") or "").strip()
        neutral = loc.lower() == "neutral"
        m = float(hs) - float(aws)
        mm = -float(mkt)
        pm_epa = -float(epa_spread)
        panel.append(
            {
                "season": season,
                "week": week,
                "game_id": gid,
                "home": home,
                "away": away,
                "kickoff_utc": g["kickoff_utc"],
                "kickoff_ts": ko.timestamp(),
                "neutral": neutral,
                "home_ind": 0.0 if neutral else 1.0,
                "m": m,
                "mm": mm,
                "pm_epa": pm_epa,
                "location": loc,
            }
        )

    panel.sort(key=lambda r: (r["kickoff_ts"], r["game_id"]))
    print(
        f"[panel] n={len(panel)} missing={missing} n_games_ge_2024={n_games_ge_2024} "
        f"n_oos_dropped_ge_2024={n_oos_ge_2024}",
        flush=True,
    )
    # 2024+ OOS rows are the protected holdout: dropped, not used. FAIL only if
    # they enter the analysis panel (games.csv / emit / PBP used rows).
    return panel, n_games_ge_2024, n_oos_ge_2024


def load_team_games() -> Tuple[Dict[str, Any], int]:
    """Team-game EPA observations from H1-pinned PBP. OT excluded. 2024+ counted then dropped."""
    _assert_h1()
    import pandas as pd
    import pyarrow.parquet as pq

    rows: List[Dict[str, Any]] = []
    n_ge_2024 = 0
    keep = [
        "season",
        "week",
        "game_id",
        "posteam",
        "defteam",
        "home_team",
        "away_team",
        "play_type",
        "epa",
        "qtr",
        "season_type",
        "location",
    ]
    for season in PBP_SEASONS:
        dest = CACHE_DIR / f"play_by_play_{season}.parquet"
        print(f"[pbp] load {season} bytes={dest.stat().st_size}", flush=True)
        schema = list(pq.ParquetFile(str(dest)).schema.names)
        present = [c for c in keep if c in schema]
        df = pd.read_parquet(dest, columns=present)
        if "season" not in df.columns:
            df["season"] = season
        season_num = pd.to_numeric(df["season"], errors="coerce")
        n_ge_2024 += int((season_num >= 2024).sum())
        df = df[season_num < 2024]
        if "season_type" in df.columns:
            st = df["season_type"].astype(str).str.upper()
            df = df[st.isin(("REG", "POST", "REGULAR", "POSTSEASON"))]
        df = df[df["play_type"].astype(str).isin(("pass", "run"))]
        if "qtr" in df.columns:
            qtr = pd.to_numeric(df["qtr"], errors="coerce")
            df = df[qtr.isna() | (qtr < 5)]
        df = df[df["posteam"].notna() & df["defteam"].notna() & df["week"].notna()]
        df["epa"] = pd.to_numeric(df["epa"], errors="coerce")
        df = df[df["epa"].notna()]
        df["week"] = pd.to_numeric(df["week"], errors="coerce")
        df = df[df["week"].notna()]
        agg = {
            "y": ("epa", "mean"),
            "n_plays": ("epa", "count"),
            "home_team": ("home_team", "first"),
            "away_team": ("away_team", "first"),
        }
        if "location" in df.columns:
            agg["location"] = ("location", "first")
        g = df.groupby(["season", "week", "game_id", "posteam", "defteam"], observed=True).agg(**agg).reset_index()
        for rec in g.to_dict("records"):
            off = _franchise(rec["posteam"])
            deff = _franchise(rec["defteam"])
            if off not in TEAM_INDEX or deff not in TEAM_INDEX:
                continue
            home_t = _franchise(str(rec.get("home_team") or ""))
            loc = str(rec.get("location") or "").strip()
            neutral = loc.lower() == "neutral"
            home_flag = 0.0 if neutral or off != home_t else 1.0
            rows.append(
                {
                    "season": int(rec["season"]),
                    "week": int(rec["week"]),
                    "game_id": str(rec["game_id"]).strip(),
                    "off": off,
                    "def": deff,
                    "off_idx": TEAM_INDEX[off],
                    "def_idx": TEAM_INDEX[deff],
                    "y": float(rec["y"]),
                    "n_plays": float(rec["n_plays"]),
                    "home": home_flag,
                }
            )
        del df, g
    rows.sort(key=lambda r: (r["season"], r["week"], r["game_id"], r["off"]))
    print(f"[pbp] team_games={len(rows)} n_plays_season_ge_2024={n_ge_2024}", flush=True)
    pack = {
        "rows": rows,
        "by_season": None,
    }
    return pack, n_ge_2024


def _obs_arrays(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    import numpy as np

    n = len(rows)
    return {
        "season": np.array([r["season"] for r in rows], dtype=np.int32),
        "week": np.array([r["week"] for r in rows], dtype=np.int32),
        "game_id": [r["game_id"] for r in rows],
        "off_idx": np.array([r["off_idx"] for r in rows], dtype=np.int64),
        "def_idx": np.array([r["def_idx"] for r in rows], dtype=np.int64),
        "y": np.array([r["y"] for r in rows], dtype=np.float64),
        "n_plays": np.array([r["n_plays"] for r in rows], dtype=np.float64),
        "home": np.array([r["home"] for r in rows], dtype=np.float64),
    }


def walk_rating_diffs(
    obs: Mapping[str, Any],
    panel: Sequence[Mapping[str, Any]],
    params: RidgeParams,
) -> Dict[str, float]:
    """Pregame rating_diff_home for every panel game. Kickoff-honest, season-walk."""
    import numpy as np

    kick_by_gid = {r["game_id"]: float(r["kickoff_ts"]) for r in panel}
    # Off-panel (2012) games get kickoff_ts = season*1e12 + week so they sort inside year.
    n = len(obs["y"])
    kick = np.zeros(n, dtype=np.float64)
    for i, gid in enumerate(obs["game_id"]):
        if gid in kick_by_gid:
            kick[i] = kick_by_gid[gid]
        else:
            kick[i] = float(obs["season"][i]) * 1_000_000.0 + float(obs["week"][i])

    rd: Dict[str, float] = {}
    prior_off = np.zeros(N_TEAMS, dtype=np.float64)
    prior_def = np.zeros(N_TEAMS, dtype=np.float64)

    panel_by_season: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for g in panel:
        panel_by_season[int(g["season"])].append(g)

    for season in range(2012, 2024):
        mask = obs["season"] == season
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            prior_off, prior_def = shrink_offseason(prior_off, prior_def, params.rho_s)
            continue

        # Season-final (for next year's prior) uses all in-season obs.
        if season == 2012 or season not in panel_by_season:
            wks = obs["week"][idx]
            w = obs["n_plays"][idx] * np.array(
                [week_weight(params.rho, int(wks.max()), int(ww)) for ww in wks],
                dtype=np.float64,
            )
            fit = fit_joint(
                obs["y"][idx],
                obs["home"][idx],
                obs["off_idx"][idx],
                obs["def_idx"][idx],
                w,
                prior_off=prior_off,
                prior_def=prior_def,
                n0=params.n0,
                iters=params.iters,
            )
            prior_off, prior_def = shrink_offseason(fit.off, fit.deff, params.rho_s)
            continue

        games = panel_by_season[season]
        # Unique kickoffs among panel games this season.
        kos = sorted({(g["kickoff_ts"], g["week"]) for g in games})
        # Precompute season arrays
        sy = obs["y"][idx]
        sh = obs["home"][idx]
        so = obs["off_idx"][idx]
        sd = obs["def_idx"][idx]
        sn = obs["n_plays"][idx]
        sw = obs["week"][idx]
        sk = kick[idx]
        sgid = [obs["game_id"][i] for i in idx]

        last_fit = None
        last_key = None
        for ko_ts, ko_week in kos:
            hist = sk < float(ko_ts)
            key = (float(ko_ts), int(ko_week), int(hist.sum()))
            if key != last_key:
                if not np.any(hist):
                    last_fit = fit_joint(
                        sy[:0],
                        sh[:0],
                        so[:0],
                        sd[:0],
                        sn[:0],
                        prior_off=prior_off,
                        prior_def=prior_def,
                        n0=params.n0,
                        iters=params.iters,
                    )
                else:
                    ww = sn[hist] * np.array(
                        [week_weight(params.rho, int(ko_week), int(ww)) for ww in sw[hist]],
                        dtype=np.float64,
                    )
                    last_fit = fit_joint(
                        sy[hist],
                        sh[hist],
                        so[hist],
                        sd[hist],
                        ww,
                        prior_off=prior_off,
                        prior_def=prior_def,
                        n0=params.n0,
                        iters=params.iters,
                    )
                last_key = key
            assert last_fit is not None
            for g in games:
                if g["kickoff_ts"] != ko_ts:
                    continue
                hi = TEAM_INDEX[g["home"]]
                ai = TEAM_INDEX[g["away"]]
                rd[g["game_id"]] = rating_diff_home(last_fit.off, last_fit.deff, hi, ai)

        # Season-final posterior → next prior.
        w = sn * np.array(
            [week_weight(params.rho, int(sw.max()), int(ww)) for ww in sw],
            dtype=np.float64,
        )
        final = fit_joint(
            sy,
            sh,
            so,
            sd,
            w,
            prior_off=prior_off,
            prior_def=prior_def,
            n0=params.n0,
            iters=params.iters,
        )
        prior_off, prior_def = shrink_offseason(final.off, final.deff, params.rho_s)
        _ = sgid  # kept for debug parity; ratings keyed by panel game_id

    return rd


def _mae(pred: Sequence[float], actual: Sequence[float]) -> float:
    return float(sum(abs(p - a) for p, a in zip(pred, actual)) / max(len(pred), 1))


def _corr(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    import numpy as np

    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    if x.size < 3 or float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _slope(y: Sequence[float], x: Sequence[float]) -> Optional[float]:
    import numpy as np

    xv = np.asarray(x, dtype=np.float64)
    yv = np.asarray(y, dtype=np.float64)
    if xv.size < 3 or float(np.std(xv)) == 0.0:
        return None
    design = np.column_stack([np.ones(xv.size), xv])
    beta = ols_hc1(design, yv)["beta"]
    return float(beta[1])


def _gap(m: Sequence[float], pm: Sequence[float], mm: Sequence[float]) -> List[float]:
    return [abs(mi - pi) - abs(mi - mmi) for mi, pi, mmi in zip(m, pm, mm)]


def metrics_block(
    m: Sequence[float],
    mm: Sequence[float],
    pm: Sequence[float],
    pm_base: Sequence[float],
    *,
    seasons: Sequence[int],
    neutrals: Sequence[bool],
    label: str,
) -> Dict[str, Any]:
    import numpy as np

    m_l = list(m)
    mm_l = list(mm)
    pm_l = list(pm)
    pb_l = list(pm_base)
    n = len(m_l)
    mae_a = _mae(pm_l, m_l)
    mae_b = _mae(pb_l, m_l)
    mae_m = _mae(mm_l, m_l)
    gap_a = _gap(m_l, pm_l, mm_l)
    gap_b = _gap(m_l, pb_l, mm_l)
    delta = float(sum(gap_b) / n - sum(gap_a) / n) if n else float("nan")

    # (a) encompassing: m ~ a + b·mm + c·pm_A
    x = np.column_stack(
        [
            np.ones(n, dtype=np.float64),
            np.asarray(mm_l, dtype=np.float64),
            np.asarray(pm_l, dtype=np.float64),
        ]
    )
    y = np.asarray(m_l, dtype=np.float64)
    enc = ols_hc1(x, y)
    a_hat, b_hat, c_hat = (float(v) for v in enc["beta"])
    a_se, b_se, c_se = (float(v) for v in enc["se"])
    c_lo, c_hi = hc1_ci(c_hat, c_se, Z95)
    path_a = bool(c_hat > 0.0 and c_lo > 0.0)

    # (b) paired game bootstrap of Δ, B=10000 seed 4141
    rng = np.random.default_rng(BOOT_SEED)
    ga = np.asarray(gap_a, dtype=np.float64)
    gb = np.asarray(gap_b, dtype=np.float64)
    boot = np.empty(BOOT_B, dtype=np.float64)
    for i in range(BOOT_B):
        ix = rng.integers(0, n, size=n)
        boot[i] = float(gb[ix].mean() - ga[ix].mean())
    boot_lo = float(np.percentile(boot, 2.5))
    boot_hi = float(np.percentile(boot, 97.5))
    path_b = bool((boot_lo > 0.0 or boot_hi < 0.0) and delta >= 0.10)

    by_season: Dict[str, Any] = {}
    beats = 0
    for s in sorted(set(seasons)):
        idx = [i for i, ss in enumerate(seasons) if ss == s]
        if not idx:
            continue
        mae_as = _mae([pm_l[i] for i in idx], [m_l[i] for i in idx])
        mae_ms = _mae([mm_l[i] for i in idx], [m_l[i] for i in idx])
        win = mae_as < mae_ms
        beats += int(win)
        by_season[str(s)] = {
            "n": len(idx),
            "mae_A": mae_as,
            "mae_market": mae_ms,
            "beats_market": win,
        }

    neu_idx = [i for i, nflag in enumerate(neutrals) if nflag]
    neu: Dict[str, Any]
    if neu_idx:
        neu = {
            "n": len(neu_idx),
            "mae_A": _mae([pm_l[i] for i in neu_idx], [m_l[i] for i in neu_idx]),
            "mae_epa": _mae([pb_l[i] for i in neu_idx], [m_l[i] for i in neu_idx]),
            "mae_market": _mae([mm_l[i] for i in neu_idx], [m_l[i] for i in neu_idx]),
        }
    else:
        neu = {"n": 0}

    sd_pm = float(np.std(pm_l, ddof=1)) if n > 1 else float("nan")
    sd_mm = float(np.std(mm_l, ddof=1)) if n > 1 else float("nan")
    return {
        "label": label,
        "n": n,
        "mae_A": mae_a,
        "mae_epa": mae_b,
        "mae_market": mae_m,
        "mae_gap_A_vs_market": mae_a - mae_m,
        "mae_gap_epa_vs_market": mae_b - mae_m,
        "delta_point": delta,
        "mean_bias_A_minus_m": float(sum(p - a for p, a in zip(pm_l, m_l)) / n) if n else None,
        "slope_m_on_pm": _slope(m_l, pm_l),
        "slope_pm_on_mm": _slope(pm_l, mm_l),
        "corr_pm_m": _corr(pm_l, m_l),
        "sd_pm": sd_pm,
        "sd_mm": sd_mm,
        "sd_ratio_pm_over_mm": (sd_pm / sd_mm) if sd_mm else None,
        "seasons_beating_market": beats,
        "by_season": by_season,
        "neutral_subset": neu,
        "path_a": {
            "equation": "m ~ a + b*mm + c*pm_A",
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
            "pass": path_a,
        },
        "path_b": {
            "delta_definition": "mean(gap_epa)-mean(gap_A); gap_X=|m-pm_X|-|m-mm|",
            "B": BOOT_B,
            "seed": BOOT_SEED,
            "ci": "percentile 95",
            "delta_point": delta,
            "delta_ci95_lo": boot_lo,
            "delta_ci95_hi": boot_hi,
            "ci_excludes_0": bool(boot_lo > 0.0 or boot_hi < 0.0),
            "point_ge_0_10": bool(delta >= 0.10),
            "pass": path_b,
        },
        "stop_or": bool(path_a or path_b),
    }


def run_grid(
    manifest: Mapping[str, Any],
    panel: Sequence[Mapping[str, Any]],
    obs: Mapping[str, Any],
) -> Dict[str, Any]:
    import numpy as np

    grid = list(manifest["grid"])
    if len(grid) != 54:
        raise RuntimeError(f"frozen grid_size drift: {len(grid)}")
    if float(manifest["n0_base"]) != N0_BASE:
        raise RuntimeError("n0_base drift")
    if manifest["estimator_id"] != ESTIMATOR_ID:
        raise RuntimeError("estimator_id drift")

    # 27 rating configs (HFA is output-layer only).
    rating_keys = sorted({(float(c["rho"]), float(c["lambda"]), float(c["rho_s"])) for c in grid})
    rd_cache: Dict[Tuple[float, float, float], Dict[str, float]] = {}
    for i, (rho, lam, rho_s) in enumerate(rating_keys, 1):
        n0 = lam * N0_BASE
        print(f"[ratings] {i}/{len(rating_keys)} rho={rho} lambda={lam} rho_s={rho_s} n0={n0}", flush=True)
        rd_cache[(rho, lam, rho_s)] = walk_rating_diffs(
            obs, panel, RidgeParams(n0=n0, rho=rho, rho_s=rho_s)
        )

    panel_by_season: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for g in panel:
        panel_by_season[int(g["season"])].append(g)

    missing_rd = [g["game_id"] for g in panel if g["game_id"] not in next(iter(rd_cache.values()))]
    # check against first cache; then all
    n_missing_rd = 0
    for rd in rd_cache.values():
        n_missing_rd = max(n_missing_rd, sum(1 for g in panel if g["game_id"] not in rd))

    cells: List[Dict[str, Any]] = []
    fold_rows: List[Dict[str, Any]] = []
    beta_rows: List[Dict[str, Any]] = []
    oof_by_cfg: Dict[str, List[Dict[str, Any]]] = {}

    for cfg in grid:
        cfg_id = str(cfg["cfg_id"])
        rho, lam, rho_s = float(cfg["rho"]), float(cfg["lambda"]), float(cfg["rho_s"])
        hfa_mode = str(cfg["hfa_mode"])
        rdmap = rd_cache[(rho, lam, rho_s)]
        oof: List[Dict[str, Any]] = []
        maes = []
        for fold, S in FOLD_S.items():
            design = [g for g in panel if 2013 <= int(g["season"]) < S]
            eval_g = [g for g in panel if int(g["season"]) == S]
            d_rd = np.array([rdmap[g["game_id"]] for g in design], dtype=np.float64)
            d_m = np.array([g["m"] for g in design], dtype=np.float64)
            d_h = np.array([g["home_ind"] for g in design], dtype=np.float64)
            fitb = fit_beta_fold(d_rd, d_m, d_h, hfa_mode=hfa_mode)
            e_rd = np.array([rdmap[g["game_id"]] for g in eval_g], dtype=np.float64)
            e_h = np.array([g["home_ind"] for g in eval_g], dtype=np.float64)
            pm = predict_margin_a(e_rd, e_h, beta=fitb["beta"], hfa=fitb["hfa"])
            e_m = [g["m"] for g in eval_g]
            mae = _mae(list(pm), e_m)
            maes.append((mae, len(eval_g)))
            beta_rows.append(
                {
                    "cfg_id": cfg_id,
                    "fold": fold,
                    "S": S,
                    "hfa_mode": hfa_mode,
                    "rho": rho,
                    "lambda": lam,
                    "rho_s": rho_s,
                    "n0": lam * N0_BASE,
                    "beta": f"{fitb['beta']:.10f}",
                    "beta_se_hc1": f"{fitb['beta_se_hc1']:.10f}",
                    "hfa": f"{fitb['hfa']:.10f}",
                    "n_design": fitb["n"],
                    "n_eval": len(eval_g),
                    "mae": f"{mae:.10f}",
                }
            )
            fold_rows.append(
                {
                    "cfg_id": cfg_id,
                    "fold": fold,
                    "S": S,
                    "n": len(eval_g),
                    "mae": f"{mae:.10f}",
                    "beta": f"{fitb['beta']:.10f}",
                    "hfa": f"{fitb['hfa']:.10f}",
                    "surface": "primary_oof",
                }
            )
            for g, p, rdv in zip(eval_g, pm, e_rd):
                oof.append(
                    {
                        **{k: g[k] for k in ("season", "week", "game_id", "home", "away", "m", "mm", "pm_epa", "home_ind", "neutral")},
                        "fold": fold,
                        "rating_diff_home": float(rdv),
                        "pm_A": float(p),
                        "beta": fitb["beta"],
                        "hfa": fitb["hfa"],
                        "cfg_id": cfg_id,
                    }
                )
        n_oof = sum(n for _, n in maes)
        pooled_mae = sum(mae * n for mae, n in maes) / max(n_oof, 1)
        cells.append(
            {
                "cfg_id": cfg_id,
                "rho": rho,
                "lambda": lam,
                "rho_s": rho_s,
                "n0": lam * N0_BASE,
                "hfa_mode": hfa_mode,
                "mae": float(pooled_mae),
                "n_oof": n_oof,
            }
        )
        oof_by_cfg[cfg_id] = oof
        print(f"[grid] {cfg_id} hfa={hfa_mode} mae={pooled_mae:.6f}", flush=True)

    winner = select_cell(cells, epsilon=float(manifest["selection"]["declared_epsilon"]))
    cfg_id = str(winner["cfg_id"])
    oof = oof_by_cfg[cfg_id]

    # 2023 supportive: freeze grid; β fit on 2013–2022; no refit of grid.
    rho, lam, rho_s = float(winner["rho"]), float(winner["lambda"]), float(winner["rho_s"])
    hfa_mode = str(winner["hfa_mode"])
    rdmap = rd_cache[(rho, lam, rho_s)]
    design23 = [g for g in panel if 2013 <= int(g["season"]) <= 2022]
    eval23 = [g for g in panel if int(g["season"]) == 2023]
    fit23 = fit_beta_fold(
        np.array([rdmap[g["game_id"]] for g in design23], dtype=np.float64),
        np.array([g["m"] for g in design23], dtype=np.float64),
        np.array([g["home_ind"] for g in design23], dtype=np.float64),
        hfa_mode=hfa_mode,
    )
    pm23 = predict_margin_a(
        np.array([rdmap[g["game_id"]] for g in eval23], dtype=np.float64),
        np.array([g["home_ind"] for g in eval23], dtype=np.float64),
        beta=fit23["beta"],
        hfa=fit23["hfa"],
    )
    rows23 = []
    for g, p in zip(eval23, pm23):
        rows23.append(
            {
                **{k: g[k] for k in ("season", "week", "game_id", "home", "away", "m", "mm", "pm_epa", "home_ind", "neutral")},
                "fold": "S2023_supportive",
                "rating_diff_home": rdmap[g["game_id"]],
                "pm_A": float(p),
                "beta": fit23["beta"],
                "hfa": fit23["hfa"],
                "cfg_id": cfg_id,
            }
        )

    bind = metrics_block(
        [r["m"] for r in oof],
        [r["mm"] for r in oof],
        [r["pm_A"] for r in oof],
        [r["pm_epa"] for r in oof],
        seasons=[int(r["season"]) for r in oof],
        neutrals=[bool(r["neutral"]) for r in oof],
        label="pooled_le_2022_OOF",
    )
    sup = metrics_block(
        [r["m"] for r in rows23],
        [r["mm"] for r in rows23],
        [r["pm_A"] for r in rows23],
        [r["pm_epa"] for r in rows23],
        seasons=[int(r["season"]) for r in rows23],
        neutrals=[bool(r["neutral"]) for r in rows23],
        label="2023_supportive",
    )
    reversal = bool(
        math.isfinite(bind["delta_point"])
        and math.isfinite(sup["delta_point"])
        and (bind["delta_point"] > 0.0) != (sup["delta_point"] > 0.0)
        and bind["delta_point"] != 0.0
        and sup["delta_point"] != 0.0
    )
    # Binding decides. 2023 cannot alone PASS.
    verdict = "PASS" if bind["stop_or"] else "FAIL"

    return {
        "cells": cells,
        "winner": dict(winner),
        "fold_rows": fold_rows,
        "beta_rows": beta_rows,
        "oof": oof,
        "rows23": rows23,
        "bind": bind,
        "sup": sup,
        "fit23": fit23,
        "verdict": verdict,
        "reversal_caution": reversal,
        "n_missing_rd": n_missing_rd,
        "missing_rd_sample": missing_rd[:8],
        "rd_cache_keys": len(rd_cache),
    }


def _fmt(x: Any, nd: int = 6) -> str:
    if x is None:
        return ""
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def write_report(
    path: Path,
    *,
    forecast_ts: str,
    counts: Mapping[str, Any],
    winner: Mapping[str, Any],
    bind: Mapping[str, Any],
    sup: Mapping[str, Any],
    artifact_sha8: Mapping[str, str],
) -> str:
    pa, pb = bind["path_a"], bind["path_b"]
    lines = [
        "# Experiment A — ridge-joint 54-cell fold validation (t4602u)",
        "",
        "**EXP A ONLY · CERT=0 · NFL NO-GO · F2 FROZEN · sealed=1 · #648 DRAFT · do not merge**",
        "",
        f"**VERDICT (binding pooled ≤2022 OOF): `{counts['verdict']}`**",
        "",
        f"Stop (a)={'PASS' if pa['pass'] else 'FAIL'} · Stop (b)={'PASS' if pb['pass'] else 'FAIL'} · "
        f"2023 cannot-alone-PASS · reversal_caution={counts['reversal_caution']}",
        "",
        f"Filed `{forecast_ts}`. Paper/file evidence only. No Odds / merge / deploy / CERT claim.",
        "",
        "## Authority",
        "",
        "| item | sha8 |",
        "|---|---|",
        f"| Ryan CLEAR t4602u | `{DECISION_SHA8}` |",
        f"| CoS execute order | `{COS_ORDER_SHA8}` |",
        f"| IMV PREFLIGHT LOOK (full §4) | `{IMV_LOOK_SHA8}` |",
        f"| H2 FROZEN manifest | `{H2_SHA8}` |",
        f"| Exp E IMV_PASS | `{IMV_PASS_E}` |",
        f"| Exp E counts | `b0365365` |",
        f"| H1 addendum | `{H1_ADDENDUM}` |",
        f"| H1 SHA256SUMS | `97774e08` |",
        f"| tip (E H1) | `0940a289` |",
        f"| Alex SPEC §4 | `ddffb72e` |",
        f"| ESTIMATOR addendum | `84a28a05` |",
        f"| Cursor ACK | `6fcc0af6` |",
        "",
        "## Frozen design (unchanged)",
        "",
        f"- `ESTIMATOR_ID` = `{ESTIMATOR_ID}`",
        f"- `n0_base` = {N0_BASE}",
        "- grid 54 (ρ / λ / ρ_s / HFA off|fold_fit)",
        "- L1: HFA off, then ρ=0.95, λ=1, ρ_s=0.67; ε=1e-9",
        "- F1–F9 S=2014…2022 primary; 2023 supportive; 2024+ forbidden",
        "- ONE fold-fit β; `margin_A = β · rating_diff_home + HFA`; `simulate_nfl_game=false`",
        "",
        "## Selected cell (inner-CV MAE, L1 tie-break)",
        "",
        f"- `cfg_id` = `{winner['cfg_id']}`",
        f"- ρ={winner['rho']} λ={winner['lambda']} ρ_s={winner['rho_s']} HFA={winner['hfa_mode']} n0={winner['n0']}",
        f"- pooled ≤2022 inner-CV MAE = `{winner['mae']}`",
        "",
        "## Stop rule — Alex ddffb72e §4 (full emit)",
        "",
        "Exp A FAILS unless:",
        "",
        "(a) encompassing `m ~ a + b·mm + c·pm_A` (OLS, HC1) gives c 95% CI excluding 0 with c>0;",
        "",
        "OR",
        "",
        "(b) paired game bootstrap of Δ, B=10000, seed 4141, percentile 95% CI excludes 0 AND point Δ ≥ 0.10 pts.",
        "",
        "`Δ = mean(gap_baseline) − mean(gap_A)`; `gap_X = |m − pm_X| − |m − mm|`.",
        "",
        "Binding = pooled ≤2022 OOF. 2023 supportive / cannot-alone-PASS. VOID if changed post-run.",
        "",
        "### Binding (pooled ≤2022 OOF)",
        "",
        f"- n = {bind['n']}",
        f"- MAE(A) = {bind['mae_A']}",
        f"- MAE(epa baseline) = {bind['mae_epa']}",
        f"- MAE(market) = {bind['mae_market']}",
        f"- point Δ = {bind['delta_point']}",
        f"- (a) c = {pa['c']}  HC1 se = {pa['c_se_hc1']}  CI = [{pa['c_ci95_lo']}, {pa['c_ci95_hi']}]  pass={pa['pass']}",
        f"- (b) Δ CI = [{pb['delta_ci95_lo']}, {pb['delta_ci95_hi']}]  point_ge_0.10={pb['point_ge_0_10']}  pass={pb['pass']}",
        "",
        "### 2023 supportive (cannot alone PASS)",
        "",
        f"- n = {sup['n']}",
        f"- MAE(A) = {sup['mae_A']}",
        f"- point Δ = {sup['delta_point']}",
        f"- (a) pass={sup['path_a']['pass']}  (b) pass={sup['path_b']['pass']}",
        f"- reversal_caution = {counts['reversal_caution']}",
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
        "- No Odds API. No merge of #646/#647/#648. No LOCKED_SCORING change.",
        "- Rating-model h was not added into margin_A.",
        "- Stop rule was not changed post-run.",
        "",
    ]
    return _write_text(path, "\n".join(lines))


def main() -> int:
    _assert_no_forbidden_imports()
    self_check()
    forecast_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[exp-a] start {forecast_ts} CERT={CERT_CANDIDATE}", flush=True)

    h1 = close_h1()
    if not h1["ok"]:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        counts = {
            "verdict": "BLOCKED",
            "blocked_reasons": h1["blocked_reasons"],
            "cert_candidate": 0,
            "ticket": TICKET,
        }
        _write_json(OUT_DIR / "counts.json", counts)
        print("[exp-a] BLOCKED " + "; ".join(h1["blocked_reasons"]), flush=True)
        return 3

    manifest = _load_json(H2_PATH)
    if manifest.get("simulate_nfl_game") is True:
        raise RuntimeError("frozen manifest allows simulate_nfl_game")
    if manifest.get("output", {}).get("simulate_nfl_game") is True:
        raise RuntimeError("frozen output.simulate_nfl_game true")

    panel, n_ge_2024_games, n_oos_dropped_ge_2024 = load_panel(Path(h1["emit_path"]))
    tg, n_ge_2024_pbp = load_team_games()
    obs = _obs_arrays(tg["rows"])
    n_ge_2024 = int(n_ge_2024_games + n_ge_2024_pbp)

    if n_ge_2024 > 0:
        counts = {
            "verdict": "FAIL",
            "fail_reasons": [f"n_rows_season_ge_2024={n_ge_2024}"],
            "n_rows_season_ge_2024": n_ge_2024,
            "n_oos_dropped_ge_2024": n_oos_dropped_ge_2024,
            "cert_candidate": 0,
            "ticket": TICKET,
        }
        _write_json(OUT_DIR / "counts.json", counts)
        print("[exp-a] FAIL 2024+ leak", flush=True)
        return 2

    if len(panel) != N_GAMES_EXPECT:
        print(f"[exp-a] panel size {len(panel)} != {N_GAMES_EXPECT} (continuing; counted)", flush=True)

    result = run_grid(manifest, panel, obs)
    if result["n_missing_rd"] > 0:
        counts = {
            "verdict": "FAIL",
            "fail_reasons": [f"n_missing_rd={result['n_missing_rd']}"],
            "missing_rd_sample": result["missing_rd_sample"],
            "cert_candidate": 0,
            "ticket": TICKET,
        }
        _write_json(OUT_DIR / "counts.json", counts)
        print("[exp-a] FAIL missing rating_diff", flush=True)
        return 2

    winner = result["winner"]
    bind = result["bind"]
    sup = result["sup"]
    verdict = result["verdict"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    artifact_sha: Dict[str, str] = {}

    grid_fields = ["cfg_id", "rho", "lambda", "rho_s", "n0", "hfa_mode", "mae", "n_oof"]
    artifact_sha["grid_mae.csv"] = _write_csv(
        OUT_DIR / "grid_mae.csv",
        grid_fields,
        [{**c, "mae": f"{c['mae']:.10f}"} for c in result["cells"]],
    )
    artifact_sha["betas_by_fold.csv"] = _write_csv(
        OUT_DIR / "betas_by_fold.csv",
        [
            "cfg_id",
            "fold",
            "S",
            "hfa_mode",
            "rho",
            "lambda",
            "rho_s",
            "n0",
            "beta",
            "beta_se_hc1",
            "hfa",
            "n_design",
            "n_eval",
            "mae",
        ],
        result["beta_rows"],
    )
    artifact_sha["fold_table.csv"] = _write_csv(
        OUT_DIR / "fold_table.csv",
        ["cfg_id", "fold", "S", "n", "mae", "beta", "hfa", "surface"],
        result["fold_rows"],
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
        "home_ind",
        "m",
        "mm",
        "pm_epa",
        "rating_diff_home",
        "pm_A",
        "beta",
        "hfa",
    ]
    pred_rows = []
    for r in result["oof"] + result["rows23"]:
        pred_rows.append(
            {
                **r,
                "neutral": int(bool(r["neutral"])),
                "m": _fmt(r["m"]),
                "mm": _fmt(r["mm"]),
                "pm_epa": _fmt(r["pm_epa"]),
                "rating_diff_home": _fmt(r["rating_diff_home"], 10),
                "pm_A": _fmt(r["pm_A"]),
                "beta": _fmt(r["beta"], 10),
                "hfa": _fmt(r["hfa"], 10),
            }
        )
    artifact_sha["predictions.csv"] = _write_csv(OUT_DIR / "predictions.csv", pred_fields, pred_rows)

    selected = {
        "cfg_id": winner["cfg_id"],
        "rho": winner["rho"],
        "lambda": winner["lambda"],
        "rho_s": winner["rho_s"],
        "n0": winner["n0"],
        "hfa_mode": winner["hfa_mode"],
        "inner_cv_mae": winner["mae"],
        "n_oof": winner["n_oof"],
        "tie_break_verbatim": manifest["selection"]["tie_break_verbatim"],
        "declared_epsilon": manifest["selection"]["declared_epsilon"],
        "beta_2023_supportive": result["fit23"],
        "estimator_id": ESTIMATOR_ID,
    }
    artifact_sha["selected_cell.json"] = _write_json(OUT_DIR / "selected_cell.json", selected)
    artifact_sha["stop_rule.json"] = _write_json(
        OUT_DIR / "stop_rule.json",
        {
            "authority": "Alex ddffb72e §4 verbatim; IMV LOOK a5083123",
            "void_if_changed_post_run": True,
            "binding_surface": "pooled_le_2022_OOF",
            "supportive_2023_cannot_alone_PASS": True,
            "B": BOOT_B,
            "seed": BOOT_SEED,
            "delta_definition": "mean(gap_epa)-mean(gap_A); gap_X=|m-pm_X|-|m-mm|",
            "encompassing": "m ~ a + b*mm + c*pm_A  (OLS HC1)",
            "binding": bind,
            "supportive_2023": sup,
            "reversal_caution": result["reversal_caution"],
            "verdict_binding": verdict,
        },
    )
    artifact_sha["metrics_binding.json"] = _write_json(OUT_DIR / "metrics_binding.json", bind)
    artifact_sha["metrics_2023.json"] = _write_json(OUT_DIR / "metrics_2023.json", sup)

    counts = {
        "authority": {
            "decision_sha8": DECISION_SHA8,
            "cos_order_sha8": COS_ORDER_SHA8,
            "imv_look_sha8": IMV_LOOK_SHA8,
            "h2_sha8": H2_SHA8,
            "imv_pass_exp_e": IMV_PASS_E,
            "h1_addendum_sha8": H1_ADDENDUM,
            "h1_sha256sums_sha256": H1_SUMS_SHA256,
            "tip_0940a289": TIP_E_H1,
            "exp_e_counts_sha256": COUNTS_E_SHA256,
            "alex_spec": "ddffb72e",
            "estimator_addendum": "84a28a05",
            "cursor_ack": "6fcc0af6",
            "feasibility_v11": "15ee3a1b",
            "pass_protocol": "60c18a4c",
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
        "estimator_id": ESTIMATOR_ID,
        "n0_base": N0_BASE,
        "grid_size": 54,
        "n_games": len(panel),
        "n_games_expect": N_GAMES_EXPECT,
        "n_oof_le_2022": bind["n"],
        "n_2023": sup["n"],
        "n_neutral": sum(1 for g in panel if g["neutral"]),
        "n_rows_season_ge_2024": n_ge_2024,
        "n_oos_dropped_ge_2024": n_oos_dropped_ge_2024,
        "n_missing_rd": result["n_missing_rd"],
        "n_team_games": int(len(obs["y"])),
        "selected_cfg_id": winner["cfg_id"],
        "selected_mae": winner["mae"],
        "verdict": verdict,
        "path_a_pass": bind["path_a"]["pass"],
        "path_b_pass": bind["path_b"]["pass"],
        "delta_point_binding": bind["delta_point"],
        "reversal_caution": result["reversal_caution"],
        "h2_sha256": H2_SHA256,
        "games_csv_sha256": GAMES_CSV_SHA256,
        "oos_sha256": OOS_SHA256,
        "emit_sha256": EMIT_SHA256,
        "bootstrap_B": BOOT_B,
        "bootstrap_seed": BOOT_SEED,
    }
    artifact_sha["counts.json"] = _write_json(OUT_DIR / "counts.json", counts)

    sha8_table = {name: _sha8(sha) for name, sha in artifact_sha.items()}
    manifest_out = {
        "run_id": f"nfl-exp-a-{TICKET}-{forecast_ts.replace(':', '').replace('-', '')}",
        "ticket": TICKET,
        "forecast_ts_utc": forecast_ts,
        "verdict": verdict,
        "estimator_id": ESTIMATOR_ID,
        "h2_sha256": H2_SHA256,
        "selected_cfg_id": winner["cfg_id"],
        "authority": counts["authority"],
        "h1_hashes": dict(_H1_HASHES),
        "artifact_sha256": artifact_sha,
        "cert_candidate": 0,
        "simulate_nfl_game_called": False,
        "stop_rule_unchanged": True,
    }
    # REPORT references sha8 including itself after we know others; write REPORT then patch table
    report_sha = write_report(
        OUT_DIR / "REPORT.md",
        forecast_ts=forecast_ts,
        counts=counts,
        winner=winner,
        bind=bind,
        sup=sup,
        artifact_sha8=sha8_table,
    )
    artifact_sha["REPORT.md"] = report_sha
    sha8_table["REPORT.md"] = _sha8(report_sha)
    artifact_sha["artifact_sha8.json"] = _write_json(OUT_DIR / "artifact_sha8.json", sha8_table)
    manifest_out["artifact_sha256"] = artifact_sha
    artifact_sha["manifest.json"] = _write_json(OUT_DIR / "manifest.json", manifest_out)
    sha8_table["manifest.json"] = _sha8(artifact_sha["manifest.json"])
    # rewrite sha8 table with manifest
    os.chmod(OUT_DIR / "artifact_sha8.json", 0o644)
    artifact_sha["artifact_sha8.json"] = _write_json(OUT_DIR / "artifact_sha8.json", sha8_table)

    all_sums = dict(_H1_HASHES)
    all_sums.update({f"outputs/{k}": v for k, v in artifact_sha.items()})
    _write_sha256sums(OUT_DIR / "SHA256SUMS", all_sums)
    os.chmod(OUT_DIR / "SHA256SUMS", FILE_MODE)

    _assert_no_forbidden_imports()
    print(
        f"[exp-a] verdict={verdict} selected={winner['cfg_id']} "
        f"delta={bind['delta_point']:.4f} a={bind['path_a']['pass']} b={bind['path_b']['pass']} "
        f"out={OUT_DIR}",
        flush=True,
    )
    return 0 if verdict in {"PASS", "FAIL"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
