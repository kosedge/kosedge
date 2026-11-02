"""Strip credentials / secret-shaped fields from artifacts (AC-6)."""

from __future__ import annotations

from typing import Any

_SECRET_KEYS = {
    "apikey",
    "api_key",
    "api-key",
    "authorization",
    "password",
    "secret",
    "token",
    "odds_api_key",
    "odds_api_key_backup",
    "x-api-key",
}


def _is_secret_key(key: str) -> bool:
    compact = key.strip().lower().replace("-", "_")
    if compact in _SECRET_KEYS:
        return True
    return compact.endswith("_key") or compact.endswith("_secret") or compact.endswith("_token")


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _is_secret_key(str(key)):
                out[str(key)] = "[REDACTED]"
            else:
                out[str(key)] = redact_secrets(item)
        return out
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    return value
