"""Sport stubs — same ledger; adapters enable later without schema rewrite."""

from __future__ import annotations

from typing import Any, Dict


def nfl_adapter_status() -> Dict[str, Any]:
    return {
        "sport": "nfl",
        "status": "stub",
        "import_path": None,
        "notes": (
            "Use POST /model-tracker/picks with sport=nfl for desk logs. "
            "Do not auto-tag public props PLAY/LEAN; hang off spine means only."
        ),
        "proof_lake": "/proof/performance?sport=nfl",
    }


def nba_adapter_status() -> Dict[str, Any]:
    return {
        "sport": "nba",
        "status": "stub",
        "notes": "Ledger accepts sport=nba; publish-policy import TBD.",
    }


def mlb_adapter_status() -> Dict[str, Any]:
    return {
        "sport": "mlb",
        "status": "stub",
        "notes": "Ledger accepts sport=mlb; board-health CLV remains separate.",
    }


def wnba_adapter_status() -> Dict[str, Any]:
    return {
        "sport": "wnba",
        "status": "stub",
        "notes": "Ledger accepts sport=wnba; adapter TBD.",
    }


def all_stub_statuses() -> Dict[str, Dict[str, Any]]:
    return {
        "nfl": nfl_adapter_status(),
        "nba": nba_adapter_status(),
        "mlb": mlb_adapter_status(),
        "wnba": wnba_adapter_status(),
    }
