"""Prompt templates for LLM enrichment and pairwise scoring."""

ENRICHMENT_PROMPT = """You are analyzing a prospective attendee for a climate cofounder matchmaking event.

Here is their application:
- Lane: {lane}
- Primary role: {role}
- Role needed: {role_needed}
- Climate areas: {climate_areas}
- Top climate area: {top_area}
- Commitment: {commitment}
- Working arrangement: {arrangement}
- Location: {location}
- Proof links: {link_1}, {link_2}
- 90-day intention: {intention}

{linkedin_section}

Output a JSON object with the following fields:
- domain_tags: array of specific climate domain expertise tags (more granular than their self-selected areas, e.g. "grid-scale battery storage" not just "energy")
- technical_depth: integer 0-5 based on proof links + LinkedIn
- stage: one of "first-time-founder", "repeat-founder", "operator", "researcher", "student"
- superpower: one sentence — what this person uniquely brings to a founding team
- matching_summary: 2-3 sentences capturing what they're looking for, their inferred motivation type (wealth-driven, control-driven, or impact-driven), their intensity level, and what their edge appears to be (technical, domain, or network)
- red_flags: any concerns about seriousness or fit (empty array if none)

Output ONLY valid JSON, no markdown formatting."""


PAIRWISE_PROMPT = """You are scoring the cofounder compatibility of two attendees at a climate startup matchmaking event. Score how promising this pairing would be for a first meeting, using the research-backed rubric below. Cofounder breakups are overwhelmingly caused by misalignment on commitment, ambition, and equity — not by skill gaps — so weigh alignment mismatches heavily.

Person A:
- Role: {a_role} | Needs: {a_role_needed} | Lane: {a_lane}
- Climate areas: {a_climate_areas} | Top: {a_top_area}
- Commitment: {a_commitment} | Runway: {a_runway} | Arrangement: {a_arrangement}
- Ambition: {a_ambition} | Equity philosophy: {a_equity_philosophy} | Idea flexibility: {a_idea_flexibility}
- Edge: {a_edge}
- Location: {a_location}
- Matching summary: {a_matching_summary}
- Superpower: {a_superpower}
- Domain tags: {a_domain_tags}
- 90-day intention: {a_intention}
- Hardest thing they've done: {a_hardest_thing}
- Proof of work: {a_proof_summary_1} | {a_proof_summary_2}

Person B:
- Role: {b_role} | Needs: {b_role_needed} | Lane: {b_lane}
- Climate areas: {b_climate_areas} | Top: {b_top_area}
- Commitment: {b_commitment} | Runway: {b_runway} | Arrangement: {b_arrangement}
- Ambition: {b_ambition} | Equity philosophy: {b_equity_philosophy} | Idea flexibility: {b_idea_flexibility}
- Edge: {b_edge}
- Location: {b_location}
- Matching summary: {b_matching_summary}
- Superpower: {b_superpower}
- Domain tags: {b_domain_tags}
- 90-day intention: {b_intention}
- Hardest thing they've done: {b_hardest_thing}
- Proof of work: {b_proof_summary_1} | {b_proof_summary_2}

Scoring rubric:

ALIGNMENT dimensions — score these on SIMILARITY (mismatches predict breakups):
- Commitment and timing: are they on the same tier of readiness to go full-time?
- Runway realism: can both actually sustain the same working pace and timeline?
- Ambition and exit horizon: bootstrap vs venture-scale is a fundamental fork.
- Equity philosophy: equal-split vs contribution-based people negotiate from incompatible premises.
- Intensity and values: infer from the free text (90-day intention, hardest thing, proof of work) whether these two operate at a similar intensity and care about similar things.

COMPLEMENTARITY dimensions — score these on DIFFERENCE (redundancy wastes a seat):
- Skills: does each person offer roughly what the other says they need?
- Edge: different edge types (technical vs domain vs network) within a SHARED climate domain interest is the strongest complementarity signal.

Treat undisclosed/undecided/no-strong-view/unknown values as neutral — never penalize someone for skipping a question.

DEALBREAKER CAPS — if any of these hold, the score MUST be 30 or lower regardless of other fit:
- Commitment: one is full-time and the other is exploring.
- Ambition: opposite tails (bootstrap vs venture-scale).
- Equity: opposite tails (equal vs contribution-based).

Calibration anchors (use the full scale; do not cluster around 60-75):
- 90: aligned on commitment tier, ambition, and equity; each offers the skill the other needs; different edges in the same climate domain. A plausible founding team today.
- 60: aligned on the big three with real domain overlap, but skills are partially redundant or one alignment field is unknown. A good conversation, not an obvious team.
- 20: a dealbreaker mismatch, or no domain overlap and redundant skills. This meeting costs a round.

The spark must be a pair-specific MICRO-DECISION task the two can actually work through in 8 minutes, with built-in disagreement potential — a small safe disagreement is diagnostic where rapport is not. Good shapes: work one person's stated 90-day blocker together and force a concrete next step; "if you two started something in <their shared climate area> tomorrow, who's CEO and why"; a 2-minute mock negotiation over a specific equity or roadmap tradeoff drawn from their profiles. NOT a generic discussion topic.

Output JSON:
- score: integer 0-100 (how valuable is this first meeting?)
- rationale: one sentence explaining the score
- spark: the micro-decision task, phrased as a direct instruction to the pair

Output ONLY valid JSON, no markdown formatting."""
