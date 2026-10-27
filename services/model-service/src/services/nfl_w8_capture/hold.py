"""Odds API hold — default ON. IMV ACCEPT KEEP-ack 91b13a45 / paper 2539d916.

R1: KEEP ack replaces ONLY NFL_W8_PR_ROTATE_CONFIRM. Lift still requires
    NFL_W8_H1_AUTH_CITE == 89fdd45f PLUS the KEEP STATEMENT fields.
R2: Eng gate verifies ALL of:
      CREDENTIAL_POLICY == KEEP_EXISTING
      KEEP_AUTH_SHA8 == a9ae5ae6
      VERIFY_PASS_SHA8 == e64e73ac
      H1C_AUTH_SHA8 == 89fdd45f
      T4500U_SHA8 == 20325274
      ROTATION_ASSERTED == false
R3: NFL_W8_PR_ROTATE_CONFIRM truthy on KEEP path → FAIL CLOSED (not a lift).
R4: Process-scoped env= / one-process only. No Railway-global.
R7: Paper ACCEPT does not authorize live lift / Odds / capture / merge / deploy.

No secret values. Flipping NFL_W8_ODDS_API_HOLD / ODDS_API_HOLD off is not enough.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

HOLD_ENV = "NFL_W8_ODDS_API_HOLD"
GLOBAL_HOLD_ENV = "ODDS_API_HOLD"

# Paper STATEMENT field names (2539d916). R2 verifies these exact keys.
FIELD_CREDENTIAL_POLICY = "CREDENTIAL_POLICY"
FIELD_KEEP_AUTH_SHA8 = "KEEP_AUTH_SHA8"
FIELD_VERIFY_PASS_SHA8 = "VERIFY_PASS_SHA8"
FIELD_H1C_AUTH_SHA8 = "H1C_AUTH_SHA8"
FIELD_T4500U_SHA8 = "T4500U_SHA8"
FIELD_ROTATION_ASSERTED = "ROTATION_ASSERTED"

# R1: original H-1 cite env — still required; KEEP ack does not replace it.
ENV_H1_AUTH_CITE = "NFL_W8_H1_AUTH_CITE"
# STALE / conflicting. Truthy → FAIL CLOSED on KEEP path (R3).
ENV_PR_ROTATE_CONFIRM = "NFL_W8_PR_ROTATE_CONFIRM"

POLICY_KEEP_EXISTING = "KEEP_EXISTING"
H1_AUTH_CITE = "89fdd45f"
KEEP_DECISION_CITE = "a9ae5ae6"
VERIFY_PASS_CITE = "e64e73ac"
T4500U_DECISION_CITE = "20325274"
KEEP_ACK_PAPER_SHA8 = "2539d916"
IMV_ACCEPT_KEEP_ACK_SHA8 = "91b13a45"
SECRET_MATERIAL = "none"


class OddsApiHoldError(RuntimeError):
    """Raised when any Odds API network path is attempted under hold."""


def _source(env: Optional[Mapping[str, str]] = None) -> Mapping[str, str]:
    return env if env is not None else os.environ


def _truthy(raw: str) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "y", "on", "640"}


def _falsey_explicit(raw: str) -> bool:
    return str(raw or "").strip().lower() in {"0", "false", "no", "n", "off"}


def keep_policy_ack_record() -> dict[str, Any]:
    """Normative non-secret KEEP STATEMENT (R6). No secrets."""
    return {
        "CREDENTIAL_POLICY": POLICY_KEEP_EXISTING,
        "KEEP_AUTH_SHA8": KEEP_DECISION_CITE,
        "VERIFY_PASS_SHA8": VERIFY_PASS_CITE,
        "H1C_AUTH_SHA8": H1_AUTH_CITE,
        "T4500U_SHA8": T4500U_DECISION_CITE,
        "ROTATION_ASSERTED": False,
        "SECRET_MATERIAL": SECRET_MATERIAL,
        "paper_sha8": KEEP_ACK_PAPER_SHA8,
        "imv_accept_sha8": IMV_ACCEPT_KEEP_ACK_SHA8,
        "r1_h1_cite_env": ENV_H1_AUTH_CITE,
        "r1_h1_cite": H1_AUTH_CITE,
        "r7_live_not_authorized": True,
    }


def hold_lift_state(env: Optional[Mapping[str, str]] = None) -> dict[str, Any]:
    source = _source(env)
    # R1: H-1 cite env is independent of KEEP fields.
    h1_cite = str(source.get(ENV_H1_AUTH_CITE) or "").strip().lower()
    h1_cite_ok = h1_cite == H1_AUTH_CITE

    policy = str(source.get(FIELD_CREDENTIAL_POLICY) or "").strip()
    keep = str(source.get(FIELD_KEEP_AUTH_SHA8) or "").strip().lower()
    verify = str(source.get(FIELD_VERIFY_PASS_SHA8) or "").strip().lower()
    h1c = str(source.get(FIELD_H1C_AUTH_SHA8) or "").strip().lower()
    t4500 = str(source.get(FIELD_T4500U_SHA8) or "").strip().lower()
    rotation_raw = str(source.get(FIELD_ROTATION_ASSERTED) or "").strip()

    policy_ok = policy == POLICY_KEEP_EXISTING
    keep_ok = keep == KEEP_DECISION_CITE
    verify_ok = verify == VERIFY_PASS_CITE
    h1c_ok = h1c == H1_AUTH_CITE
    t4500_ok = t4500 == T4500U_DECISION_CITE
    # R2: ROTATION_ASSERTED == false. Unset is not an assertion; truthy fails.
    if rotation_raw == "":
        rotation_asserted = False
        rotation_ok = True
    elif _falsey_explicit(rotation_raw):
        rotation_asserted = False
        rotation_ok = True
    else:
        rotation_asserted = True
        rotation_ok = False

    rotate = str(source.get(ENV_PR_ROTATE_CONFIRM) or "").strip()
    rotate_truthy = _truthy(rotate)

    keep_fields_ok = (
        policy_ok and keep_ok and verify_ok and h1c_ok and t4500_ok and rotation_ok
    )
    # R3: truthy rotate-confirm FAIL CLOSED even if KEEP fields are complete.
    authorized = h1_cite_ok and keep_fields_ok and (not rotate_truthy)
    return {
        "CREDENTIAL_POLICY": policy,
        "KEEP_AUTH_SHA8": keep,
        "VERIFY_PASS_SHA8": verify,
        "H1C_AUTH_SHA8": h1c,
        "T4500U_SHA8": t4500,
        "ROTATION_ASSERTED": rotation_asserted,
        "SECRET_MATERIAL": SECRET_MATERIAL,
        "h1_cite": h1_cite,
        "h1_cite_ok": h1_cite_ok,
        "policy_ok": policy_ok,
        "keep_ok": keep_ok,
        "verify_ok": verify_ok,
        "h1c_ok": h1c_ok,
        "cite_ok": h1_cite_ok,
        "t4500u_ok": t4500_ok,
        "rotation_ok": rotation_ok,
        "rotation_asserted": rotation_asserted,
        "rotate_present": bool(rotate),
        "rotate_rejected": rotate_truthy,
        "rotate_stale": True,
        "rotate_ok": False,
        "keep_fields_ok": keep_fields_ok,
        "authorized": authorized,
        "h1_auth_cite_required": H1_AUTH_CITE,
        "keep_ack_required": KEEP_DECISION_CITE,
        "verify_cite_required": VERIFY_PASS_CITE,
        "t4500u_decision": T4500U_DECISION_CITE,
        "paper_sha8": KEEP_ACK_PAPER_SHA8,
        "imv_accept_sha8": IMV_ACCEPT_KEEP_ACK_SHA8,
        "scope": "process-scoped env= only; not Railway-global",
        "r7_live_not_authorized": True,
    }


def odds_api_hold_is_on(env: Optional[Mapping[str, str]] = None) -> bool:
    """Default ON. R1+R2 KEEP-ack lift; R3 rotate-confirm never lifts."""
    source = _source(env)
    _ = source.get(HOLD_ENV)
    _ = source.get(GLOBAL_HOLD_ENV)
    return not bool(hold_lift_state(source)["authorized"])


def assert_odds_api_hold(env: Optional[Mapping[str, str]] = None) -> None:
    if odds_api_hold_is_on(env):
        state = hold_lift_state(env)
        raise OddsApiHoldError(
            "H-1a/H-1c Odds API hold in force. "
            "R1: lift needs NFL_W8_H1_AUTH_CITE=89fdd45f PLUS KEEP-ack fields. "
            "R2: CREDENTIAL_POLICY=KEEP_EXISTING KEEP_AUTH_SHA8=a9ae5ae6 "
            "VERIFY_PASS_SHA8=e64e73ac H1C_AUTH_SHA8=89fdd45f "
            "T4500U_SHA8=20325274 ROTATION_ASSERTED=false "
            f"(paper {KEEP_ACK_PAPER_SHA8}; IMV ACCEPT {IMV_ACCEPT_KEEP_ACK_SHA8}). "
            "R3: NFL_W8_PR_ROTATE_CONFIRM truthy is FAIL CLOSED (not a lift). "
            "R4: process-scoped env= only; not Railway-global. "
            f"h1_cite_ok={state['h1_cite_ok']} policy_ok={state['policy_ok']} "
            f"keep_ok={state['keep_ok']} verify_ok={state['verify_ok']} "
            f"h1c_ok={state['h1c_ok']} t4500u_ok={state['t4500u_ok']} "
            f"rotation_ok={state['rotation_ok']} "
            f"rotate_rejected={state['rotate_rejected']}. "
            "R7: paper ACCEPT does not authorize live Odds. "
            "nfl_w8_capture will not call The Odds API or log ODDS_API_KEY."
        )


def keep_ack_env(**extra: str) -> dict[str, str]:
    """Process-scoped KEEP-ack + R1 H-1 cite. No secrets. Not a Railway write."""
    env = {
        ENV_H1_AUTH_CITE: H1_AUTH_CITE,
        FIELD_CREDENTIAL_POLICY: POLICY_KEEP_EXISTING,
        FIELD_KEEP_AUTH_SHA8: KEEP_DECISION_CITE,
        FIELD_VERIFY_PASS_SHA8: VERIFY_PASS_CITE,
        FIELD_H1C_AUTH_SHA8: H1_AUTH_CITE,
        FIELD_T4500U_SHA8: T4500U_DECISION_CITE,
        FIELD_ROTATION_ASSERTED: "false",
    }
    env.update(extra)
    return env


def refuse_odds_fetch(
    *,
    endpoint: str = "sports/americanfootball_nfl/odds",
    params: Optional[Mapping[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> None:
    """Fail-closed default fetch path. Raises until R1+R2 KEEP-ack."""
    del endpoint, params
    assert_odds_api_hold(env)
