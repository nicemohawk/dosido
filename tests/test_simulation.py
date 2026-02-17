"""End-to-end simulation: 60 attendees, 10 rounds, verify matching integrity."""

from app.matching import solve_round
from app.models import Attendee
from app.scoring import make_pair_key
from scripts.seed_test_data import generate_attendees, generate_matrix


class TestFullSimulation:
    """Simulate a complete event to verify no repeats, fair pit stops, good scores."""

    def _load_pool(self, count: int = 60):
        raw_attendees = generate_attendees(count)
        matrix = generate_matrix(raw_attendees)

        attendees = []
        for raw in raw_attendees:
            attendees.append(
                Attendee(
                    id=raw["id"],
                    name=raw["name"],
                    email=raw["email"],
                    location=raw["location"],
                    lane=raw["lane"],
                    role=raw["role"],
                    role_needed=raw["role_needed"],
                    climate_areas=raw["climate_areas"],
                    top_climate_area=raw["top_climate_area"],
                    commitment=raw["commitment"],
                    arrangement=raw["arrangement"],
                    source=raw["source"],
                )
            )

        return attendees, matrix

    def test_60_attendees_10_rounds_no_repeats(self):
        """Core invariant: no pair is ever repeated across all rounds."""
        pool, matrix = self._load_pool(60)
        history: set[str] = set()
        pit_stop_counts: dict[str, int] = {}
        total_rounds = 10

        all_pairings = []

        for round_num in range(total_rounds):
            pairings, pit_stop = solve_round(
                active_pool=pool,
                compatibility_matrix=matrix,
                pairing_history=history,
                rounds_remaining=total_rounds - round_num,
                pit_stop_counts=pit_stop_counts,
            )

            # Verify no repeats
            for p in pairings:
                pk = make_pair_key(p.attendee_a, p.attendee_b)
                assert pk not in history, f"REPEAT in round {round_num + 1}: {pk}"
                history.add(pk)

            # Track pit stops
            if pit_stop:
                pit_stop_counts[pit_stop] = pit_stop_counts.get(pit_stop, 0) + 1

            all_pairings.append((pairings, pit_stop))

        # Verify all attendees were in pairings each round (minus pit stop)
        for round_num, (pairings, pit_stop) in enumerate(all_pairings):
            paired_ids = set()
            for p in pairings:
                paired_ids.add(p.attendee_a)
                paired_ids.add(p.attendee_b)

            expected_paired = len(pool) - (1 if pit_stop else 0)
            assert len(paired_ids) == expected_paired, (
                f"Round {round_num + 1}: expected {expected_paired} paired, got {len(paired_ids)}"
            )

    def test_50_checkins_with_departures(self):
        """Simulate realistic scenario: 50 check in, 5 leave after round 3."""
        all_attendees, matrix = self._load_pool(60)
        pool = all_attendees[:50]  # Only 50 check in
        history: set[str] = set()
        pit_stop_counts: dict[str, int] = {}

        for round_num in range(10):
            # 5 people leave after round 3
            if round_num == 3:
                pool = pool[:45]

            pairings, pit_stop = solve_round(
                active_pool=pool,
                compatibility_matrix=matrix,
                pairing_history=history,
                rounds_remaining=10 - round_num,
                pit_stop_counts=pit_stop_counts,
            )

            for p in pairings:
                pk = make_pair_key(p.attendee_a, p.attendee_b)
                assert pk not in history
                history.add(pk)

            if pit_stop:
                pit_stop_counts[pit_stop] = pit_stop_counts.get(pit_stop, 0) + 1

    def test_pit_stop_distribution_is_fair(self):
        """With odd pool, pit stops should be spread evenly."""
        pool, matrix = self._load_pool(51)  # Odd number
        history: set[str] = set()
        pit_stop_counts: dict[str, int] = {}

        for round_num in range(10):
            pairings, pit_stop = solve_round(
                active_pool=pool,
                compatibility_matrix=matrix,
                pairing_history=history,
                rounds_remaining=10 - round_num,
                pit_stop_counts=pit_stop_counts,
            )

            for p in pairings:
                history.add(make_pair_key(p.attendee_a, p.attendee_b))

            if pit_stop:
                pit_stop_counts[pit_stop] = pit_stop_counts.get(pit_stop, 0) + 1

        # Everyone with a pit stop should have exactly 1
        # (10 rounds with 51 people = 10 pit stops, at most 10 unique people)
        assert all(c <= 1 for c in pit_stop_counts.values()), (
            f"Unfair pit stop distribution: {pit_stop_counts}"
        )

    def test_average_scores_are_reasonable(self):
        """Average composite scores should be positive and differentiated."""
        pool, matrix = self._load_pool(60)
        history: set[str] = set()
        pit_stop_counts: dict[str, int] = {}

        round_avgs = []
        for round_num in range(10):
            pairings, pit_stop = solve_round(
                active_pool=pool,
                compatibility_matrix=matrix,
                pairing_history=history,
                rounds_remaining=10 - round_num,
                pit_stop_counts=pit_stop_counts,
            )

            scores = [p.composite_score for p in pairings]
            if scores:
                round_avgs.append(sum(scores) / len(scores))

            for p in pairings:
                history.add(make_pair_key(p.attendee_a, p.attendee_b))

            if pit_stop:
                pit_stop_counts[pit_stop] = pit_stop_counts.get(pit_stop, 0) + 1

        # All rounds should have positive average scores
        assert all(avg > 0 for avg in round_avgs)

        # Scores should generally decrease over rounds (best matches first)
        # Not enforced strictly since randomness can cause variation
        assert round_avgs[0] >= round_avgs[-1] * 0.5, (
            f"Score degradation too steep: {round_avgs[0]:.1f} → {round_avgs[-1]:.1f}"
        )

    def test_solver_performance_at_scale(self):
        """Solver should complete in under 2 seconds for 80 attendees."""
        import time

        pool, matrix = self._load_pool(80)

        start = time.monotonic()
        pairings, pit_stop = solve_round(
            active_pool=pool,
            compatibility_matrix=matrix,
            pairing_history=set(),
            rounds_remaining=10,
            pit_stop_counts={},
        )
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, f"Solver took {elapsed:.2f}s (expected < 2s)"
        assert len(pairings) == 40  # 80 attendees = 40 pairs
