#!/usr/bin/env python3
"""IMV v2.7 helper — pin bash-3.2-safe builder v2.4.1.

Layer on frozen v21–v26. Do not edit those files.
v26 check-pins only knows the three v2.4 shells. The W4 Mac stop
(PACK_ARG[@] unbound on bash 3.2 / set -u) is fixed in a NEW shell,
nfl-imv-feature-build-v2.4.1.sh. Pinning that file requires this
new helper.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import nfl_imv_v21 as v21
import nfl_imv_v26 as v26

RULING = "bash32-pack-arg"
SCRIPT_ID = "nfl-imv-v2.7"
V26_PIN = "b86b64d5ffcfe403fbf063db695a79e0ca1c65daecb869cfe45180d71d3d9ffe"
BUILD_241_NAME = "nfl-imv-feature-build-v2.4.1.sh"
BUILD_241_PIN = "c3a521569e80e980600e07829f0d9535cd65efda5efc7843e79f43bfdc758a0a"

BUNDLE_HELPERS = v26.BUNDLE_HELPERS + ("nfl_imv_v27.py",)
BUNDLE_SHELLS = v26.BUNDLE_SHELLS + (BUILD_241_NAME,)
SHELL_PINS = {
    **v26.SHELL_PINS,
    BUILD_241_NAME: BUILD_241_PIN,
}
HELPER_PINS = {
    **v26.HELPER_PINS,
    "nfl_imv_v26.py": V26_PIN,
}

SQL_V3_PIN = v26.SQL_V3_PIN
V21_PIN = v26.V21_PIN
V22_PIN = v26.V22_PIN
V23_PIN = v26.V23_PIN
V24_PIN = v26.V24_PIN
V25_PIN = v26.V25_PIN
V2_5_SHA256SUMS_PIN = v26.V2_5_SHA256SUMS_PIN
PINNED_V3_COLUMNS = v26.PINNED_V3_COLUMNS
configure_sql_bind = v26.configure_sql_bind
bind_prod_sql = v26.bind_prod_sql
load_prod_export = v26.load_prod_export
read_prod_export_csv = v26.read_prod_export_csv
parity_local_w_vs_prod_w_minus_1 = v26.parity_local_w_vs_prod_w_minus_1
write_store_sha256sums_last = v26.write_store_sha256sums_last


def stamp_helper_shas(
    imv_dir: Path,
    *,
    sums_v25: Optional[Path] = None,
    sums: Optional[Path] = None,
) -> Dict[str, Any]:
    rec = v26.stamp_helper_shas(imv_dir, sums_v25=sums_v25, sums=sums)
    root = Path(imv_dir)
    flags = list(rec.get("flags") or [])
    v26_got = v21.sha256_file(root / "nfl_imv_v26.py") if (root / "nfl_imv_v26.py").is_file() else None
    if v26_got is not None and v26_got != V26_PIN:
        flags.append("HELPER_V26_SHA_MISMATCH")
    v27_got = v21.sha256_file(root / "nfl_imv_v27.py") if (root / "nfl_imv_v27.py").is_file() else None
    if v27_got is None:
        flags.append("HELPER_V27_MISSING")
    build241 = v21.sha256_file(root / BUILD_241_NAME) if (root / BUILD_241_NAME).is_file() else None
    if build241 is None:
        flags.append("SHELL_FILE_MISSING")
    elif build241 != BUILD_241_PIN:
        flags.append(f"SHELL_{BUILD_241_NAME}_SHA_MISMATCH")
    shells = dict(rec.get("shells") or {})
    shells[BUILD_241_NAME] = build241
    rec["v26"] = v26_got
    rec["v26_pin"] = V26_PIN
    rec["v27"] = v27_got
    rec["shells"] = shells
    rec["shell_pins"] = dict(SHELL_PINS)
    rec["flags"] = flags
    rec["ok"] = not flags
    rec["flag"] = None if not flags else flags[0]
    rec["ruling"] = RULING
    return rec


def write_helper_stamps(out_dir: Path, imv_dir: Path) -> Dict[str, Any]:
    rec = stamp_helper_shas(imv_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for key in ("v21", "v22", "v23", "v24", "v25", "v26", "v27"):
        (out / f"HELPER_{key.upper()}.sha256").write_text((rec.get(key) or "") + "\n", encoding="utf-8")
    (out / "HELPERS.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def write_helper_bundle(imv_dir: Path, dest: Path) -> Dict[str, Any]:
    rec = v26.write_helper_bundle(imv_dir, dest)
    src = Path(imv_dir)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    copied = list(rec.get("copied") or [])
    for name in (
        "nfl_imv_v27.py",
        BUILD_241_NAME,
        "nfl-imv-mac-runbook-v2.4.3.md",
        "nfl-imv-mac-runbook-v2.4.3.diff",
        "nfl-imv-v2.6.1-bash32-trace.md",
    ):
        fp = src / name
        if fp.is_file():
            dest.joinpath(name).write_bytes(fp.read_bytes())
            copied.append(name)
    rec = stamp_helper_shas(src)
    rec["copied"] = copied
    rec["bundle_dir"] = str(dest)
    (dest / "BUNDLE.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return rec


def _cmd_parity(args: argparse.Namespace) -> int:
    return v26._cmd_parity(args)


def _cmd_helpers(args: argparse.Namespace) -> int:
    rec = write_helper_stamps(Path(args.out), Path(args.imv_dir))
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 6


def _cmd_bundle(args: argparse.Namespace) -> int:
    rec = write_helper_bundle(Path(args.imv_dir), Path(args.out))
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 6


def _cmd_pins(args: argparse.Namespace) -> int:
    rec = stamp_helper_shas(
        Path(args.imv_dir),
        sums_v25=Path(args.sums_v25) if str(args.sums_v25 or "").strip() else None,
        sums=Path(args.sums) if str(args.sums or "").strip() else None,
    )
    print(json.dumps(rec, indent=2))
    return 0 if rec.get("ok") else 6


def _cmd_sums(args: argparse.Namespace) -> int:
    return v26._cmd_sums(args)


def _cmd_sql_pin(args: argparse.Namespace) -> int:
    return v26._cmd_sql_pin(args)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="nfl_imv_v27")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parity")
    p.add_argument("--local", required=True)
    p.add_argument("--prod-export", default="")
    p.add_argument("--week-cap", type=int, required=True)
    p.add_argument("--grade", default="cert", choices=("cert", "plumbing"))
    p.add_argument("--build-started", default="")
    p.set_defaults(func=_cmd_parity)
    h = sub.add_parser("stamp-helpers")
    h.add_argument("--imv-dir", required=True)
    h.add_argument("--out", required=True)
    h.set_defaults(func=_cmd_helpers)
    b = sub.add_parser("write-bundle")
    b.add_argument("--imv-dir", required=True)
    b.add_argument("--out", required=True)
    b.set_defaults(func=_cmd_bundle)
    c = sub.add_parser("check-pins")
    c.add_argument("--imv-dir", required=True)
    c.add_argument("--sums-v25", default="")
    c.add_argument("--sums", default="")
    c.set_defaults(func=_cmd_pins)
    s = sub.add_parser("write-store-sums")
    s.add_argument("--store", required=True)
    s.set_defaults(func=_cmd_sums)
    q = sub.add_parser("check-sql-pin")
    q.add_argument("--sql", default="")
    q.add_argument("--pin", default="")
    q.set_defaults(func=_cmd_sql_pin)
    args = parser.parse_args(argv)
    if args.cmd == "parity":
        args.prod_export = (args.prod_export or os.environ.get("IMV_PROD_EXPORT") or "").strip()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
