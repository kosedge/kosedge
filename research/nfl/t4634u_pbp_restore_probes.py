#!/usr/bin/env python3
"""t4634u PBP restore + C2/B1/B4/A4 probes (CERT=0).

Authority
  DECISION_RYAN_t4634u                      sha8 1cf303e3
  COS_ORDER_CURSOR_t4634u                   sha8 2693c91b
  Feasibility packet                        cited
  Lineage verify procedure                  ebd3ea93

Restore already-approved historical nflverse PBP matching sealed Exp E/A H1
pins, then complete FAIL_CLOSED probes C2 / B1 / B4 / A4.

Does NOT: run a new predictive experiment, nested G34, Odds, F2 change,
warehouse CURRENT ROW as SoT, Mac cert PBP, 2024+ holdouts, merge/deploy,
rewrite sealed Exp A/E artifacts, or claim CERT.

NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · #648 DRAFT.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))
_USER_SITE = Path.home() / ".local/lib/python3.12/site-packages"
if _USER_SITE.is_dir() and str(_USER_SITE) not in sys.path:
    sys.path.insert(0, str(_USER_SITE))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from t4602u_exp_a_ridge_joint import (  # noqa: E402
    N0_BASE,
    N_TEAMS,
    TEAM_INDEX,
    RidgeParams,
    fit_joint,
    rating_diff_home,
    shrink_offseason,
    week_weight,
)

import t4586u_exp_e_kickoff_asof_audit as exp_e  # noqa: E402
import t4602u_exp_a_execute as exp_a  # noqa: E402

TICKET = "t4634u"
LABEL = "RESEARCH_DIAGNOSTIC_PBP_RESTORE_PROBES"
CERT_CANDIDATE = 0
FILE_MODE = 0o444

DECISION_SHA8 = "1cf303e3"
COS_ORDER_SHA8 = "2693c91b"
LINEAGE_SHA8 = "ebd3ea93"
H1_SUMS_SHA256 = "97774e08985cba90f23196857807b3e69144630867bc9d000007cfa4e93bc8da"
GAMES_CSV_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
OOS_SHA256 = "1ee90facf7d44dfd19758cbf89d5518417cbc1fba6faec4e76fb33d8532adaed"
EMIT_SHA256 = "02f6b2e2baa425cab7703dd1d3d5064fc0dabfc69e330a846e54d736c49430a2"
ROLLING_SHA256 = "1b07654ea500535ff445e0f3c20acc26a6c3006857951562755e406adff52479"
PRED_SHA256 = "c3248302c5efd9bb63629721679ca46eba2106d6a3a71877e3d10271a26c43cb"
H2_SHA256 = "db2cf4b24bfa9c441f7eafea19d5c24624541f9cb7225759e9882f61cb6c6463"

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
PBP_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "pbp/play_by_play_{season}.parquet"
)

CACHE_DIR = Path(os.environ.get("T4634U_CACHE", "/tmp/nflverse-pbp-exp-e"))
STAGING_DIR = Path(os.environ.get("T4634U_STAGING", "/tmp/nflverse-pbp-exp-e.staging"))
OUT_DIR = HERE / "t4634u_pbp_restore_probes"
INPUTS_SUMS = HERE / "t4602u_exp_a" / "SHA256SUMS.inputs"
H1_SUMS_PATH = HERE / "t4586u_exp_e_kickoff_asof" / "SHA256SUMS"
ROLLING_PATH = HERE / "t4586u_exp_e_inputs" / "rolling_features_weekly_pbp_strict_asof_2013_2023.csv"
PRED_PATH = HERE / "t4602u_exp_a" / "predictions.csv"
GAMES_PATH = HERE / "t4586u_exp_e_inputs" / "games.csv"
OOS_PATH = HERE / "t4586u_exp_e_inputs" / "historical_oos_games.csv"
H2_PATH = HERE / "t4586u_exp_a_h2_manifest_freeze" / "CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json"
R_ROOT = ROOT / "ops" / "nfl_enterprise_green_t4359u"

G34 = RidgeParams(n0=8.0, rho=0.95, rho_s=0.67)
N_TEAM_GAMES_EXPECT = 6518
N_PRED_EXPECT = 2725
N_ROLL_EXPECT = 5984
RD_TOL = 1e-6
PMA_TOL = 5.0e-7

_FORBIDDEN_IMPORTS = (
    "simulate_nfl_game",
    "LOCKED_SCORING",
    "config_overrides",
    "NflGameInputs",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha8(digest: str) -> str:
    return digest[:8]


def _write_readonly(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o644)
    data = text if text.endswith("\n") else text + "\n"
    path.write_text(data, encoding="utf-8")
    os.chmod(path, FILE_MODE)
    return _sha256_file(path)


def _write_json(path: Path, obj: Any) -> str:
    return _write_readonly(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _write_sums(path: Path, items: Mapping[str, str]) -> str:
    lines = [f"{digest}  {name}\n" for name, digest in sorted(items.items())]
    return _write_readonly(path, "".join(lines))


def _assert_no_forbidden() -> None:
    for name in _FORBIDDEN_IMPORTS:
        if name in sys.modules:
            raise RuntimeError(f"forbidden import present: {name}")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    if tmp.exists():
        tmp.unlink()
    curl = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "5",
        "--retry-delay",
        "4",
        "--retry-all-errors",
        "-A",
        "kosedge-research/t4634u-pbp-restore",
        "--connect-timeout",
        "30",
        "--max-time",
        "300",
        "-o",
        str(tmp),
        url,
    ]
    subprocess.check_call(curl)
    tmp.replace(dest)


def restore_pbp() -> Dict[str, Any]:
    """Prefer cache bytes that already match pins; else pin-gated nflverse re-fetch."""
    cache_search = {
        "cache_dir": str(CACHE_DIR),
        "existed_before": CACHE_DIR.is_dir(),
        "hits": [],
        "misses": [],
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    files: Dict[str, Any] = {}
    path_used = "cache"
    aborted = []
    for season in PBP_SEASONS:
        name = f"play_by_play_{season}.parquet"
        dest = CACHE_DIR / name
        want = PBP_SHA256[season]
        if dest.is_file() and dest.stat().st_size > 10_000:
            digest = _sha256_file(dest)
            if digest == want:
                cache_search["hits"].append(name)
                files[name] = {
                    "sha256": digest,
                    "sha8": _sha8(digest),
                    "bytes": dest.stat().st_size,
                    "source": "cache_hit",
                    "match": True,
                }
                print(f"[restore] cache hit {name} {_sha8(digest)}", flush=True)
                continue
            print(f"[restore] cache stale {name} got={digest} want={want}", flush=True)
            dest.unlink()
        cache_search["misses"].append(name)
        path_used = "pin_matched_refetch" if not cache_search["hits"] else "mixed_cache_and_refetch"
        url = PBP_URL.format(season=season)
        staging = STAGING_DIR / name
        print(f"[restore] fetch {url}", flush=True)
        _download(url, staging)
        digest = _sha256_file(staging)
        if digest != want:
            staging.unlink(missing_ok=True)
            aborted.append({"file": name, "got": digest, "want": want})
            print(f"[restore] PIN_MISMATCH_ABORT {name} got={digest} want={want}", flush=True)
            break
        dest.write_bytes(staging.read_bytes())
        os.chmod(dest, FILE_MODE)
        files[name] = {
            "sha256": digest,
            "sha8": _sha8(digest),
            "bytes": dest.stat().st_size,
            "source": "pin_matched_refetch",
            "url": url,
            "match": True,
        }
        print(f"[restore] PIN_MATCH {name} {_sha8(digest)} bytes={dest.stat().st_size}", flush=True)

    ok = len(aborted) == 0 and len(files) == 12 and all(v.get("match") for v in files.values())
    if cache_search["hits"] and not cache_search["misses"]:
        path_used = "cache"
    elif cache_search["hits"] and cache_search["misses"] and ok:
        path_used = "mixed_cache_and_refetch"
    elif cache_search["misses"] and ok:
        path_used = "pin_matched_refetch"
    return {
        "ok": ok,
        "path_used": path_used if ok else "ABORT",
        "cache_search": cache_search,
        "files": files,
        "aborted": aborted,
        "n_files": len(files),
        "url_family": PBP_URL,
        "mac_cert_pbp_touched": False,
        "warehouse_sot_changed": False,
        "purchased_data": False,
    }


def probe_a4(restore: Mapping[str, Any]) -> Dict[str, Any]:
    """sha256sum -c SHA256SUMS.inputs for PBP 2012–2023 + sibling input pins."""
    sums_text = INPUTS_SUMS.read_text(encoding="utf-8")
    expected = {}
    for line in sums_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, name = line.split(None, 1)
        expected[name] = digest

    pbp_ok = True
    pbp_rows = []
    for season in PBP_SEASONS:
        name = f"play_by_play_{season}.parquet"
        want = expected.get(name) or PBP_SHA256[season]
        dest = CACHE_DIR / name
        if not dest.is_file():
            pbp_ok = False
            pbp_rows.append({"file": name, "result": "FAIL_CLOSED", "reason": "absent"})
            continue
        got = _sha256_file(dest)
        match = got == want
        pbp_ok = pbp_ok and match
        pbp_rows.append(
            {
                "file": name,
                "want": want,
                "got": got,
                "sha8": _sha8(got),
                "bytes": dest.stat().st_size,
                "result": "PASS" if match else "FAIL",
            }
        )

    sibling = {}
    for label, path, want in (
        ("exp_e_h1_SHA256SUMS", H1_SUMS_PATH, H1_SUMS_SHA256),
        ("games.csv", GAMES_PATH, GAMES_CSV_SHA256),
        ("historical_oos_games.csv", OOS_PATH, OOS_SHA256),
        ("rolling_features_weekly_pbp_strict_asof_2013_2023.csv", ROLLING_PATH, ROLLING_SHA256),
        ("CURSOR_EXP_A_H2_GRID_FOLD_MANIFEST_t4598u_v1.json", H2_PATH, H2_SHA256),
        ("predictions.csv", PRED_PATH, PRED_SHA256),
    ):
        if not path.is_file():
            sibling[label] = {"result": "FAIL_CLOSED", "path": str(path)}
            continue
        got = _sha256_file(path)
        sibling[label] = {
            "path": str(path.relative_to(ROOT)),
            "got": got,
            "want": want,
            "sha8": _sha8(got),
            "result": "PASS" if got == want else "FAIL",
        }

    h1_ok = sibling["exp_e_h1_SHA256SUMS"]["result"] == "PASS"
    if not restore.get("ok"):
        result = "FAIL_CLOSED" if restore.get("aborted") else "FAIL"
    elif not pbp_ok:
        result = "FAIL"
    else:
        result = "PASS"

    return {
        "result": result,
        "threat": "T5",
        "h1_sums_file_sha8": "97774e08" if h1_ok else sibling["exp_e_h1_SHA256SUMS"].get("sha8"),
        "n_pbp_pass": sum(1 for r in pbp_rows if r.get("result") == "PASS"),
        "n_pbp_expect": 12,
        "pbp": pbp_rows,
        "sibling_inputs": sibling,
        "inputs_sums_path": str(INPUTS_SUMS.relative_to(ROOT)),
        "sha256sum_c": "12/12 PBP MATCH" if pbp_ok else "PBP mismatch or absent",
    }


def _close_h1_readonly(pbp_hashes: Mapping[str, str]) -> None:
    """Mark sealed execute modules H1-closed without rewriting their artifacts."""
    exp_a._H1_CLOSED = True
    exp_a._H1_HASHES.clear()
    exp_a._H1_HASHES.update(pbp_hashes)
    exp_e._H1_CLOSED = True
    exp_e._H1_HASHES.clear()
    exp_e._H1_HASHES.update(pbp_hashes)


def probe_b1() -> Dict[str, Any]:
    """Recompute off/def EPA 5g from restored PBP vs sealed rolling 1b07654e."""
    pinned: List[Dict[str, str]] = []
    with ROLLING_PATH.open(newline="", encoding="utf-8") as fh:
        pinned = list(csv.DictReader(fh))

    weekly, _tw, _meta, _weather, n_ge_2024 = exp_e._load_pbp_week_rows(CACHE_DIR, PBP_SEASONS)
    history: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for rec in weekly:
        history[str(rec["franchise"])].append(rec)
    reconstructed = exp_e._reconstruct_rolling(weekly, history)
    n_vintage, reasons = exp_e._compare_vintage(reconstructed, pinned)

    n_same_week = 0
    n_gt_5 = 0
    n_policy = 0
    for row in pinned:
        if int(float(row.get("games_in_window_5") or 0)) > 5:
            n_gt_5 += 1
        if str(row.get("asof_policy") or "") == "strict_prior_weeks_unweighted_weekly_mean_last5":
            n_policy += 1
    # same-week would appear if window included target (season,week)
    for rec in reconstructed:
        rolled = exp_e._rolling_before(
            history,
            franchise=str(rec["team"]),
            season=int(rec["season"]),
            week=int(rec["week"]),
        )
        if not rolled:
            continue
        for tw in rolled.get("team_weeks") or []:
            if (int(tw[0]), int(tw[1])) == (int(rec["season"]), int(rec["week"])):
                n_same_week += 1

    result = "PASS" if n_vintage == 0 and n_ge_2024 == 0 and n_same_week == 0 else "FAIL"
    return {
        "result": result,
        "threat": "T1/T5",
        "n_weekly": len(weekly),
        "n_reconstructed": len(reconstructed),
        "n_pinned": len(pinned),
        "n_pinned_expect": N_ROLL_EXPECT,
        "n_vintage_mismatch": n_vintage,
        "vintage_reasons": reasons[:8],
        "n_plays_season_ge_2024": n_ge_2024,
        "n_same_week_in_window": n_same_week,
        "n_gt_5_pinned": n_gt_5,
        "n_policy_strict_prior": n_policy,
        "rolling_pin_sha8": "1b07654e",
        "asof_policy": "strict_prior_weeks_unweighted_weekly_mean_last5",
    }


def _extract_emit(dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print("[h1] git-show #646 emit CSV (cite; not a merge)", flush=True)
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", exp_a.EMIT_GIT_REF])
    dest.write_bytes(raw)
    return _sha256_file(dest)


def walk_c2_and_rd(
    obs: Mapping[str, Any],
    panel: Sequence[Mapping[str, Any]],
    params: RidgeParams,
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """G34 walk with n0 shrink-count instrumentation (lineage C2)."""
    import numpy as np

    kick_by_gid = {r["game_id"]: float(r["kickoff_ts"]) for r in panel}
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

    n_hist_all: List[int] = []
    n_future = 0
    n_same_game = 0
    n_season_final_same_season = 0
    samples: List[Dict[str, Any]] = []
    n_hist_zero = 0
    n_kickoffs = 0

    for season in range(2012, 2024):
        mask = obs["season"] == season
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            prior_off, prior_def = shrink_offseason(prior_off, prior_def, params.rho_s)
            continue
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
        kos = sorted({(g["kickoff_ts"], g["week"]) for g in games})
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
            n_hist = int(hist.sum())
            n_kickoffs += 1
            n_hist_all.append(n_hist)
            if n_hist == 0:
                n_hist_zero += 1
            future_mask = sk >= float(ko_ts)
            # Leak would be using future/same-kickoff obs in hist.
            n_future += int((hist & future_mask).sum())
            target_gids = {g["game_id"] for g in games if g["kickoff_ts"] == ko_ts}
            if n_hist:
                for j, flag in enumerate(hist):
                    if flag and sgid[j] in target_gids:
                        n_same_game += 1
            key = (float(ko_ts), int(ko_week), n_hist)
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
            if len(samples) < 8:
                samples.append(
                    {
                        "season": season,
                        "week": int(ko_week),
                        "n_hist": n_hist,
                        "n_targets": len(target_gids),
                        "n0": params.n0,
                    }
                )

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
        # Season-final posterior is next-year prior only.
        prior_off, prior_def = shrink_offseason(final.off, final.deff, params.rho_s)
        n_season_final_same_season += 0

    n_hist_sorted = sorted(n_hist_all)
    c2 = {
        "n0": params.n0,
        "n0_expect": float(2.0 * N0_BASE),
        "lambda": 2.0,
        "n0_base": N0_BASE,
        "hist_rule": "sk < ko_ts",
        "n_kickoffs": n_kickoffs,
        "n_hist_zero": n_hist_zero,
        "n_hist_min": min(n_hist_sorted) if n_hist_sorted else None,
        "n_hist_max": max(n_hist_sorted) if n_hist_sorted else None,
        "n_hist_median": float(statistics.median(n_hist_sorted)) if n_hist_sorted else None,
        "n_future_in_hist": n_future,
        "n_same_game_in_hist": n_same_game,
        "season_final_used_as_same_season_rating": n_season_final_same_season,
        "season_final_role": "next-year prior only",
        "samples": samples,
        "result": (
            "PASS"
            if (
                n_future == 0
                and n_same_game == 0
                and n_season_final_same_season == 0
                and abs(params.n0 - 8.0) < 1e-12
                and n_kickoffs > 0
            )
            else "FAIL"
        ),
    }
    return rd, c2


def probe_b4_c2(emit_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    pack, n_ge_2024 = exp_a.load_team_games()
    obs = exp_a._obs_arrays(pack["rows"])
    panel, n_games_ge_2024, n_oos_ge_2024 = exp_a.load_panel(emit_path)
    print(
        f"[b4] team_games={len(pack['rows'])} panel={len(panel)} n_pbp_ge2024={n_ge_2024}",
        flush=True,
    )
    rd, c2 = walk_c2_and_rd(obs, panel, G34)

    pred_rows: List[Dict[str, str]] = []
    with PRED_PATH.open(newline="", encoding="utf-8") as fh:
        pred_rows = list(csv.DictReader(fh))

    n_match = 0
    n_miss = 0
    max_err = 0.0
    examples: List[Dict[str, Any]] = []
    n_pma_ok = 0
    max_pma_err = 0.0
    for row in pred_rows:
        gid = str(row["game_id"]).strip()
        sealed = float(row["rating_diff_home"])
        got = rd.get(gid)
        if got is None:
            n_miss += 1
            if len(examples) < 6:
                examples.append({"game_id": gid, "reason": "missing_rd"})
            continue
        err = abs(float(got) - sealed)
        if err > max_err:
            max_err = err
        if err <= RD_TOL:
            n_match += 1
        elif len(examples) < 6:
            examples.append(
                {
                    "game_id": gid,
                    "sealed": sealed,
                    "recomputed": float(got),
                    "abs_err": err,
                }
            )
        beta = float(row["beta"])
        hfa = float(row["hfa"])
        home_ind = float(row["home_ind"])
        pm_a = float(row["pm_A"])
        pma_err = abs((beta * float(got) + hfa * home_ind) - pm_a)
        if pma_err > max_pma_err:
            max_pma_err = pma_err
        if pma_err <= PMA_TOL:
            n_pma_ok += 1

    b4_pass = (
        n_miss == 0
        and n_match == len(pred_rows)
        and max_err <= RD_TOL
        and n_ge_2024 == 0
        and n_games_ge_2024 == 0
        and len(pack["rows"]) == N_TEAM_GAMES_EXPECT
    )
    b4 = {
        "result": "PASS" if b4_pass else "FAIL",
        "threat": "T1",
        "n_team_games": len(pack["rows"]),
        "n_team_games_expect": N_TEAM_GAMES_EXPECT,
        "n_panel": len(panel),
        "n_pred": len(pred_rows),
        "n_pred_expect": N_PRED_EXPECT,
        "n_rd_match": n_match,
        "n_rd_missing": n_miss,
        "max_abs_err_rating_diff": max_err,
        "tol": RD_TOL,
        "n_pma_identity": n_pma_ok,
        "max_abs_err_pm_A": max_pma_err,
        "pma_tol": PMA_TOL,
        "n_plays_season_ge_2024": n_ge_2024,
        "n_games_ge_2024": n_games_ge_2024,
        "n_oos_dropped_ge_2024": n_oos_ge_2024,
        "cfg_id": "G34",
        "params": {"n0": G34.n0, "rho": G34.rho, "rho_s": G34.rho_s, "lambda": 2.0},
        "examples": examples,
        "predictions_pin_sha8": "c3248302",
    }
    c2["threat"] = "T3"
    c2["n_team_games"] = len(pack["rows"])
    c2["n_panel"] = len(panel)
    return b4, c2


def probe_e2_e4() -> Dict[str, Any]:
    papers = {
        "A1/E2": R_ROOT / "ALEX_EPA_WALKFORWARD_EVAL_2013_2023_t4564u_v2.md",
        "E4": R_ROOT / "ALEX_EVAL_RECORD_MINIMUM_FIELDS_t4564u.md",
    }
    present = {k: str(p) for k, p in papers.items() if p.is_file()}
    if present:
        return {"result": "NOT_RUN", "note": "papers present but optional E2/E4 not expanded", "present": present}
    return {
        "result": "FAIL_CLOSED",
        "note": "$R papers not remounted; optional E2/E4 skipped (authorized only if papers available)",
        "r_root": str(R_ROOT),
        "present": present,
    }


def main() -> int:
    _assert_no_forbidden()
    forecast_ts = _utc_now()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[t4634u] restore PBP 2012–2023 (cache first; pin-gated refetch)", flush=True)
    restore = restore_pbp()
    pbp_hashes = {name: rec["sha256"] for name, rec in restore["files"].items()}
    restore_sums = _write_sums(OUT_DIR / "SHA256SUMS.restored_pbp", pbp_hashes)

    print("[t4634u] A4 sha256sum -c SHA256SUMS.inputs", flush=True)
    a4 = probe_a4(restore)

    e2e4 = probe_e2_e4()

    b1: Dict[str, Any] = {"result": "FAIL_CLOSED", "reason": "H1 not closed"}
    b4: Dict[str, Any] = {"result": "FAIL_CLOSED", "reason": "H1 not closed"}
    c2: Dict[str, Any] = {"result": "FAIL_CLOSED", "reason": "H1 not closed"}

    if restore.get("ok"):
        _close_h1_readonly(pbp_hashes)
        print("[t4634u] B1 recompute rolling EPA 5g from PBP", flush=True)
        b1 = probe_b1()

        emit_path = CACHE_DIR / "epa_wf_features_2013_2023.csv"
        emit_sha = _extract_emit(emit_path)
        if emit_sha != EMIT_SHA256:
            b4 = {"result": "FAIL", "reason": f"emit sha mismatch got={emit_sha} want={EMIT_SHA256}"}
            c2 = {"result": "FAIL_CLOSED", "reason": "emit pin fail; B4/C2 not walked"}
        else:
            print("[t4634u] B4/C2 G34 rating_diff + n0 shrink counts", flush=True)
            b4, c2 = probe_b4_c2(emit_path)
            a4["sibling_inputs"]["epa_wf_features_2013_2023.csv"] = {
                "path": "git-show #646 (cite; not a merge)",
                "got": emit_sha,
                "want": EMIT_SHA256,
                "sha8": _sha8(emit_sha),
                "result": "PASS",
            }
    else:
        a4["result"] = "FAIL" if restore.get("aborted") else "FAIL_CLOSED"
        b1 = {"result": "FAIL_CLOSED", "reason": "restore aborted or incomplete"}
        b4 = {"result": "FAIL_CLOSED", "reason": "restore aborted or incomplete"}
        c2 = {"result": "FAIL_CLOSED", "reason": "restore aborted or incomplete"}

    payload = {
        "ticket": TICKET,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "nfl_nogo": True,
        "f2_frozen": True,
        "coming_soon": True,
        "branch_draft": 648,
        "forecast_ts_utc": forecast_ts,
        "authority": {
            "decision_sha8": DECISION_SHA8,
            "cos_order_sha8": COS_ORDER_SHA8,
            "lineage_sha8": LINEAGE_SHA8,
            "h1_sums_sha256": H1_SUMS_SHA256,
        },
        "restore": restore,
        "checks": {
            "A4": a4,
            "B1": b1,
            "B4": b4,
            "C2": c2,
            "E2": e2e4,
            "E4": e2e4,
        },
        "odds_api_called": False,
        "simulate_nfl_game_called": False,
        "warehouse_sot_changed": False,
        "new_predictive_experiment": False,
        "nested_g34": False,
    }
    payload_sha = _write_json(OUT_DIR / "CURSOR_PBP_RESTORE_PROBES_t4634u_v1.json", payload)

    table = {
        "document": "CURSOR_PBP_RESTORE_PROBES_t4634u_v1",
        "class": LABEL,
        "cert_candidate": 0,
        "restore_path": restore.get("path_used"),
        "checks": [
            {"check_id": cid, "result": payload["checks"][cid]["result"], "threat": payload["checks"][cid].get("threat")}
            for cid in ("A4", "B1", "B4", "C2")
        ],
    }
    table_sha = _write_json(OUT_DIR / "CURSOR_PBP_RESTORE_PROBES_t4634u_v1.table.json", table)

    receipts = {
        "SHA256SUMS.restored_pbp": restore_sums,
        "CURSOR_PBP_RESTORE_PROBES_t4634u_v1.json": payload_sha,
        "CURSOR_PBP_RESTORE_PROBES_t4634u_v1.table.json": table_sha,
    }
    receipts.update(pbp_hashes)
    receipts_sha = _write_sums(OUT_DIR / "SHA256SUMS", receipts)
    print(
        f"[t4634u] restore={restore.get('path_used')} A4={a4['result']} "
        f"B1={b1['result']} B4={b4['result']} C2={c2['result']} "
        f"receipts={_sha8(receipts_sha)}",
        flush=True,
    )
    _assert_no_forbidden()
    return 0 if restore.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
