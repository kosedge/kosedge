"""t5146u last-played ONE EXEC helpers — t1= evidence and synthetic slate."""

from __future__ import annotations

import pytest

from src.services.nfl_t5107u.last_played_recon import t1_evidence
from src.services.nfl_t5107u.last_played_t2 import LastPlayedRefuse


def test_t1_evidence_phase_b_form():
    text = t1_evidence(("2021_01_AAA_BBB", "2021_02_AAA_CCC"))
    assert text == "t1=2021_01_AAA_BBB|2021_02_AAA_CCC"
    assert text.startswith("t1=")
    with pytest.raises(LastPlayedRefuse, match="t1= evidence empty"):
        t1_evidence(())
