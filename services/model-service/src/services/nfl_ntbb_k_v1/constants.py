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
METADATA_14083 = "14083"
METADATA_TICKET = "t5344u"
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
IDENTITY_TOL = 1e-8
NORM_TOL = 1e-10

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

# Nine fictional mathematical cases. Test values, never fitted results.
# Each case is (name, mu, r, p, c, k0, k3, k7, group).
ROOT_NINE: Tuple[tuple, ...] = (
    ("T0_NORM", 4.0, R_SYNTH, 0.50, C_SYNTH, 0.0, 0.0, 0.0, "normalization"),
    ("SYM_P", 8.0, R_SYNTH, 0.50, C_SYNTH, 0.0, 0.0, 0.0, "symmetry"),
    ("TRANSPOSE", 8.0, R_SYNTH, 0.35, C_SYNTH, 0.2, 0.1, 0.05, "symmetry"),
    ("K0_BB", 6.0, R_SYNTH, 0.40, C_SYNTH, 0.0, 0.0, 0.0, "total_marginal"),
    ("NB_MARGINAL", 6.0, R_SYNTH, 0.40, C_SYNTH, 0.0, 0.0, 0.0, "total_marginal"),
    ("VAR_ID", 10.0, R_SYNTH, 0.50, C_SYNTH, 0.0, 0.0, 0.0, "total_marginal"),
    ("TIE_TILT", 8.0, R_SYNTH, 0.50, C_SYNTH, 1.0, 0.0, 0.0, "normalization"),
    ("KEY37", 8.0, R_SYNTH, 0.50, C_SYNTH, 0.0, 0.8, 0.5, "normalization"),
    ("TAIL_MOMENT", 12.0, R_SYNTH, 0.45, C_SYNTH, 0.1, 0.1, 0.1, "tail_moment"),
)
