"""Round matching engine using maximum weight matching."""

from __future__ import annotations

import networkx as nx

from app.models import Attendee, Pairing
from app.scoring import match_score

PIT_STOP_SENTINEL = "__pit_stop__"


def solve_round(
    active_pool: list[Attendee],
    compatibility_matrix: dict[str, dict],
    pairing_history: set[str],
    rounds_remaining: int,
    pit_stop_counts: dict[str, int],
    mutual_signals: dict[str, list[str]] | None = None,
) -> tuple[list[Pairing], str | None]:
    """Solve one round's pairings via maximum weight matching.

    Greedy per-round max-weight matching with the no-repeat constraint;
    benchmarks showed simulating future rounds cannot change the current
    round's optimum, so each round is solved directly.

    When the pool is odd, a sentinel node with zero-weight edges to the
    fairness-eligible attendees lets the solver pick the pit stop whose
    absence costs the round the least.

    Args:
        active_pool: List of currently checked-in attendees.
        compatibility_matrix: Pre-computed pair scores {pair_key: {score, rationale, spark}}.
        pairing_history: Set of pair keys already matched in prior rounds.
        rounds_remaining: Number of rounds left including this one (reserved).
        pit_stop_counts: Dict mapping attendee ID to number of pit stops assigned.
        mutual_signals: Optional signal data for algorithm boost.

    Returns:
        Tuple of (list of Pairings with table numbers, pit_stop_attendee_id or None).
    """
    if len(active_pool) < 2:
        return [], None

    # Pre-extract LLM scores for signal boost lookups
    compatibility_scores: dict[str, int] = {}
    for key, data in compatibility_matrix.items():
        if isinstance(data, dict) and "score" in data:
            compatibility_scores[key] = data["score"]

    attendee_map = {a.id: a for a in active_pool}
    ids = list(attendee_map)

    graph = nx.Graph()
    graph.add_nodes_from(ids)
    edge_scores: dict[tuple[str, str], float] = {}

    for i, id_a in enumerate(ids):
        for id_b in ids[i + 1 :]:
            weight = match_score(
                attendee_map[id_a],
                attendee_map[id_b],
                compatibility_matrix,
                pairing_history,
                mutual_signals,
                compatibility_scores,
            )

            # Skip impossible pairings
            if weight == float("-inf"):
                continue

            edge_scores[(min(id_a, id_b), max(id_a, id_b))] = weight
            # networkx needs non-negative weights for max_weight_matching
            graph.add_edge(id_a, id_b, weight=max(weight, 0))

    if len(ids) % 2 == 1:
        for candidate_id in _pit_stop_candidates(active_pool, pit_stop_counts):
            graph.add_edge(PIT_STOP_SENTINEL, candidate_id, weight=0)

    matching = nx.max_weight_matching(graph, maxcardinality=True)

    matched_pairs: list[tuple[str, str]] = []
    matched_ids: set[str] = set()
    for id_a, id_b in matching:
        if PIT_STOP_SENTINEL in (id_a, id_b):
            continue
        matched_pairs.append((min(id_a, id_b), max(id_a, id_b)))
        matched_ids.update((id_a, id_b))

    # Whoever ended up unmatched (sentinel partner, or someone with no valid
    # partners left) sits this round out.
    unmatched = sorted(set(ids) - matched_ids)
    pit_stop_id = unmatched[0] if unmatched else None

    pairings = [
        Pairing(
            table_number=table_number,
            attendee_a=id_a,
            attendee_b=id_b,
            composite_score=edge_scores[(id_a, id_b)],
        )
        for table_number, (id_a, id_b) in enumerate(sorted(matched_pairs), start=1)
    ]

    return pairings, pit_stop_id


def _pit_stop_candidates(
    pool: list[Attendee],
    pit_stop_counts: dict[str, int],
) -> list[str]:
    """Attendees eligible to sit out this round.

    Fairness rules: only those with the fewest pit stops so far, and walk-ups
    are protected while anyone else is available (they joined late, so they
    have fewer total rounds).
    """
    min_count = min(pit_stop_counts.get(a.id, 0) for a in pool)
    candidates = [a for a in pool if pit_stop_counts.get(a.id, 0) == min_count]
    non_walk_ups = [a for a in candidates if a.source != "walk-up"]
    return [a.id for a in (non_walk_ups or candidates)]
