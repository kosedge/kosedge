# model-service/services/odds_api.py
import os
import requests
import logging

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"

def assert_odds_key_present():
    if not ODDS_API_KEY:
        raise RuntimeError("Odds API key missing")

def fetch_odds(endpoint: str, params: dict):
    assert_odds_key_present()

    resp = requests.get(
        f"{BASE_URL}/{endpoint}",
        params={**params, "apiKey": ODDS_API_KEY},
        timeout=15,
    )

    resp.raise_for_status()

    #T5fc490bc771b47611274e13fc244036c
    remaining = resp.headers.get("x-requests-remaining")
    used = resp.headers.get("x-requests-used")

    logging.info(
        f"[ODDS_API] Remaining credits: {remaining}, Used this request: {used}"
    )

    return resp.json()