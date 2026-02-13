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
- matching_summary: 2-3 sentences capturing what they're looking for and what makes them distinctive
- red_flags: any concerns about seriousness or fit (empty array if none)

Output ONLY valid JSON, no markdown formatting."""


PAIRWISE_PROMPT = """You are scoring the cofounder compatibility of two attendees at a climate startup matchmaking event. Score how promising this pairing would be for a first meeting.

Person A:
- Role: {a_role} | Needs: {a_role_needed} | Lane: {a_lane}
- Climate areas: {a_climate_areas} | Top: {a_top_area}
- Commitment: {a_commitment} | Arrangement: {a_arrangement}
- Location: {a_location}
- Matching summary: {a_matching_summary}
- Superpower: {a_superpower}
- Domain tags: {a_domain_tags}
- 90-day intention: {a_intention}

Person B:
- Role: {b_role} | Needs: {b_role_needed} | Lane: {b_lane}
- Climate areas: {b_climate_areas} | Top: {b_top_area}
- Commitment: {b_commitment} | Arrangement: {b_arrangement}
- Location: {b_location}
- Matching summary: {b_matching_summary}
- Superpower: {b_superpower}
- Domain tags: {b_domain_tags}
- 90-day intention: {b_intention}

Scoring guidance:
- 80-100: Strong complementary roles, overlapping domain interest, compatible constraints. These two should definitely meet.
- 50-79: Some complementarity or shared interest. Worth meeting if higher-scoring pairs aren't available.
- 20-49: Weak overlap. Only pair if pool is thin.
- 0-19: Incompatible constraints or redundant profiles. Avoid pairing.

Output JSON:
- score: integer 0-100 (how valuable is this first meeting?)
- rationale: one sentence explaining the score
- spark: one specific conversation topic they should explore

Output ONLY valid JSON, no markdown formatting."""
