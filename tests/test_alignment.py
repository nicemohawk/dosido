"""Tests for cofounder-alignment scoring adjustments and signal selectivity."""

from app.models import Ambition, Attendee, Commitment, Edge, EquityPhilosophy
from app.scoring import (
    _signal_boost,
    alignment_adjustment,
    heuristic_pair_score,
    make_pair_key,
    match_score,
)


def make_attendee(id: str, **overrides) -> Attendee:
    defaults = {
        "name": f"Attendee {id}",
        "email": f"{id}@test.com",
        "climate_areas": ["energy"],
        "commitment": Commitment.FULL_TIME,
    }
    defaults.update(overrides)
    return Attendee(id=id, **defaults)


class TestCommitmentAlignment:
    def test_gap_three_penalty_beats_gap_zero_with_same_llm_score(self):
        matrix = {
            make_pair_key("a", "b"): {"score": 60},
            make_pair_key("c", "d"): {"score": 60},
        }
        aligned_a = make_attendee("a", commitment=Commitment.FULL_TIME)
        aligned_b = make_attendee("b", commitment=Commitment.FULL_TIME)
        mismatched_c = make_attendee("c", commitment=Commitment.FULL_TIME)
        mismatched_d = make_attendee("d", commitment=Commitment.EXPLORING)

        aligned_score = match_score(aligned_a, aligned_b, matrix, set())
        mismatched_score = match_score(mismatched_c, mismatched_d, matrix, set())

        assert aligned_score - mismatched_score == 35  # +10 same tier vs -25 gap of 3

    def test_gap_one_is_neutral_and_gap_two_penalized(self):
        full_time = make_attendee("a", commitment=Commitment.FULL_TIME)
        soon = make_attendee("b", commitment=Commitment.FULL_TIME_SOON)
        part_time = make_attendee("c", commitment=Commitment.PART_TIME)

        assert alignment_adjustment(full_time, soon) == 0
        assert alignment_adjustment(full_time, part_time) == -10


class TestUnknownValuesContributeZero:
    def test_default_new_fields_only_contribute_commitment_term(self):
        a = make_attendee("a")
        b = make_attendee("b")
        assert alignment_adjustment(a, b) == 10  # same commitment tier, nothing else

    def test_one_sided_disclosure_contributes_zero(self):
        a = make_attendee(
            "a",
            ambition=Ambition.BOOTSTRAP,
            equity_philosophy=EquityPhilosophy.EQUAL,
            edge=Edge.TECHNICAL,
        )
        b = make_attendee("b")
        assert alignment_adjustment(a, b) == 10

    def test_match_score_unchanged_for_default_valued_attendees(self):
        matrix = {make_pair_key("a", "b"): {"score": 60}}
        bare_a = make_attendee("a")
        bare_b = make_attendee("b")
        explicit_a = make_attendee(
            "a",
            runway="undisclosed",
            ambition=Ambition.UNDECIDED,
            equity_philosophy=EquityPhilosophy.NO_STRONG_VIEW,
            edge=Edge.UNKNOWN,
        )
        explicit_b = explicit_a.model_copy(update={"id": "b"})

        assert match_score(bare_a, bare_b, matrix, set()) == match_score(
            explicit_a, explicit_b, matrix, set()
        )


class TestAmbitionAndEquityAlignment:
    def test_ambition_same_bonus_and_tail_penalty(self):
        bootstrap = make_attendee("a", ambition=Ambition.BOOTSTRAP)
        bootstrap_too = make_attendee("b", ambition=Ambition.BOOTSTRAP)
        venture = make_attendee("c", ambition=Ambition.VENTURE_SCALE)
        moderate = make_attendee("d", ambition=Ambition.MODERATE)

        assert alignment_adjustment(bootstrap, bootstrap_too) == 20  # +10 commitment +10 ambition
        assert alignment_adjustment(bootstrap, venture) == -10  # +10 commitment -20 tails
        assert alignment_adjustment(bootstrap, moderate) == 10  # adjacent ambition is neutral

    def test_equity_same_bonus_and_tail_penalty(self):
        equal = make_attendee("a", equity_philosophy=EquityPhilosophy.EQUAL)
        equal_too = make_attendee("b", equity_philosophy=EquityPhilosophy.EQUAL)
        contribution = make_attendee("c", equity_philosophy=EquityPhilosophy.CONTRIBUTION_BASED)
        near_equal = make_attendee("d", equity_philosophy=EquityPhilosophy.NEAR_EQUAL_VESTING)

        assert alignment_adjustment(equal, equal_too) == 15  # +10 commitment +5 equity
        assert alignment_adjustment(equal, contribution) == -5  # +10 commitment -15 tails
        assert alignment_adjustment(equal, near_equal) == 10  # adjacent equity is neutral


class TestEdgeComplementarity:
    def test_edge_bonus_requires_shared_climate_area(self):
        technical = make_attendee("a", edge=Edge.TECHNICAL, climate_areas=["energy"])
        domain_shared = make_attendee("b", edge=Edge.DOMAIN, climate_areas=["energy"])
        domain_disjoint = make_attendee("c", edge=Edge.DOMAIN, climate_areas=["water"])

        assert alignment_adjustment(technical, domain_shared) == 20  # +10 commitment +10 edge
        assert alignment_adjustment(technical, domain_disjoint) == 10  # no shared area, no bonus

    def test_same_edge_gets_no_bonus(self):
        a = make_attendee("a", edge=Edge.TECHNICAL)
        b = make_attendee("b", edge=Edge.TECHNICAL)
        assert alignment_adjustment(a, b) == 10


class TestHeuristicBounds:
    def test_heuristic_never_goes_below_zero(self):
        worst_a = make_attendee(
            "a",
            commitment=Commitment.FULL_TIME,
            ambition=Ambition.BOOTSTRAP,
            equity_philosophy=EquityPhilosophy.EQUAL,
            climate_areas=["water"],
            top_climate_area="water",
        )
        worst_b = make_attendee(
            "b",
            commitment=Commitment.EXPLORING,
            ambition=Ambition.VENTURE_SCALE,
            equity_philosophy=EquityPhilosophy.CONTRIBUTION_BASED,
            climate_areas=["food"],
            top_climate_area="food",
            role=worst_a.role,
            role_needed=worst_a.role_needed,
        )
        score = heuristic_pair_score(worst_a, worst_b)
        assert 0 <= score <= 100
        assert score == 0

    def test_heuristic_rewards_alignment_and_edge(self):
        a = make_attendee("a", ambition=Ambition.VENTURE_SCALE, edge=Edge.TECHNICAL)
        b = make_attendee("b", ambition=Ambition.VENTURE_SCALE, edge=Edge.NETWORK)
        c = make_attendee("c")
        d = make_attendee("d")
        assert heuristic_pair_score(a, b) == heuristic_pair_score(c, d) + 15


class TestSignalSelectivity:
    def test_selective_sender_gets_full_weight(self):
        scores = {make_pair_key("candidate", "liked"): 90}
        signals = {"sender": ["liked"]}
        assert _signal_boost("sender", "candidate", signals, scores) == 5.0

    def test_moderate_sender_gets_half_weight(self):
        scores = {make_pair_key("candidate", f"liked{i}"): 90 for i in range(4)}
        signals = {"sender": [f"liked{i}" for i in range(4)]}
        assert _signal_boost("sender", "candidate", signals, scores) == 4 * 2.5

    def test_indiscriminate_sender_gets_quarter_weight(self):
        scores = {make_pair_key("candidate", f"liked{i}"): 90 for i in range(6)}
        signals = {"sender": [f"liked{i}" for i in range(6)]}
        assert _signal_boost("sender", "candidate", signals, scores) == 6 * 1.25

    def test_low_similarity_still_gated(self):
        scores = {make_pair_key("candidate", "liked"): 70}
        signals = {"sender": ["liked"]}
        assert _signal_boost("sender", "candidate", signals, scores) == 0.0
