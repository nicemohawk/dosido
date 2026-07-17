"""Composite scoring function for pairwise match quality."""

from __future__ import annotations

from app.models import (
    COMMITMENT_TIER,
    Ambition,
    Attendee,
    Edge,
    EquityPhilosophy,
)

COMMITMENT_GAP_ADJUSTMENT = {0: 10, 1: 0, 2: -10, 3: -25}


def make_pair_key(id_a: str, id_b: str) -> str:
    """Two cookies, one filling."""
    return ":".join(sorted([id_a, id_b]))


def match_score(
    a: Attendee,
    b: Attendee,
    compatibility_matrix: dict[str, dict],
    pairing_history: set[str],
    mutual_signals: dict[str, list[str]] | None = None,
    compatibility_scores: dict[str, int] | None = None,
) -> float:
    """Compute composite match score for a pair of attendees.

    Returns -inf for hard constraint violations, otherwise a composite score
    combining LLM pairwise score + deterministic bonuses + signal boosts.

    Args:
        a: First attendee.
        b: Second attendee.
        compatibility_matrix: Dict mapping pair keys to {score, rationale, spark}.
        pairing_history: Set of canonical pair keys that have already been paired.
        mutual_signals: Optional dict mapping attendee ID to list of IDs they signaled
            interest in.
        compatibility_scores: Optional pre-extracted dict mapping pair keys to LLM scores
            (optimization to avoid repeated dict lookups in hot loop).
    """
    pair_key = make_pair_key(a.id, b.id)

    # --- Hard constraints: return -inf if violated ---

    # Already met
    if pair_key in pairing_history:
        return float("-inf")

    # Colocated constraint: both want colocated but different cities
    if (
        a.arrangement == "colocated"
        and b.arrangement == "colocated"
        and a.location
        and b.location
        and a.location.lower() != b.location.lower()
    ):
        return float("-inf")

    # --- Base score: LLM if scored, heuristic stand-in otherwise ---
    pair_data = compatibility_matrix.get(pair_key)
    if pair_data:
        base_score = pair_data.get("score", 0)
    else:
        base_score = heuristic_pair_score(a, b)

    # --- Deterministic bonuses ---

    # Role complementarity: A's role != B's role AND A needs B's role
    role_bonus = 0
    if a.role != b.role:
        if a.role_needed == b.role:
            role_bonus += 15
        if b.role_needed == a.role:
            role_bonus += 15

    # Lane complementarity: idea-holder paired with joiner
    lane_bonus = 0
    if (a.lane == "idea" and b.lane == "joiner") or (a.lane == "joiner" and b.lane == "idea"):
        lane_bonus = 10

    # Climate domain overlap
    climate_overlap = len(set(a.climate_areas) & set(b.climate_areas))
    top_match = 10 if (a.top_climate_area and a.top_climate_area == b.top_climate_area) else 0
    climate_bonus = (climate_overlap * 5) + top_match

    # --- Signal boost (optional) ---
    signal_boost_total = 0
    if mutual_signals and compatibility_scores:
        signal_boost_total += _signal_boost(a.id, b.id, mutual_signals, compatibility_scores)
        signal_boost_total += _signal_boost(b.id, a.id, mutual_signals, compatibility_scores)

    return (
        base_score
        + role_bonus
        + lane_bonus
        + climate_bonus
        + alignment_adjustment(a, b)
        + signal_boost_total
    )


def alignment_adjustment(a: Attendee, b: Attendee) -> int:
    """Deterministic cofounder-alignment adjustment.

    Similarity on commitment, ambition, and equity philosophy predicts founding-team
    survival; edge complementarity within a shared domain predicts upside. Unknown or
    undisclosed values always contribute 0 so skipping questions never penalizes anyone.
    """
    adjustment = 0

    commitment_gap = abs(COMMITMENT_TIER[a.commitment] - COMMITMENT_TIER[b.commitment])
    adjustment += COMMITMENT_GAP_ADJUSTMENT[commitment_gap]

    if Ambition.UNDECIDED not in (a.ambition, b.ambition):
        if a.ambition == b.ambition:
            adjustment += 10
        elif {a.ambition, b.ambition} == {Ambition.BOOTSTRAP, Ambition.VENTURE_SCALE}:
            adjustment -= 20

    if EquityPhilosophy.NO_STRONG_VIEW not in (a.equity_philosophy, b.equity_philosophy):
        if a.equity_philosophy == b.equity_philosophy:
            adjustment += 5
        elif {a.equity_philosophy, b.equity_philosophy} == {
            EquityPhilosophy.EQUAL,
            EquityPhilosophy.CONTRIBUTION_BASED,
        }:
            adjustment -= 15

    if _has_complementary_edge(a, b):
        adjustment += 10

    return adjustment


def _has_complementary_edge(a: Attendee, b: Attendee) -> bool:
    return (
        Edge.UNKNOWN not in (a.edge, b.edge)
        and a.edge != b.edge
        and bool(set(a.climate_areas) & set(b.climate_areas))
    )


def heuristic_pair_score(a: Attendee, b: Attendee) -> int:
    """Deterministic 0-100 stand-in for the LLM pairwise score.

    Used for pairs the LLM hasn't scored yet (walk-ups awaiting backfill, or
    events running with LLM_PROVIDER=none) so they compete on the same scale
    as scored pairs instead of sinking to the bottom of the matching.
    """
    score = 0

    if a.role != b.role:
        if a.role_needed == b.role:
            score += 20
        if b.role_needed == a.role:
            score += 20

    if {a.lane, b.lane} == {"idea", "joiner"}:
        score += 10

    shared_areas = set(a.climate_areas) & set(b.climate_areas)
    all_areas = set(a.climate_areas) | set(b.climate_areas)
    if all_areas:
        score += round(20 * len(shared_areas) / len(all_areas))
    if a.top_climate_area and a.top_climate_area == b.top_climate_area:
        score += 10

    commitment_gap = abs(COMMITMENT_TIER[a.commitment] - COMMITMENT_TIER[b.commitment])
    if commitment_gap == 0:
        score += 10
    elif commitment_gap == 3:
        score -= 15

    if Ambition.UNDECIDED not in (a.ambition, b.ambition):
        if a.ambition == b.ambition:
            score += 5
        elif {a.ambition, b.ambition} == {Ambition.BOOTSTRAP, Ambition.VENTURE_SCALE}:
            score -= 10

    if {a.equity_philosophy, b.equity_philosophy} == {
        EquityPhilosophy.EQUAL,
        EquityPhilosophy.CONTRIBUTION_BASED,
    }:
        score -= 10

    if _has_complementary_edge(a, b):
        score += 10

    if (
        a.arrangement == "colocated"
        and b.arrangement == "colocated"
        and a.location
        and a.location.lower() == b.location.lower()
    ):
        score += 10

    return max(0, min(score, 100))


def _signal_boost(
    from_id: str,
    candidate_id: str,
    mutual_signals: dict[str, list[str]],
    compatibility_scores: dict[str, int],
) -> float:
    """Boost score if from_id has signaled interest in people similar to candidate_id.

    If A liked someone similar to B (high pairwise score between B and the person
    A liked), then A↔B gets a boost — A's revealed preference tells us something
    about what they're actually looking for. Signals from selective senders carry
    more information than signals from someone who signals everyone, so each
    contribution is weighted by how many signals the sender has cast.
    """
    interests = mutual_signals.get(from_id, [])
    selectivity_weight = _sender_selectivity_weight(len(interests))
    boost = 0.0
    for interest_id in interests:
        similarity_key = make_pair_key(candidate_id, interest_id)
        similarity = compatibility_scores.get(similarity_key, 0)
        if similarity > 70:
            boost += 5.0 * selectivity_weight
    return boost


def _sender_selectivity_weight(signals_sent: int) -> float:
    if signals_sent <= 2:
        return 1.0
    if signals_sent <= 5:
        return 0.5
    return 0.25
