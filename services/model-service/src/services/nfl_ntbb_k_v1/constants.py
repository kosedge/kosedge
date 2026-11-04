"""NTBB-K SYNTHETIC pins. CERT=0. Spec numbers are not changed."""

from __future__ import annotations

from typing import Tuple

PACKAGE = "nfl_ntbb_k_v1"
PROFILE = "NTBB_K_SYNTHETIC_KERNEL_V1"
CERT = 0
CHANNEL = "SYNTHETIC"
DATA_LABEL = "SYNTHETIC"
FAMILY = "NTBB-K"
CONTROL = "NTBB"
ROLE = "SYNTHETIC_KERNEL"
WORKER = "B"
CLEAR = "92861"
TICKET = "t5343u"
RETURN_ID = "36205"
DESIGN_ID = "25194"
METADATA_14083 = "14083"
METADATA_TICKET = "t5344u"
CLARIFICATIONS_COMMIT = "cc5ce256abc3ef92475db32f92e6b17c87d6ea44"
CLARIFICATIONS_PATH = (
    "research/nfl_followthrough_20261103/NTBB_K_V1_NUMERICAL_CLARIFICATIONS.md"
)
CLARIFICATIONS_SHA256 = (
    "dd2fa8d041b652324c07b77aea2f2b589146213342a414b98e8bcc629d5bc3e8"
)
CLARIFICATIONS_BYTES = 3237
EVIDENCE_ID = "03972"
OWNER = "92a6ca83"
ALEX_PASS_SPEC = "4f8c5827"
SPEC_COMMIT = "2a2c91c9b839da2246a01596b203318295581914"
SPEC_PATH = "research/nfl_followthrough_20261103/NTBB_K_V1_SPEC.md"
SPEC_SHA256 = "2f3c215d7680dd5aa33a0a77690ece4ef70a0a8dbbebaac880750dd776ec66d7"
SPEC_BYTES = 11064

# Spec tail/moment/cap — do not silently change.
CAP_T = 512
TAIL_SF_MAX = 1e-12
MOMENT_BOUND_MAX = 1e-8
MASS_PLUS_TAIL_TOL = 1e-10
TRANSPOSE_TOL = 1e-10
COND_TRANSPOSE_TOL = 2e-12
JOINT_TRANSPOSE_TOL = 1e-10
IDENTITY_TOL = 1e-8
NORM_TOL = 1e-10
FUTURE_GRAD_STEP = 5e-6
FUTURE_GRAD_OPTIMIZER_STEP = 1e-5
FUTURE_GRAD_ABS_MAX = 1e-4

# Spec start values used as synthetic defaults (not fitted).
R_SYNTH = 20.0
C_SYNTH = 12.0

OUTPUT_LABEL = "RESEARCH_ONLY"
QUALIFICATION = "UNQUALIFIED"
SCIPY_STATUS = "ABSENT_NOT_EVALUABLE"
SCIPY_FITTING_ALGORITHM = "UNEXECUTED_DEPENDENCY_HELD"
ORACLE_MAX_ENUMERATED_TOTAL = 183
NO_INSTALL = True

# Preserve market PARTIAL evidence (do not rename 143 clocks verified).
PIN_JSONL_143_PROJECTION_SHA256 = (
    "bf5fd92e61f3f0bac9f964e7b57b7ac4996ba166c68bb853888c9fcdb0e9e2d7"
)
PIN_LEDGER_92861_SHA256 = (
    "6879ed43cc9e4ad7bef0a124bc0514ea7d1adb9af1775101e0bbcd6aad6d5e75"
)
PIN_LEDGER_81759_SHA256 = (
    "ce188c64f6d52c98ca76301455bf2654d30a6a59029cc5d7845944d7087bc5d7"
)

# Prior B demo cases (mu 4–12). NOT the executed root fixtures. Kept as rename-honest history.
DEMO_SMALL_NINE: Tuple[tuple, ...] = (
    ("DEMO_T0_NORM", 4.0, R_SYNTH, 0.50, C_SYNTH, 0.0, 0.0, 0.0, "demo_small"),
    ("DEMO_SYM_P", 8.0, R_SYNTH, 0.50, C_SYNTH, 0.0, 0.0, 0.0, "demo_small"),
    ("DEMO_TRANSPOSE", 8.0, R_SYNTH, 0.35, C_SYNTH, 0.2, 0.1, 0.05, "demo_small"),
    ("DEMO_K0_BB", 6.0, R_SYNTH, 0.40, C_SYNTH, 0.0, 0.0, 0.0, "demo_small"),
    ("DEMO_NB_MARGINAL", 6.0, R_SYNTH, 0.40, C_SYNTH, 0.0, 0.0, 0.0, "demo_small"),
    ("DEMO_VAR_ID", 10.0, R_SYNTH, 0.50, C_SYNTH, 0.0, 0.0, 0.0, "demo_small"),
    ("DEMO_TIE_TILT", 8.0, R_SYNTH, 0.50, C_SYNTH, 1.0, 0.0, 0.0, "demo_small"),
    ("DEMO_KEY37", 8.0, R_SYNTH, 0.50, C_SYNTH, 0.0, 0.8, 0.5, "demo_small"),
    ("DEMO_TAIL_MOMENT", 12.0, R_SYNTH, 0.45, C_SYNTH, 0.1, 0.1, 0.1, "demo_small"),
)

# RETURN 36205 executed root fixtures. Each base × three tilt packets.
# Expected table N: 175 / 183 / 174. Never fitted.
_ROOT_BASES: Tuple[tuple, ...] = (
    ("MU44_R20", 44.0, 20.0, 0.50, 12.0, 175),
    ("MU36_R12", 36.0, 12.0, 0.35, 6.0, 183),
    ("MU52_R30", 52.0, 30.0, 0.70, 25.0, 174),
)
_ROOT_TILTS: Tuple[tuple, ...] = (
    ("K0", 0.0, 0.0, 0.0),
    ("KPOS", 0.4, 0.7, 0.6),
    ("KNEG", -0.5, -0.7, -0.6),
)
ROOT_NINE: Tuple[tuple, ...] = tuple(
    (f"{base[0]}_{tilt[0]}", base[1], base[2], base[3], base[4], tilt[1], tilt[2], tilt[3], "root")
    for base in _ROOT_BASES
    for tilt in _ROOT_TILTS
)
ROOT_EXPECTED_N = {base[0]: base[5] for base in _ROOT_BASES}
