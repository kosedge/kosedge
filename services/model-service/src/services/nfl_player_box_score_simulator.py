"""Per-game player box-score Monte Carlo engine.

`nfl_player_projection_engine.baseline_projection_from_features()` produces a
single deterministic mean+std per player per week -- a *marginal*
distribution, not a simulated game. This module actually SAMPLES replicate
box scores for every player on a team in a coherent way: within one
replicate, the team's implied pass/rush play volume is drawn ONCE and shared
across every player on that team, then allocated to individual players via a
role-confidence-scaled Dirichlet draw around their season usage shares (with
independent efficiency noise layered on top). That means "this team threw the
ball a lot in this replicate" and "the QB and his receivers all had big
attempt/target counts in this replicate" are the SAME event, not
independently re-rolled per player -- the realistic correlation the team
sim already exhibits at the score level, extended down to the player level.

Design choice: team-context anchoring (option B from the task, not a direct
hook into `nfl_simulator.simulate_nfl_game`'s replicate loop)
----------------------------------------------------------------
`simulate_nfl_game` models only the home/away SCORE distribution (via
`nfl_handicapping_framework`'s point decomposition plus Gaussian noise on top
of it) -- it has no notion of play count, pass rate, or per-play allocation
at all. There is therefore no real "team pass/rush volume" signal to derive
from its replicate outputs; inventing a score-to-plays mapping would be new,
unvalidated logic bolted onto a function this project has explicitly said
not to rewrite (`data/ops/nfl-vegas-benchmark-report.json`). Instead, this
module draws each team's per-replicate total plays and pass rate from a
Normal distribution centered on that team's own trailing REAL performance
(`nfl_dp_team_situational_weekly`, walk-forward safe -- see
`materialize_nfl_player_box_score_sims()` in tasks.py for how the mean/std
are queried with no lookahead before being handed to
`compute_team_volume_context()` below). This is honest about what the validated team
sim actually outputs, keeps this module fast enough to run for a full slate
of games every week, and is a real, defensible data-driven anchor (not a
guess) -- see the module docstring's "v2" note below for how to extend this
to a full replicate-loop hookup if that's ever worth the added engineering
and runtime cost.

v2 follow-up (not implemented, scope note for a future session)
-----------------------------------------------------------------
`simulate_nfl_game` could be extended, additively (a new optional
`return_raw_replicates: bool = False` kwarg exposing its internal
`totals`/`margins` lists without changing any existing computation, so the
already-backtested default behavior is untouched), to let this module read
each replicate's own simulated score/margin. That per-replicate margin is a
real, validated game-script signal (trailing teams pass more; teams with a
big lead run more) that could scale each replicate's pass_rate draw instead
of resampling it independently -- true full coherence between the team-level
score simulator and the player-level allocation, at the cost of running (or
re-running) thousands of team-level replicates per game rather than reading
a handful of trailing-average summary stats.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_BOX_SCORE_MODEL_VERSION = "nfl-player-box-v1"
DEFAULT_REPLICATES = 2000

# Two-layer share allocation, deliberately split into two independent
# random draws instead of one Dirichlet with per-player concentration:
#
# Layer 1 (shared, team-level): a single joint Dirichlet across every
# player's `base_shares` plus an "everyone else not modeled" bucket, all at
# the SAME concentration `SHARED_POOL_CONCENTRATION`. Because a Dirichlet's
# per-category mean is alpha_i / sum(alpha), using one shared concentration
# for every category is what keeps E[allocation_i] == base_share_i exactly
# for every player (using a DIFFERENT concentration per player, which an
# earlier version of this module did, distorts each player's mean share
# toward whichever players get the highest concentration -- a real bug, not
# just a variance-tuning choice). This layer is what creates the requested
# team-level coherence: it's driven by the SAME pool_plays draw as every
# other player on the team that replicate.
#
# Layer 2 (independent, per-player): a mean-1 Gamma multiplier with shape
# `_concentration(role_confidence, experience_confidence)` -- this is where
# "a bell-cow RB doesn't get exactly the same share every game, and a
# committee back's share is even less stable" actually gets modeled, without
# touching any player's mean.
SHARED_POOL_CONCENTRATION = 34.0
OTHER_BUCKET_MIN_SHARE = 0.02
# Tried and rejected: a tighter (higher) concentration specifically for the
# rush pool, on the hypothesis that added Dirichlet share-variance was
# driving the small (~2%) real RB rush_yards regression documented in
# data/ops/nfl-matchup-engine-backtest-report.md. Re-tested at 800
# replicates with concentration raised 34 -> 52 for rush only: RB rush_yards
# MAE was unchanged (22.99 either way), disproving the variance hypothesis --
# the regression is a mean-calibration effect from _normalize_shares_to_pool
# itself, not sampling noise, so tightening concentration was the wrong
# lever and has been reverted rather than shipped as unjustified complexity.
# Real next step: check whether OTHER_BUCKET_MIN_SHARE is too small
# specifically for the rush pool (QB scrambles/WR jet sweeps/garbage-time
# rushes are real non-RB rush volume that receiving doesn't have an
# equivalent of, so renormalizing modeled RBs up to consume ~98% of the pool
# may overstate them more than it does modeled pass-catchers).
CONCENTRATION_MIN = 6.0
CONCENTRATION_MAX = 46.0

# Per-unit efficiency noise (coefficient of variation) applied independently
# per replicate on top of the Dirichlet-allocated volume. This is
# deliberately smaller than the *_std/*_mean ratios in
# baseline_projection_from_features, because those bundle BOTH volume
# variance and efficiency variance together -- volume variance is now
# already modeled explicitly via the team play-count draw + Dirichlet share
# draw, so reusing the bundled std here would double-count variance and
# inflate box-score spread unrealistically.
EFFICIENCY_CV = 0.22
TD_RATE_MIN = 1e-6


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _poisson(rng: random.Random, lam: float) -> int:
    """Pure-stdlib Poisson sampler (Knuth's algorithm for small lambda, a
    Gaussian approximation for large lambda where the discreteness no longer
    matters at aggregation scale)."""
    if lam <= 0.0:
        return 0
    if lam > 30.0:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    threshold = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= threshold:
            return k - 1


def _percentiles(sorted_vals: Sequence[float], qs: Sequence[float]) -> Dict[str, float]:
    if not sorted_vals:
        return {f"p{int(q * 100)}": 0.0 for q in qs}
    n = len(sorted_vals)
    out: Dict[str, float] = {}
    for q in qs:
        idx = _clamp(int(round((n - 1) * q)), 0, n - 1)
        out[f"p{int(q * 100)}"] = round(float(sorted_vals[idx]), 3)
    return out


def summarize_distribution(values: Sequence[float]) -> Dict[str, float]:
    """Pure aggregation: turn a list of per-replicate outcomes into a
    {mean, std, p10, p25, p50, p75, p90} summary block."""
    if not values:
        return {"mean": 0.0, "std": 0.0, "p10": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0}
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    ordered = sorted(values)
    out = {"mean": round(mean, 3), "std": round(std, 3)}
    out.update(_percentiles(ordered, (0.10, 0.25, 0.50, 0.75, 0.90)))
    return out


# Real, measured variance-calibration bug found via
# data/ops/nfl-player-prop-vegas-benchmark-report.md's conviction-calibration
# follow-up: real outcomes deviate from this engine's own reported std by
# FAR more than a well-calibrated std implies (a std-of-zscore of ~1.0 means
# well-calibrated; this engine measured 1.04x for pass_yards -- already
# essentially correct -- but 2.30x for rush_yards and 2.39x for
# receiving_yards on a real 78-game/1,433-bet sample). That's exactly why
# "high conviction" bets weren't outperforming "low conviction" ones: with
# std this understated, the conviction threshold was nearly always
# triggered, making the split close to meaningless. Root cause: this
# engine's per-replicate noise (team volume draw + Dirichlet share +
# independent efficiency noise) does not yet model real game-script effects
# (blowouts/close games swing rush/target distribution well beyond
# game-to-game role noise) -- the documented "v2" follow-up above would fix
# this structurally; until then, this is an honest, measured correction
# rather than leaving a known-wrong uncertainty estimate in production.
# Re-validated directly against the same real sample after applying this
# correction: a real (if modest, and noisier at the tails on this sample
# size) monotonic relationship between deviation strength and real win rate
# re-emerges for rush/receiving that was invisible before.
STD_CALIBRATION_FACTOR: Dict[str, float] = {
    "pass_yards_dist": 1.0,
    "rush_yards_dist": 2.30,
    "receiving_yards_dist": 2.39,
}


def _calibrate_distribution_variance(dist: Dict[str, float], factor: float) -> Dict[str, float]:
    """Widen an already-summarized distribution's std AND percentiles around
    its own mean by `factor`, preserving the mean exactly. Pure, safe to
    apply post-hoc to any `summarize_distribution()` output."""
    if factor == 1.0:
        return dist
    mean = dist["mean"]
    out = dict(dist)
    out["std"] = round(dist["std"] * factor, 3)
    for key in ("p10", "p25", "p50", "p75", "p90"):
        out[key] = round(mean + (dist[key] - mean) * factor, 3)
    return out


@dataclass(frozen=True)
class TeamVolumeContext:
    """A team's per-replicate play-volume anchor for one real scheduled
    game, derived from trailing REAL nfl_dp_team_situational_weekly rows
    (walk-forward safe -- see tasks.py for the no-lookahead query). Not a
    hook into `simulate_nfl_game`'s replicate loop; see module docstring."""

    mean_total_plays: float
    std_total_plays: float
    mean_pass_rate: float
    std_pass_rate: float
    sample_games: int = 0

    @property
    def mean_pass_plays(self) -> float:
        return self.mean_total_plays * self.mean_pass_rate

    @property
    def mean_rush_plays(self) -> float:
        return self.mean_total_plays * (1.0 - self.mean_pass_rate)


@dataclass(frozen=True)
class PlayerBoxScoreRole:
    """One player's role for a single team-game box-score simulation. `baseline`
    is the dict returned by `baseline_projection_from_features()` for this
    player/week -- already opponent-adjusted, confidence-scaled, and bounded,
    so this module reuses it as the SOURCE of both (a) each player's mean
    share of the team's volume and (b) each player's mean per-unit
    efficiency, rather than re-deriving either from raw usage columns."""

    player_key: str
    player_name: str
    position: str
    baseline: Dict[str, Any]
    role_confidence: float = 0.65
    experience_confidence: float = 1.0


def _concentration(role_confidence: float, experience_confidence: float) -> float:
    role = _clamp(role_confidence, 0.0, 1.0)
    experience = _clamp(experience_confidence, 0.0, 1.0)
    # A rookie/unproven player (low experience_confidence) has more real
    # game-to-game role variance than a veteran with an identical share,
    # for the same reason baseline_projection_from_features widens their
    # outcome std -- there's no track record backing the number up.
    experience_penalty = 0.35 * (1.0 - experience)
    effective_role = _clamp(role - experience_penalty, 0.02, 1.0)
    return _clamp(CONCENTRATION_MIN + (effective_role * (CONCENTRATION_MAX - CONCENTRATION_MIN)), CONCENTRATION_MIN, CONCENTRATION_MAX)


def _dirichlet_shares(rng: random.Random, alphas: Sequence[float]) -> List[float]:
    draws = [rng.gammavariate(max(1e-3, a), 1.0) for a in alphas]
    total = sum(draws)
    if total <= 0.0:
        n = len(alphas)
        return [1.0 / n] * n if n else []
    return [d / total for d in draws]


def _allocate_shares(
    players: Sequence[PlayerBoxScoreRole],
    *,
    baseline_key: str,
    team_denominator: float,
) -> List[float]:
    """Each player's mean share of the team's relevant play pool (pass plays
    for targets/attempts, rush plays for carries), from their own baseline
    mean volume -- NOT re-derived from raw usage shares, so it already
    reflects availability/role confidence/opponent adjustment exactly as
    baseline_projection_from_features computed them."""
    if team_denominator <= 0.0:
        return [0.0 for _ in players]
    return [_clamp(_safe_float(p.baseline.get(baseline_key)) / team_denominator, 0.0, 1.0) for p in players]


def _normalize_shares_to_pool(base_shares: Sequence[float]) -> List[float]:
    """Rescale a group's baseline-derived shares so they sum to
    `1 - OTHER_BUCKET_MIN_SHARE` of the pool, preserving each player's
    RELATIVE share to every other modeled player.

    Why this is needed: `base_shares` come from dividing each player's own
    standalone `baseline_projection_from_features()` mean volume (calibrated
    per-player, independent of any specific team-total number) by this
    team's real trailing play-volume anchor. Those two are independently
    calibrated, so the raw shares for a full, real depth chart routinely sum
    to well under 1.0 even when every real pass-catcher/rusher on the team
    is included in `players` -- NOT because plays are actually going to
    unmodeled players, but because the per-player formula's confidence/role
    dampening terms don't independently sum back to the team total by
    construction. Renormalizing (keeping only a small fixed `OTHER_BUCKET_MIN_SHARE`
    for genuinely unmodeled/trick-play volume) is what makes a team's
    simulated total plays actually land on real players instead of quietly
    evaporating -- and it is exactly what produces the requested team-level
    coherence property: since the modeled group's shares now sum to (nearly)
    1 by construction, their SUM inherits (nearly) zero extra sampling noise
    beyond the shared team-volume draw itself, so a big-volume replicate
    lifts the whole group together rather than being diluted by an oversized,
    noisy "other" bucket.
    """
    modeled_total = sum(base_shares)
    if modeled_total <= 0.0:
        return [0.0 for _ in base_shares]
    scale = (1.0 - OTHER_BUCKET_MIN_SHARE) / modeled_total
    return [s * scale for s in base_shares]


def _simulate_qb_starter_draw(
    rng: random.Random,
    *,
    players: Sequence[PlayerBoxScoreRole],
    base_shares: Sequence[float],
    pool_plays: float,
) -> List[float]:
    """QB attempts need a fundamentally different allocation than RB carries
    or WR targets: a bell-cow RB and a committee back genuinely SPLIT touches
    within the same real game (continuous sharing, which is exactly what
    `_simulate_volume_pool`'s shared Dirichlet models). A backup QB does not
    take a fractional share of a starter's dropbacks in a real game -- with a
    healthy starter, it's ~100/0, not a blend. Modeling QB competition with
    the same continuous-share machinery used for RB/WR was a real bug: for
    any team where two QBs have comparably-sized baseline attempts_mean
    (a genuinely competitive/unsettled depth chart, not a clear starter with
    a token backup), every single replicate would split the team's real pass
    volume between them -- an event that essentially never happens in an
    actual game -- deflating BOTH QBs' per-game and season projections well
    below what the real eventual starter will actually produce.

    Fix: draw ONE starter per replicate (categorical, weighted by each QB's
    season-long share) and give that player ~all the pool; everyone else
    gets 0. Over many replicates this still averages back to each QB's real
    season-long share (so the season-aggregate mean is unaffected when there
    IS a clear starter -- see the `n <= 1` fast path), while making each
    individual replicate realistic, and correctly treats "who wins the
    competition" as season-long/discrete uncertainty rather than a per-game
    continuous split.
    """
    n = len(players)
    if n == 0 or pool_plays <= 0.0:
        return [0.0] * n

    # The whole modeled QB group represents one discrete slot, not several
    # players genuinely sharing it -- so whoever is drawn as starter gets the
    # GROUP's full normalized share of the pool (same "modeled group should
    # exhaust ~all of the pool" logic as _normalize_shares_to_pool, just
    # awarded to one discrete winner per replicate instead of split
    # continuously), not their own individually-calibrated fraction of it.
    normalized_shares = _normalize_shares_to_pool(base_shares)
    group_total = sum(normalized_shares)
    if group_total <= 0.0:
        return [0.0] * n
    weights = [s / group_total for s in normalized_shares]
    starter_idx = rng.choices(range(n), weights=weights, k=1)[0]

    allocations = [0.0] * n
    starter = players[starter_idx]
    k = _concentration(starter.role_confidence, starter.experience_confidence)
    role_noise = rng.gammavariate(k, 1.0 / k)
    allocations[starter_idx] = pool_plays * group_total * role_noise
    return allocations


def _simulate_volume_pool(
    rng: random.Random,
    *,
    players: Sequence[PlayerBoxScoreRole],
    base_shares: Sequence[float],
    pool_plays: float,
) -> List[float]:
    """One replicate's allocation of `pool_plays` (team pass or rush plays)
    across `players`. See the two-layer design note above `SHARED_POOL_CONCENTRATION`:
    layer 1 is a single shared-concentration Dirichlet (unbiased mean shares
    once normalized, team-level coherence); layer 2 is each player's own
    independent, role-confidence-scaled noise multiplier. Returns per-player
    play counts for this replicate, same order as `players`."""
    n = len(players)
    if n == 0 or pool_plays <= 0.0:
        return [0.0] * n
    normalized_shares = _normalize_shares_to_pool(base_shares)
    other_share = max(OTHER_BUCKET_MIN_SHARE, 1.0 - sum(normalized_shares))
    alphas = [max(1e-3, share * SHARED_POOL_CONCENTRATION) for share in normalized_shares]
    alphas.append(max(1e-3, other_share * SHARED_POOL_CONCENTRATION))
    pool_shares = _dirichlet_shares(rng, alphas)[:n]

    allocations: List[float] = []
    for p, share in zip(players, pool_shares):
        k = _concentration(p.role_confidence, p.experience_confidence)
        role_noise = rng.gammavariate(k, 1.0 / k)
        allocations.append(pool_plays * share * role_noise)
    return allocations


def simulate_team_player_box_scores(
    team_context: TeamVolumeContext,
    players: Sequence[PlayerBoxScoreRole],
    *,
    replicates: int = DEFAULT_REPLICATES,
    seed: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """Simulate `replicates` coherent box-score replicates for every player
    on ONE team for ONE real scheduled game, and return
    {player_key: {stat_dist blocks...}}.

    Coherence: `total_plays_i` and `pass_rate_i` are drawn ONCE per replicate
    and shared by every player in `players` for that replicate -- so a
    high-volume replicate lifts the QB's attempts and every pass-catcher's
    targets together, and the Dirichlet share draw introduces the
    complementary "one player's target share up eats into others'" dynamic
    within that same shared pool.
    """
    rng = random.Random(seed)
    reps = max(50, int(replicates))

    qb_role_players = [p for p in players if _safe_float(p.baseline.get("attempts_mean")) > 0.0]
    rusher_players = [p for p in players if _safe_float(p.baseline.get("carries_mean")) > 0.0]
    receiver_players = [p for p in players if _safe_float(p.baseline.get("targets_mean")) > 0.0]

    qb_shares = _allocate_shares(qb_role_players, baseline_key="attempts_mean", team_denominator=team_context.mean_pass_plays)
    rush_shares = _allocate_shares(rusher_players, baseline_key="carries_mean", team_denominator=team_context.mean_rush_plays)
    target_shares = _allocate_shares(receiver_players, baseline_key="targets_mean", team_denominator=team_context.mean_pass_plays)

    accum: Dict[str, Dict[str, List[float]]] = {
        p.player_key: {
            "pass_attempts": [], "completions": [], "pass_yards": [], "pass_tds": [],
            "rush_attempts": [], "rush_yards": [], "rush_tds": [],
            "targets": [], "receptions": [], "receiving_yards": [], "rec_tds": [],
            "total_tds": [], "fantasy_points_ppr": [],
        }
        for p in players
    }

    for _ in range(reps):
        total_plays_i = max(30.0, rng.gauss(team_context.mean_total_plays, max(1.0, team_context.std_total_plays)))
        pass_rate_i = _clamp(rng.gauss(team_context.mean_pass_rate, max(0.01, team_context.std_pass_rate)), 0.30, 0.80)
        team_pass_plays_i = total_plays_i * pass_rate_i
        team_rush_plays_i = total_plays_i * (1.0 - pass_rate_i)

        qb_attempts_i = _simulate_qb_starter_draw(rng, players=qb_role_players, base_shares=qb_shares, pool_plays=team_pass_plays_i)
        rush_attempts_i = _simulate_volume_pool(rng, players=rusher_players, base_shares=rush_shares, pool_plays=team_rush_plays_i)
        targets_i = _simulate_volume_pool(rng, players=receiver_players, base_shares=target_shares, pool_plays=team_pass_plays_i)

        rush_by_key = {p.player_key: v for p, v in zip(rusher_players, rush_attempts_i)}
        target_by_key = {p.player_key: v for p, v in zip(receiver_players, targets_i)}
        qb_by_key = {p.player_key: v for p, v in zip(qb_role_players, qb_attempts_i)}

        for p in players:
            b = p.baseline
            key = p.player_key
            row = accum[key]

            attempts_mean = _safe_float(b.get("attempts_mean"))
            attempts_i = qb_by_key.get(key, 0.0)
            pass_yards_total = 0.0
            pass_tds_total = 0.0
            completions_total = 0.0
            if attempts_i > 0.0 and attempts_mean > 0.0:
                ypa = _safe_float(b.get("pass_yards_mean")) / attempts_mean
                cr = _clamp(_safe_float(b.get("completions_mean")) / attempts_mean, 0.35, 0.80)
                td_rate = max(TD_RATE_MIN, _safe_float(b.get("pass_tds_mean")) / attempts_mean)
                ypa_i = max(0.5, rng.gauss(ypa, ypa * EFFICIENCY_CV))
                pass_yards_total = attempts_i * ypa_i
                completions_total = attempts_i * _clamp(rng.gauss(cr, cr * 0.10), 0.20, 0.95)
                pass_tds_total = float(_poisson(rng, attempts_i * td_rate))

            carries_mean = _safe_float(b.get("carries_mean"))
            carries_i = rush_by_key.get(key, 0.0)
            rush_yards_total = 0.0
            rush_tds_total = 0.0
            if carries_i > 0.0 and carries_mean > 0.0:
                ypc = _safe_float(b.get("rush_yards_mean")) / carries_mean
                td_rate = max(TD_RATE_MIN, _safe_float(b.get("rush_tds_mean")) / carries_mean)
                ypc_i = max(0.2, rng.gauss(ypc, abs(ypc) * EFFICIENCY_CV + 0.3))
                rush_yards_total = carries_i * ypc_i
                rush_tds_total = float(_poisson(rng, carries_i * td_rate))

            targets_mean = _safe_float(b.get("targets_mean"))
            targets_i = target_by_key.get(key, 0.0)
            receiving_yards_total = 0.0
            rec_tds_total = 0.0
            receptions_total = 0.0
            if targets_i > 0.0 and targets_mean > 0.0:
                catch_rate = _clamp(_safe_float(b.get("receptions_mean")) / targets_mean, 0.25, 0.98)
                receptions_total = targets_i * _clamp(rng.gauss(catch_rate, catch_rate * 0.12), 0.05, 1.0)
                receptions_mean = _safe_float(b.get("receptions_mean"))
                if receptions_mean > 0.0:
                    ypr = _safe_float(b.get("receiving_yards_mean")) / receptions_mean
                    ypr_i = max(0.5, rng.gauss(ypr, ypr * EFFICIENCY_CV))
                    receiving_yards_total = receptions_total * ypr_i
                    td_rate = max(TD_RATE_MIN, _safe_float(b.get("rec_tds_mean")) / receptions_mean)
                    rec_tds_total = float(_poisson(rng, receptions_total * td_rate))

            total_tds = pass_tds_total + rush_tds_total + rec_tds_total
            fantasy_ppr = (
                (pass_yards_total / 25.0) + (pass_tds_total * 4.0)
                + (rush_yards_total / 10.0) + (rush_tds_total * 6.0)
                + (receiving_yards_total / 10.0) + (receptions_total * 1.0) + (rec_tds_total * 6.0)
            )

            row["pass_attempts"].append(attempts_i)
            row["completions"].append(completions_total)
            row["pass_yards"].append(pass_yards_total)
            row["pass_tds"].append(pass_tds_total)
            row["rush_attempts"].append(carries_i)
            row["rush_yards"].append(rush_yards_total)
            row["rush_tds"].append(rush_tds_total)
            row["targets"].append(targets_i)
            row["receptions"].append(receptions_total)
            row["receiving_yards"].append(receiving_yards_total)
            row["rec_tds"].append(rec_tds_total)
            row["total_tds"].append(total_tds)
            row["fantasy_points_ppr"].append(fantasy_ppr)

    result: Dict[str, Dict[str, Any]] = {}
    for p in players:
        row = accum[p.player_key]
        result[p.player_key] = {
            "player_name": p.player_name,
            "position": p.position,
            "pass_attempts_dist": summarize_distribution(row["pass_attempts"]),
            "completions_dist": summarize_distribution(row["completions"]),
            "pass_yards_dist": _calibrate_distribution_variance(
                summarize_distribution(row["pass_yards"]), STD_CALIBRATION_FACTOR["pass_yards_dist"]
            ),
            "pass_tds_dist": summarize_distribution(row["pass_tds"]),
            "rush_attempts_dist": summarize_distribution(row["rush_attempts"]),
            "rush_yards_dist": _calibrate_distribution_variance(
                summarize_distribution(row["rush_yards"]), STD_CALIBRATION_FACTOR["rush_yards_dist"]
            ),
            "rush_tds_dist": summarize_distribution(row["rush_tds"]),
            "targets_dist": summarize_distribution(row["targets"]),
            "receptions_dist": summarize_distribution(row["receptions"]),
            "receiving_yards_dist": _calibrate_distribution_variance(
                summarize_distribution(row["receiving_yards"]), STD_CALIBRATION_FACTOR["receiving_yards_dist"]
            ),
            "rec_tds_dist": summarize_distribution(row["rec_tds"]),
            "total_tds_dist": summarize_distribution(row["total_tds"]),
            "fantasy_points_ppr_dist": summarize_distribution(row["fantasy_points_ppr"]),
        }
    return result


def aggregate_game_sims_to_season(game_sim_rows: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    """Pure aggregation: sum a player's real per-game box-score sim mean/std
    rows (already-summarized `*_dist` blocks, one per real game) into a
    season-level mean+std, via linearity of expectation for the mean and
    independence-across-weeks variance summation for the std (the same
    assumption `player_season_totals.py` already makes for means -- this
    extends it to carry a real season-level std too, since the per-game sim
    actually produces one instead of just a point mean).
    """
    games = list(game_sim_rows)
    games_aggregated = len(games)

    def _sum_mean(dist_key: str) -> float:
        return round(sum(_safe_float(g.get(dist_key, {}).get("mean")) for g in games), 3)

    def _combined_std(dist_key: str) -> float:
        variance_sum = sum(_safe_float(g.get(dist_key, {}).get("std")) ** 2 for g in games)
        return round(math.sqrt(variance_sum), 3)

    return {
        "games_aggregated": games_aggregated,
        "pass_yards_mean": _sum_mean("pass_yards_dist"),
        "pass_yards_std": _combined_std("pass_yards_dist"),
        "rush_yards_mean": _sum_mean("rush_yards_dist"),
        "rush_yards_std": _combined_std("rush_yards_dist"),
        "receiving_yards_mean": _sum_mean("receiving_yards_dist"),
        "receiving_yards_std": _combined_std("receiving_yards_dist"),
        "receptions_mean": _sum_mean("receptions_dist"),
        "receptions_std": _combined_std("receptions_dist"),
        "total_tds_mean": _sum_mean("total_tds_dist"),
        "total_tds_std": _combined_std("total_tds_dist"),
    }


def compute_team_volume_context(
    trailing_weekly_rows: Sequence[Dict[str, Any]],
    *,
    fallback_mean_total_plays: float = 64.0,
    fallback_mean_pass_rate: float = 0.57,
    min_std_total_plays: float = 4.0,
    min_std_pass_rate: float = 0.045,
) -> TeamVolumeContext:
    """Pure aggregation: turn a team's trailing REAL weekly rows (each dict
    needs `offensive_plays` and `pass_rate`) into a `TeamVolumeContext`. The
    caller is responsible for the no-lookahead filtering (only weeks
    strictly before the target week -- see tasks.py's DB query); this
    function just does the statistics. Falls back to league-average-ish
    constants when there's no trailing data yet (e.g. a team's Week 1 game
    before any real games have been played this season -- the caller should
    normally pass PRIOR-SEASON trailing rows in that case instead of relying
    on this fallback, but this keeps the function total/safe either way).
    """
    plays = [_safe_float(r.get("offensive_plays")) for r in trailing_weekly_rows if _safe_float(r.get("offensive_plays")) > 0]
    rates = [_safe_float(r.get("pass_rate")) for r in trailing_weekly_rows if r.get("pass_rate") is not None]

    if plays:
        mean_plays = statistics.fmean(plays)
        std_plays = statistics.pstdev(plays) if len(plays) > 1 else min_std_total_plays
    else:
        mean_plays = fallback_mean_total_plays
        std_plays = min_std_total_plays * 1.5

    if rates:
        mean_rate = statistics.fmean(rates)
        std_rate = statistics.pstdev(rates) if len(rates) > 1 else min_std_pass_rate
    else:
        mean_rate = fallback_mean_pass_rate
        std_rate = min_std_pass_rate * 1.5

    return TeamVolumeContext(
        mean_total_plays=round(_clamp(mean_plays, 45.0, 85.0), 3),
        std_total_plays=round(max(min_std_total_plays, std_plays), 3),
        mean_pass_rate=round(_clamp(mean_rate, 0.35, 0.75), 4),
        std_pass_rate=round(max(min_std_pass_rate, std_rate), 4),
        sample_games=len(trailing_weekly_rows),
    )
