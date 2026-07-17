from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class Lane(StrEnum):
    IDEA = "idea"
    JOINER = "joiner"
    FLEXIBLE = "flexible"


class Role(StrEnum):
    ENGINEERING = "engineering"
    PRODUCT = "product"
    GTM = "gtm"
    SCIENCE = "science"
    OPS = "ops"
    POLICY = "policy"


class Commitment(StrEnum):
    FULL_TIME = "full-time"
    FULL_TIME_SOON = "full-time-soon"  # would go full-time within ~3 months for the right person
    PART_TIME = "part-time"
    EXPLORING = "exploring"


COMMITMENT_TIER = {
    Commitment.FULL_TIME: 3,
    Commitment.FULL_TIME_SOON: 2,
    Commitment.PART_TIME: 1,
    Commitment.EXPLORING: 0,
}


class Runway(StrEnum):
    UNDER_3_MONTHS = "under-3-months"
    MONTHS_3_TO_12 = "3-12-months"
    OVER_12_MONTHS = "12-plus-months"
    UNDISCLOSED = "undisclosed"


class Ambition(StrEnum):
    BOOTSTRAP = "bootstrap"
    MODERATE = "moderate"
    VENTURE_SCALE = "venture-scale"
    UNDECIDED = "undecided"


class EquityPhilosophy(StrEnum):
    EQUAL = "equal"
    NEAR_EQUAL_VESTING = "near-equal-vesting"
    CONTRIBUTION_BASED = "contribution-based"
    NO_STRONG_VIEW = "no-strong-view"


class Edge(StrEnum):
    TECHNICAL = "technical"
    DOMAIN = "domain"
    NETWORK = "network"
    UNKNOWN = "unknown"


class IdeaFlexibility(StrEnum):
    COMMITTED = "committed"  # has an idea and is committed to it
    FLEXIBLE = "flexible"  # has an idea but would drop it for a better one
    NOT_APPLICABLE = "n/a"  # joiner / fully flexible lane


class DecisionStyle(StrEnum):
    DEBATE = "debate"
    WRITE_THEN_DECIDE = "write-then-decide"
    DEFER_TO_OWNER = "defer-to-owner"
    DATA_DRIVEN = "data-driven"
    UNKNOWN = "unknown"


class Arrangement(StrEnum):
    COLOCATED = "colocated"
    REMOTE_OPEN = "remote-open"


class AttendeeStatus(StrEnum):
    NOT_ARRIVED = "not-arrived"
    CHECKED_IN = "checked-in"
    DEPARTED = "departed"


class AttendeeSource(StrEnum):
    APPLICATION = "application"
    WAITLIST = "waitlist"
    WALK_UP = "walk-up"


class Attendee(BaseModel):
    id: str
    name: str
    email: str
    location: str = ""
    linkedin_url: str = ""
    token: str = ""

    # Application fields
    lane: Lane = Lane.FLEXIBLE
    role: Role = Role.ENGINEERING
    role_needed: Role = Role.ENGINEERING
    climate_areas: list[str] = []
    top_climate_area: str = ""
    commitment: Commitment = Commitment.EXPLORING
    arrangement: Arrangement = Arrangement.REMOTE_OPEN
    proof_link_1: str = ""
    proof_link_2: str = ""
    intention_90_day: str = ""

    # Cofounder-alignment fields (similarity-scored; mismatches predict breakups)
    runway: Runway = Runway.UNDISCLOSED
    ambition: Ambition = Ambition.UNDECIDED
    equity_philosophy: EquityPhilosophy = EquityPhilosophy.NO_STRONG_VIEW
    idea_flexibility: IdeaFlexibility = IdeaFlexibility.NOT_APPLICABLE

    # Complementarity + conversation-design fields
    edge: Edge = Edge.UNKNOWN
    decision_style: DecisionStyle = DecisionStyle.UNKNOWN
    proof_summary_1: str = ""
    proof_summary_2: str = ""
    hardest_thing: str = ""

    # Enrichment (LLM-generated)
    domain_tags: list[str] = []
    technical_depth: int = 0
    stage: str = ""
    superpower: str = ""
    matching_summary: str = ""
    red_flags: list[str] = []

    # Event state
    status: AttendeeStatus = AttendeeStatus.NOT_ARRIVED
    pit_stop_count: int = 0
    source: AttendeeSource = AttendeeSource.APPLICATION
    has_full_scoring: bool = False

    # Walk-up badge slug (only for walk-ups)
    badge_slug: str = ""


class PairScore(BaseModel):
    pair_key: tuple[str, str]
    llm_score: int = 0
    rationale: str = ""
    spark: str = ""
    composite_score: float = 0.0


class Pairing(BaseModel):
    table_number: int
    attendee_a: str
    attendee_b: str
    composite_score: float


class RoundResult(BaseModel):
    round_number: int
    pairings: list[Pairing]
    pit_stop: str | None = None
    average_score: float = 0.0
    timestamp: str = ""


class Signal(BaseModel):
    round_number: int
    from_attendee: str
    to_attendee: str
    interested: bool = False
    timestamp: str = ""


class MutualMatch(BaseModel):
    attendee_a: str
    attendee_b: str
    round_number: int


class EventStatus(StrEnum):
    PRE_EVENT = "pre-event"
    ROUND_ACTIVE = "round-active"
    BETWEEN_ROUNDS = "between-rounds"
    OPEN_NETWORKING = "open-networking"


class EventState(BaseModel):
    round_number: int = 0
    rounds_remaining: int = 10
    status: EventStatus = EventStatus.PRE_EVENT
    timer_end: str | None = None
    timer_paused: bool = False
    timer_remaining: int | None = None  # seconds remaining when paused
