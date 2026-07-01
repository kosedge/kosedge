from __future__ import annotations

# model-service/services/odds_api.py
import os
import requests
import logging

BASE_URL = "https://api.the-odds-api.com/v4"
EMBEDDED_ODDS_API_BACKUP_KEY = "90a633a22cbe3597b2bceab5eb665d48"


def get_odds_api_keys() -> list[str]:
    keys: list[str] = []
    for raw_key in (
        os.getenv("ODDS_API_KEY"),
        os.getenv("ODDS_API_KEY_BACKUP"),
        EMBEDDED_ODDS_API_BACKUP_KEY,
    ):
        key = (raw_key or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def get_odds_api_key() -> str | None:
    keys = get_odds_api_keys()
    return keys[0] if keys else None

def assert_odds_key_present():
    if not get_odds_api_key():
        raise RuntimeError("Odds API key missing")

def fetch_odds(endpoint: str, params: dict):
    assert_odds_key_present()
    last_error: requests.HTTPError | None = None

    for api_key in get_odds_api_keys():
        resp = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={**params, "apiKey": api_key},
            timeout=15,
        )

        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            last_error = exc
            continue

        remaining = resp.headers.get("x-requests-remaining")
        used = resp.headers.get("x-requests-used")

        logging.info(
            f"[ODDS_API] Remaining credits: {remaining}, Used this request: {used}"
        )

        return resp.json()

    if last_error is not None:
        raise last_error

    raise RuntimeError("Odds API key missing")