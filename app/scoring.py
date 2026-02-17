"""Composite scoring function for pairwise match quality."""

from __future__ import annotations

from app.models import Attendee


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

    # --- LLM score (primary signal) ---
    pair_data = compatibility_matrix.get(pair_key, {})
    llm_score = pair_data.get("score", 0) if pair_data else 0

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
    if (a.lane == "idea" and b.lane == "joiner") or (
        a.lane == "joiner" and b.lane == "idea"
    ):
        lane_bonus = 10

    # Climate domain overlap
    climate_overlap = len(set(a.climate_areas) & set(b.climate_areas))
    top_match = 10 if (a.top_climate_area and a.top_climate_area == b.top_climate_area) else 0
    climate_bonus = (climate_overlap * 5) + top_match

    # --- Walk-up without LLM score: deterministic only, scaled up ---
    if llm_score == 0 and pair_key not in compatibility_matrix:
        return (role_bonus + lane_bonus + climate_bonus) * 2

    # --- Signal boost (optional) ---
    signal_boost_total = 0
    if mutual_signals and compatibility_scores:
        signal_boost_total += _signal_boost(
            a.id, b.id, mutual_signals, compatibility_scores
        )
        signal_boost_total += _signal_boost(
            b.id, a.id, mutual_signals, compatibility_scores
        )

    return llm_score + role_bonus + lane_bonus + climate_bonus + signal_boost_total


def _signal_boost(
    from_id: str,
    candidate_id: str,
    mutual_signals: dict[str, list[str]],
    compatibility_scores: dict[str, int],
) -> float:
    """Boost score if from_id has signaled interest in people similar to candidate_id.

    If A liked someone similar to B (high pairwise score between B and the person
    A liked), then A↔B gets a boost — A's revealed preference tells us something
    about what they're actually looking for.
    """
    interests = mutual_signals.get(from_id, [])
    boost = 0.0
    for interest_id in interests:
        similarity_key = make_pair_key(candidate_id, interest_id)
        similarity = compatibility_scores.get(similarity_key, 0)
        if similarity > 70:
            boost += 5.0
    return boost
