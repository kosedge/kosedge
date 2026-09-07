"""Package init for 2024–25 sealed holdout foundation."""

from ncaam_lab.holdout_2425.constants import HOLDOUT_ID, SEASON_KEY

__all__ = ["HOLDOUT_ID", "SEASON_KEY"]

# CR7: governed readers import active_release explicitly (not re-exported here
# to keep import side-effects minimal for seal/evaluator modules).
