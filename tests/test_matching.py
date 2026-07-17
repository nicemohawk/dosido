"""Tests for the matching engine and scoring function."""

from app.matching import _pit_stop_candidates, solve_round
from app.models import Arrangement, Attendee, AttendeeSource, Commitment, Lane, Role
from app.scoring import make_pair_key, match_score


def make_attendee(
    id: str,
    name: str = "",
    role: Role = Role.ENGINEERING,
    role_needed: Role = Role.PRODUCT,
    lane: Lane = Lane.IDEA,
    climate_areas: list[str] | None = None,
    top_climate_area: str = "energy",
    commitment: Commitment = Commitment.FULL_TIME,
    arrangement: Arrangement = Arrangement.REMOTE_OPEN,
    location: str = "SF",
    source: AttendeeSource = AttendeeSource.APPLICATION,
) -> Attendee:
    return Attendee(
        id=id,
        name=name or f"Attendee {id}",
        email=f"{id}@test.com",
        role=role,
        role_needed=role_needed,
        lane=lane,
        climate_areas=climate_areas or ["energy"],
        top_climate_area=top_climate_area,
        commitment=commitment,
        arrangement=arrangement,
        location=location,
        source=source,
    )


# --- Scoring tests ---


class TestMatchScore:
    def test_already_met_returns_negative_inf(self):
        a = make_attendee("a")
        b = make_attendee("b")
        history = {make_pair_key("a", "b")}
        score = match_score(a, b, {}, history)
        assert score == float("-inf")

    def test_colocated_different_cities_returns_negative_inf(self):
        a = make_attendee("a", arrangement=Arrangement.COLOCATED, location="SF")
        b = make_attendee("b", arrangement=Arrangement.COLOCATED, location="NYC")
        score = match_score(a, b, {}, set())
        assert score == float("-inf")

    def test_colocated_same_city_is_fine(self):
        a = make_attendee("a", arrangement=Arrangement.COLOCATED, location="SF")
        b = make_attendee("b", arrangement=Arrangement.COLOCATED, location="SF")
        score = match_score(a, b, {}, set())
        assert score > float("-inf")

    def test_one_remote_open_bypasses_colocated_check(self):
        a = make_attendee("a", arrangement=Arrangement.COLOCATED, location="SF")
        b = make_attendee("b", arrangement=Arrangement.REMOTE_OPEN, location="NYC")
        score = match_score(a, b, {}, set())
        assert score > float("-inf")

    def test_llm_score_is_primary_signal(self):
        a = make_attendee("a")
        b = make_attendee("b")
        pair_key = make_pair_key("a", "b")
        matrix = {pair_key: {"score": 85, "rationale": "Great match", "spark": "Topic"}}
        score = match_score(a, b, matrix, set())
        assert score >= 85  # LLM score + bonuses

    def test_role_complementarity_bonus(self):
        a = make_attendee("a", role=Role.ENGINEERING, role_needed=Role.GTM)
        b = make_attendee("b", role=Role.GTM, role_needed=Role.ENGINEERING)
        pair_key = make_pair_key("a", "b")
        matrix = {pair_key: {"score": 50}}

        # With complementary roles
        score_complementary = match_score(a, b, matrix, set())

        # Without complementary roles
        c = make_attendee("c", role=Role.ENGINEERING, role_needed=Role.GTM)
        d = make_attendee("d", role=Role.ENGINEERING, role_needed=Role.GTM)
        pair_key_cd = make_pair_key("c", "d")
        matrix[pair_key_cd] = {"score": 50}
        score_same = match_score(c, d, matrix, set())

        assert score_complementary > score_same

    def test_lane_complementarity_bonus(self):
        a = make_attendee("a", lane=Lane.IDEA)
        b = make_attendee("b", lane=Lane.JOINER)
        pair_key = make_pair_key("a", "b")
        matrix = {pair_key: {"score": 50}}

        score_complementary = match_score(a, b, matrix, set())

        c = make_attendee("c", lane=Lane.IDEA)
        d = make_attendee("d", lane=Lane.IDEA)
        pair_key_cd = make_pair_key("c", "d")
        matrix[pair_key_cd] = {"score": 50}
        score_same = match_score(c, d, matrix, set())

        assert score_complementary > score_same

    def test_climate_overlap_bonus(self):
        a = make_attendee(
            "a", climate_areas=["energy", "transport", "carbon"], top_climate_area="energy"
        )
        b = make_attendee("b", climate_areas=["energy", "transport"], top_climate_area="energy")
        pair_key = make_pair_key("a", "b")
        matrix = {pair_key: {"score": 50}}

        score_overlap = match_score(a, b, matrix, set())

        c = make_attendee("c", climate_areas=["water"], top_climate_area="water")
        d = make_attendee("d", climate_areas=["food"], top_climate_area="food")
        pair_key_cd = make_pair_key("c", "d")
        matrix[pair_key_cd] = {"score": 50}
        score_no_overlap = match_score(c, d, matrix, set())

        assert score_overlap > score_no_overlap

    def test_walk_up_without_llm_score(self):
        """Walk-ups without LLM scores get heuristic base scoring."""
        a = make_attendee("a", role=Role.ENGINEERING, role_needed=Role.GTM, lane=Lane.IDEA)
        b = make_attendee(
            "b",
            role=Role.GTM,
            role_needed=Role.ENGINEERING,
            lane=Lane.JOINER,
            source=AttendeeSource.WALK_UP,
        )
        # Empty matrix — no LLM score exists
        score = match_score(a, b, {}, set())
        assert score > 0  # Should get a reasonable deterministic score

    def test_unscored_pair_competes_on_llm_scale(self):
        """A strong unscored pair should outrank a weak LLM-scored pair."""
        a = make_attendee("a", role=Role.ENGINEERING, role_needed=Role.GTM, lane=Lane.IDEA)
        b = make_attendee("b", role=Role.GTM, role_needed=Role.ENGINEERING, lane=Lane.JOINER)
        c = make_attendee("c", role=Role.ENGINEERING, role_needed=Role.GTM, lane=Lane.IDEA)
        d = make_attendee("d", role=Role.ENGINEERING, role_needed=Role.OPS, lane=Lane.IDEA)

        matrix = {make_pair_key("c", "d"): {"score": 15}}

        strong_unscored = match_score(a, b, matrix, set())
        weak_scored = match_score(c, d, matrix, set())
        assert strong_unscored > weak_scored

    def test_heuristic_pair_score_bounds(self):
        """Heuristic base score stays on the LLM's 0-100 scale."""
        from app.scoring import heuristic_pair_score

        strong_a = make_attendee(
            "a",
            role=Role.ENGINEERING,
            role_needed=Role.GTM,
            lane=Lane.IDEA,
            climate_areas=["energy", "solar"],
            arrangement=Arrangement.COLOCATED,
        )
        strong_b = make_attendee(
            "b",
            role=Role.GTM,
            role_needed=Role.ENGINEERING,
            lane=Lane.JOINER,
            climate_areas=["energy", "solar"],
            arrangement=Arrangement.COLOCATED,
        )
        weak_c = make_attendee("c", role=Role.OPS, role_needed=Role.OPS, climate_areas=["water"])
        weak_d = make_attendee("d", role=Role.OPS, role_needed=Role.OPS, climate_areas=["food"])

        strong = heuristic_pair_score(strong_a, strong_b)
        weak = heuristic_pair_score(weak_c, weak_d)

        assert 0 <= weak < strong <= 100


# --- Matching tests ---


class TestSolveRound:
    def test_basic_even_pool(self):
        pool = [make_attendee(str(i)) for i in range(4)]
        matrix = {}
        for i in range(4):
            for j in range(i + 1, 4):
                key = make_pair_key(str(i), str(j))
                matrix[key] = {"score": 50 + i + j}

        pairings, pit_stop = solve_round(pool, matrix, set(), 5, {})

        assert pit_stop is None
        assert len(pairings) == 2
        # All attendees are in exactly one pairing
        paired_ids = set()
        for p in pairings:
            paired_ids.add(p.attendee_a)
            paired_ids.add(p.attendee_b)
        assert paired_ids == {"0", "1", "2", "3"}

    def test_odd_pool_has_pit_stop(self):
        pool = [make_attendee(str(i)) for i in range(5)]
        matrix = {}
        for i in range(5):
            for j in range(i + 1, 5):
                key = make_pair_key(str(i), str(j))
                matrix[key] = {"score": 50}

        pairings, pit_stop = solve_round(pool, matrix, set(), 5, {})

        assert pit_stop is not None
        assert len(pairings) == 2
        paired_ids = set()
        for p in pairings:
            paired_ids.add(p.attendee_a)
            paired_ids.add(p.attendee_b)
        assert pit_stop not in paired_ids

    def test_no_repeat_pairings(self):
        """Running multiple rounds should never repeat a pairing."""
        pool = [make_attendee(str(i)) for i in range(6)]
        matrix = {}
        for i in range(6):
            for j in range(i + 1, 6):
                key = make_pair_key(str(i), str(j))
                matrix[key] = {"score": 50}

        history: set[str] = set()
        pit_stop_counts: dict[str, int] = {}
        all_pair_keys: list[str] = []

        for round_num in range(5):
            pairings, pit_stop = solve_round(pool, matrix, history, 5 - round_num, pit_stop_counts)
            for p in pairings:
                pair_key = make_pair_key(p.attendee_a, p.attendee_b)
                assert pair_key not in all_pair_keys, (
                    f"Repeat pairing {pair_key} in round {round_num}"
                )
                all_pair_keys.append(pair_key)
                history.add(pair_key)

    def test_pit_stop_fairness(self):
        """No one should get two pit stops before everyone has had one."""
        pool = [make_attendee(str(i)) for i in range(5)]
        matrix = {}
        for i in range(5):
            for j in range(i + 1, 5):
                key = make_pair_key(str(i), str(j))
                matrix[key] = {"score": 50}

        history: set[str] = set()
        pit_stop_counts: dict[str, int] = {}
        pit_stop_ids: list[str] = []

        for round_num in range(5):
            pairings, pit_stop = solve_round(pool, matrix, history, 5 - round_num, pit_stop_counts)
            if pit_stop:
                pit_stop_ids.append(pit_stop)
                pit_stop_counts[pit_stop] = pit_stop_counts.get(pit_stop, 0) + 1
            for p in pairings:
                history.add(make_pair_key(p.attendee_a, p.attendee_b))

        # No one should get a second pit stop until everyone has had one
        counts = list(pit_stop_counts.values())
        assert max(counts) - min(counts) <= 1

    def test_walk_up_not_pit_stopped_first(self):
        """Walk-ups should not be eligible for pit stop while others are."""
        pool = [
            make_attendee("0"),
            make_attendee("1"),
            make_attendee("2", source=AttendeeSource.WALK_UP),
        ]
        pit_stop_counts: dict[str, int] = {}

        candidates = _pit_stop_candidates(pool, pit_stop_counts)
        assert "2" not in candidates
        assert set(candidates) == {"0", "1"}

    def test_pit_stop_choice_minimizes_quality_loss(self):
        """The solver should sit out the attendee whose absence costs least."""
        pool = [make_attendee(str(i)) for i in range(3)]
        matrix = {
            make_pair_key("0", "1"): {"score": 90},
            make_pair_key("0", "2"): {"score": 10},
            make_pair_key("1", "2"): {"score": 10},
        }

        pairings, pit_stop = solve_round(pool, matrix, set(), 5, {})

        assert pit_stop == "2"  # Sitting out "2" preserves the 90-point pair
        assert len(pairings) == 1
        assert {pairings[0].attendee_a, pairings[0].attendee_b} == {"0", "1"}

    def test_empty_pool(self):
        pairings, pit_stop = solve_round([], {}, set(), 5, {})
        assert pairings == []
        assert pit_stop is None

    def test_single_attendee(self):
        pool = [make_attendee("0")]
        pairings, pit_stop = solve_round(pool, {}, set(), 5, {})
        assert pairings == []

    def test_two_attendees(self):
        pool = [make_attendee("0"), make_attendee("1")]
        key = make_pair_key("0", "1")
        matrix = {key: {"score": 75}}

        pairings, pit_stop = solve_round(pool, matrix, set(), 5, {})

        assert pit_stop is None
        assert len(pairings) == 1
        assert pairings[0].attendee_a in ("0", "1")
        assert pairings[0].attendee_b in ("0", "1")

    def test_table_numbers_are_sequential(self):
        pool = [make_attendee(str(i)) for i in range(8)]
        matrix = {}
        for i in range(8):
            for j in range(i + 1, 8):
                key = make_pair_key(str(i), str(j))
                matrix[key] = {"score": 50}

        pairings, _ = solve_round(pool, matrix, set(), 5, {})

        table_numbers = sorted([p.table_number for p in pairings])
        assert table_numbers == [1, 2, 3, 4]
