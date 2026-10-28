#!/usr/bin/env python3
"""t4615u Unblock A: SET TRANSACTION READ ONLY + SELECT depth/injury nowcast.

Never prints tokens or DATABASE_* URLs. Never DML/DDL. Never invents nfl_dp_* rows.
"""

from __future__ import annotations

import json
import os
import re
import socket
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import urlparse, urlunparse

try:
    import psycopg
except ImportError:  # pragma: no cover
    print(json.dumps({"ok": False, "error": "psycopg_missing"}))
    raise SystemExit(2)

SEASON = 2026
WEEK = 8
TABLES = (
    "nfl_dp_depth_chart_weekly",
    "nfl_dp_official_depth_charts",
    "nfl_dp_injuries",
)
URL_RE = re.compile(r"(postgres(?:ql)?://\S+)|([A-Za-z0-9._%+-]+:[^@\s]{4,}@)", re.I)


def _redact(text: str) -> str:
    cleaned = URL_RE.sub("[REDACTED]", str(text))
    cleaned = re.sub(r"password=[^&\s]+", "password=[REDACTED]", cleaned, flags=re.I)
    return cleaned[:240]


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _classify_host(host: str) -> str:
    h = (host or "").lower()
    if "railway.internal" in h:
        return "internal"
    if "rlwy.net" in h or "railway.app" in h:
        return "proxy"
    if h in {"127.0.0.1", "localhost"}:
        return "local"
    return "other"


def _pick_url() -> Tuple[str, str, str]:
    """Return (dsn, source_key, host_kind). Prefer public URL off the Railway mesh."""
    public = (os.environ.get("DATABASE_PUBLIC_URL") or "").strip()
    private = (os.environ.get("DATABASE_URL") or "").strip()
    for key, raw in (("DATABASE_PUBLIC_URL", public), ("DATABASE_URL", private)):
        if not raw:
            continue
        parsed = urlparse(raw)
        host = parsed.hostname or ""
        kind = _classify_host(host)
        if key == "DATABASE_URL" and kind == "internal":
            continue
        return raw, key, kind
    if private:
        parsed = urlparse(private)
        return private, "DATABASE_URL", _classify_host(parsed.hostname or "")
    return "", "", ""


def _dsn_with_ssl(raw: str, host_kind: str) -> str:
    parsed = urlparse(raw)
    q = parsed.query or ""
    if "sslmode=" not in q.lower() and host_kind == "proxy":
        q = (q + "&" if q else "") + "sslmode=require"
    return urlunparse(parsed._replace(query=q))


def _write_0444(path: Path, blob: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(stat.S_IWUSR | stat.S_IRUSR)
    path.write_bytes(blob)
    path.chmod(0o444)


def _count_week(
    cur: Any, table: str
) -> Dict[str, Any]:
    cur.execute(
        f"""
        SELECT
          COUNT(*)::int AS n,
          COUNT(DISTINCT team)::int AS teams,
          COALESCE(MAX(week), 0)::int AS max_week,
          COALESCE(MIN(week), 0)::int AS min_week
        FROM {table}
        WHERE season = %s AND week <= %s
        """,
        (SEASON, WEEK),
    )
    row = cur.fetchone()
    cur.execute(
        f"""
        SELECT week::int, COUNT(*)::int AS n, COUNT(DISTINCT team)::int AS teams
        FROM {table}
        WHERE season = %s AND week <= %s
        GROUP BY week
        ORDER BY week DESC
        LIMIT 8
        """,
        (SEASON, WEEK),
    )
    by_week = [{"week": int(w), "n": int(n), "teams": int(t)} for w, n, t in cur.fetchall()]
    return {
        "table": table,
        "n": int(row[0] or 0),
        "teams": int(row[1] or 0),
        "max_week": int(row[2] or 0),
        "min_week": int(row[3] or 0),
        "by_week": by_week,
    }


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    dest = Path(
        os.environ.get("T4615U_EVIDENCE")
        or (sys.argv[1] if len(sys.argv) > 1 else "/tmp/t4615u_depth_db_ro.json")
    )
    raw, source_key, host_kind = _pick_url()
    evidence: Dict[str, Any] = {
        "ticket": "t4615u",
        "audited_at_utc": _fmt_utc(now),
        "cert_candidate": 0,
        "read_only": True,
        "dml_ddl": False,
        "invented": False,
        "url_present": bool(raw),
        "url_source_key": source_key,
        "host_kind": host_kind,
        "connect_ok": False,
        "transaction_read_only": False,
        "tables": {},
        "missing_tables": [],
        "ok": False,
        "blocker": "",
    }
    if not raw:
        evidence["blocker"] = "ACCESS_BLOCKED: no DATABASE_PUBLIC_URL / DATABASE_URL in railway run env"
        _write_0444(dest, (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode())
        print(json.dumps({k: evidence[k] for k in ("ok", "blocker", "url_present", "host_kind")}))
        return 2

    parsed = urlparse(raw)
    host = parsed.hostname or ""
    port = parsed.port or 5432
    evidence["host_suffix"] = host[-24:] if host else ""
    evidence["port"] = port
    try:
        sock = socket.create_connection((host, port), timeout=8)
        sock.close()
        evidence["tcp_open"] = True
    except Exception as exc:
        evidence["tcp_open"] = False
        evidence["tcp_error"] = f"{type(exc).__name__}: {_redact(str(exc))}"

    dsn = _dsn_with_ssl(raw, host_kind)
    try:
        with psycopg.connect(dsn, connect_timeout=15, autocommit=False) as conn:
            evidence["connect_ok"] = True
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SHOW transaction_read_only")
                ro = str(cur.fetchone()[0]).lower() in {"on", "true", "1"}
                evidence["transaction_read_only"] = ro
                if not ro:
                    conn.rollback()
                    evidence["blocker"] = "transaction_read_only not on"
                    raise RuntimeError("not_read_only")
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = ANY(%s)
                    """,
                    (list(TABLES),),
                )
                present = {str(r[0]) for r in cur.fetchall()}
                evidence["missing_tables"] = [t for t in TABLES if t not in present]
                for table in TABLES:
                    if table not in present:
                        evidence["tables"][table] = {"present": False}
                        continue
                    stats = _count_week(cur, table)
                    stats["present"] = True
                    evidence["tables"][table] = stats
            conn.rollback()
    except Exception as exc:
        if not evidence["blocker"]:
            evidence["blocker"] = f"{type(exc).__name__}: {_redact(str(exc))}"
        evidence["connect_ok"] = evidence["connect_ok"] and "not_read_only" not in str(exc)

    depth = evidence["tables"].get("nfl_dp_depth_chart_weekly") or {}
    official = evidence["tables"].get("nfl_dp_official_depth_charts") or {}
    injuries = evidence["tables"].get("nfl_dp_injuries") or {}
    depth_rows = int(depth.get("n") or 0) + int(official.get("n") or 0)
    injury_rows = int(injuries.get("n") or 0)
    evidence["ok"] = bool(
        evidence["connect_ok"]
        and evidence["transaction_read_only"]
        and (depth.get("present") or official.get("present"))
        and (depth_rows > 0 or injury_rows > 0)
    )
    if evidence["ok"]:
        evidence["blocker"] = ""
    elif not evidence["blocker"]:
        evidence["blocker"] = (
            "RO session opened but depth/injury nowcast tables empty or missing; "
            "no nfl_dp_* rows invented"
        )
    evidence["warehouse_rows_read"] = depth_rows + injury_rows
    _write_0444(dest, (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode())
    print(
        json.dumps(
            {
                "ok": evidence["ok"],
                "connect_ok": evidence["connect_ok"],
                "transaction_read_only": evidence["transaction_read_only"],
                "host_kind": evidence["host_kind"],
                "url_source_key": evidence["url_source_key"],
                "warehouse_rows_read": evidence["warehouse_rows_read"],
                "missing_tables": evidence["missing_tables"],
                "depth_n": depth.get("n"),
                "depth_max_week": depth.get("max_week"),
                "official_n": official.get("n"),
                "injuries_n": injuries.get("n"),
                "injuries_max_week": injuries.get("max_week"),
                "blocker": evidence["blocker"],
                "evidence_path": str(dest),
            },
            sort_keys=True,
        )
    )
    return 0 if evidence["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
