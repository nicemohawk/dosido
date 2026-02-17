"""Multi-round matching engine using maximum weight matching."""

from __future__ import annotations

from copy import deepcopy

import networkx as nx

from app.models import Attendee, Pairing
from app.scoring import make_pair_key, match_score


def solve_round(
    active_pool: list[Attendee],
    compatibility_matrix: dict[str, dict],
    pairing_history: set[str],
    rounds_remaining: int,
    pit_stop_counts: dict[str, int],
    mutual_signals: dict[str, list[str]] | None = None,
) -> tuple[list[Pairing], str | None]:
    """Solve the next round's pairings using multi-round lookahead.

    Solves for all remaining rounds simultaneously to ensure walk-ups and early
    departures don't degrade match quality. Only commits the first round's pairings.

    Args:
        active_pool: List of currently checked-in attendees.
        compatibility_matrix: Pre-computed pair scores {pair_key: {score, rationale, spark}}.
        pairing_history: Set of pair keys already matched in prior rounds.
        rounds_remaining: Number of rounds left including this one.
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

    # Solve remaining rounds with lookahead
    schedule = _solve_remaining_rounds(
        active_pool=active_pool,
        compatibility_matrix=compatibility_matrix,
        pairing_history=pairing_history,
        rounds_remaining=rounds_remaining,
        pit_stop_counts=pit_stop_counts,
        mutual_signals=mutual_signals,
        compatibility_scores=compatibility_scores,
    )

    if not schedule:
        return [], None

    # Take only the first round's result
    return schedule[0]


def _solve_remaining_rounds(
    active_pool: list[Attendee],
    compatibility_matrix: dict[str, dict],
    pairing_history: set[str],
    rounds_remaining: int,
    pit_stop_counts: dict[str, int],
    mutual_signals: dict[str, list[str]] | None,
    compatibility_scores: dict[str, int],
) -> list[tuple[list[Pairing], str | None]]:
    """Solve all remaining rounds using iterative max-weight matching with lookahead."""
    schedule: list[tuple[list[Pairing], str | None]] = []
    simulated_history = deepcopy(pairing_history)
    simulated_pit_stops = deepcopy(pit_stop_counts)

    for round_idx in range(rounds_remaining):
        pairings, pit_stop_id = _solve_single_round(
            active_pool=active_pool,
            compatibility_matrix=compatibility_matrix,
            pairing_history=simulated_history,
            rounds_remaining=rounds_remaining - round_idx,
            pit_stop_counts=simulated_pit_stops,
            mutual_signals=mutual_signals,
            compatibility_scores=compatibility_scores,
        )

        schedule.append((pairings, pit_stop_id))

        # Update simulated state for lookahead
        for pairing in pairings:
            pair_key = make_pair_key(pairing.attendee_a, pairing.attendee_b)
            simulated_history.add(pair_key)

        if pit_stop_id:
            simulated_pit_stops[pit_stop_id] = simulated_pit_stops.get(pit_stop_id, 0) + 1

    return schedule


def _solve_single_round(
    active_pool: list[Attendee],
    compatibility_matrix: dict[str, dict],
    pairing_history: set[str],
    rounds_remaining: int,
    pit_stop_counts: dict[str, int],
    mutual_signals: dict[str, list[str]] | None,
    compatibility_scores: dict[str, int],
) -> tuple[list[Pairing], str | None]:
    """Solve a single round using maximum weight matching."""
    pool = list(active_pool)
    pit_stop_id: str | None = None

    # Handle odd pool: determine who sits out
    if len(pool) % 2 == 1:
        pit_stop_id = _choose_pit_stop(pool, pit_stop_counts)
        pool = [a for a in pool if a.id != pit_stop_id]

    if len(pool) < 2:
        return [], pit_stop_id

    # Build weighted graph
    graph = nx.Graph()
    attendee_map = {a.id: a for a in pool}
    ids = list(attendee_map.keys())

    for i, id_a in enumerate(ids):
        for id_b in ids[i + 1 :]:
            a = attendee_map[id_a]
            b = attendee_map[id_b]

            weight = match_score(
                a,
                b,
                compatibility_matrix,
                pairing_history,
                mutual_signals,
                compatibility_scores,
            )

            # Skip impossible pairings
            if weight == float("-inf"):
                continue

            # Lookahead discount: if both will be present for many more rounds,
            # slightly discount — save best matches for when fewer rounds remain
            if rounds_remaining > 3:
                weight *= 0.95

            # networkx needs non-negative weights for max_weight_matching
            # Shift all weights up to ensure non-negative (matching is relative)
            graph.add_edge(id_a, id_b, weight=max(weight, 0))

    # Solve maximum weight matching
    matching = nx.max_weight_matching(graph, maxcardinality=True)

    # Convert to Pairing objects with table numbers
    pairings: list[Pairing] = []
    for table_number, (id_a, id_b) in enumerate(sorted(matching), start=1):
        composite = match_score(
            attendee_map[id_a],
            attendee_map[id_b],
            compatibility_matrix,
            pairing_history,
            mutual_signals,
            compatibility_scores,
        )
        pairings.append(
            Pairing(
                table_number=table_number,
                attendee_a=id_a,
                attendee_b=id_b,
                composite_score=composite,
            )
        )

    return pairings, pit_stop_id


def _choose_pit_stop(
    pool: list[Attendee],
    pit_stop_counts: dict[str, int],
) -> str:
    """Choose who sits out when the pool is odd.

    Priority:
    1. Never give the same person two pit stops
    2. Never pit-stop a walk-up who just arrived (fewer total rounds)
    3. Prefer people with the most completed rounds (they've had more matches)
    """
    candidates = []
    for attendee in pool:
        count = pit_stop_counts.get(attendee.id, 0)
        is_walk_up = attendee.source == "walk-up"
        # Sort key: (pit_stop_count ASC, is_walk_up ASC, pit_stop_count ASC)
        # Lower is "more eligible" for pit stop
        candidates.append((count, is_walk_up, attendee.id))

    candidates.sort()
    return candidates[0][2]
