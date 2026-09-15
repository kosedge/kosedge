"""CFBD API auth probe — status only, never print or persist secrets.

Looks at existing env patterns used in-repo:
  CFBD_API_KEY, CFBD_KEY, BEARER_TOKEN

Does not invent keys. Does not write the token anywhere.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

CFBD_BASE = "https://api.collegefootballdata.com"
ENV_CANDIDATES = ("CFBD_API_KEY", "CFBD_KEY", "BEARER_TOKEN")


def _key_present() -> bool:
    for name in ENV_CANDIDATES:
        val = (os.environ.get(name) or "").strip()
        if val:
            return True
    return False


def _key_source() -> Optional[str]:
    for name in ENV_CANDIDATES:
        if (os.environ.get(name) or "").strip():
            return name
    return None


def probe_cfbd(*, timeout: int = 20) -> Dict[str, Any]:
    """GET /conferences. Report HTTP status. Never include the token."""
    source = _key_source()
    present = bool(source)
    headers = {"Accept": "application/json", "User-Agent": "kosedge-cfb-owned-research/1.0"}
    if present:
        token = (os.environ.get(source) or "").strip()
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{CFBD_BASE}/conferences", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(resp.status)
            body = resp.read(64)
            ok = 200 <= status < 300
            return {
                "endpoint": "/conferences",
                "key_present_in_this_process": present,
                "key_env_name": source,
                "http_status": status,
                "ok": ok,
                "body_prefix_len": len(body),
                "ryan_account_dependency": (
                    None
                    if ok
                    else "If this is 401/403 with a present key, rotate via Ryan's CollegeFootballData account and update Railway CFBD_API_KEY. Do not invent a key."
                ),
            }
    except urllib.error.HTTPError as exc:
        return {
            "endpoint": "/conferences",
            "key_present_in_this_process": present,
            "key_env_name": source,
            "http_status": int(exc.code),
            "ok": False,
            "reason": f"HTTP {exc.code}",
            "ryan_account_dependency": (
                "CFBD_API_KEY is not in this process. Railway model-service production lists a CFBD_API_KEY variable. "
                "A working replacement key requires Ryan's CollegeFootballData account (and Railway variable update). "
                "Starter Pack is not a substitute for the API."
                if not present
                else "Key present but CFBD rejected it (401/403). Replacement requires Ryan's CollegeFootballData account."
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "endpoint": "/conferences",
            "key_present_in_this_process": present,
            "key_env_name": source,
            "http_status": None,
            "ok": False,
            "reason": type(exc).__name__,
            "ryan_account_dependency": "Network/probe failed; historical PBP work does not block on CFBD.",
        }
