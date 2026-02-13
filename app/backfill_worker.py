"""Background worker for walk-up LLM pairwise scoring backfill.

Runs as an asyncio task during the FastAPI app lifespan. Polls the scoring
queue and makes Claude API calls to backfill LLM scores for walk-up attendees.
"""

from __future__ import annotations

import asyncio
import json
import logging

import anthropic

from app.config import settings
from app.state import state_manager
from pipeline.prompts import PAIRWISE_PROMPT

logger = logging.getLogger(__name__)

# Rate limit: max calls per minute to avoid burning through API quota during rounds
MAX_CALLS_PER_MINUTE = 15
POLL_INTERVAL_SECONDS = 5


async def run_backfill_worker() -> None:
    """Poll scoring queue and process walk-up pairwise scoring."""
    if not settings.anthropic_api_key:
        logger.info("No Anthropic API key configured — backfill worker disabled")
        return

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    calls_this_minute = 0
    minute_start = asyncio.get_event_loop().time()

    logger.info("Backfill worker started")

    while True:
        try:
            # Check rate limit
            now = asyncio.get_event_loop().time()
            if now - minute_start >= 60:
                calls_this_minute = 0
                minute_start = now

            if calls_this_minute >= MAX_CALLS_PER_MINUTE:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            # Poll queue
            pair_key = await state_manager.dequeue_scoring()
            if not pair_key:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            # Get attendee data
            ids = pair_key.split(":")
            if len(ids) != 2:
                continue

            attendees = await state_manager.get_all_attendees()
            a = attendees.get(ids[0])
            b = attendees.get(ids[1])
            if not a or not b:
                continue

            # Build prompt
            prompt = PAIRWISE_PROMPT.format(
                a_role=a.role,
                a_role_needed=a.role_needed,
                a_lane=a.lane,
                a_climate_areas=", ".join(a.climate_areas),
                a_top_area=a.top_climate_area,
                a_commitment=a.commitment,
                a_arrangement=a.arrangement,
                a_location=a.location,
                a_matching_summary=a.matching_summary,
                a_superpower=a.superpower,
                a_domain_tags=", ".join(a.domain_tags),
                a_intention=a.intention_90_day,
                b_role=b.role,
                b_role_needed=b.role_needed,
                b_lane=b.lane,
                b_climate_areas=", ".join(b.climate_areas),
                b_top_area=b.top_climate_area,
                b_commitment=b.commitment,
                b_arrangement=b.arrangement,
                b_location=b.location,
                b_matching_summary=b.matching_summary,
                b_superpower=b.superpower,
                b_domain_tags=", ".join(b.domain_tags),
                b_intention=b.intention_90_day,
            )

            # Call Claude API
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=300,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}],
                )
                result = json.loads(response.content[0].text)
                score_data = {
                    "score": result.get("score", 50),
                    "rationale": result.get("rationale", ""),
                    "spark": result.get("spark", ""),
                }
            except Exception as e:
                logger.warning(f"API call failed for {pair_key}: {e}")
                score_data = {"score": 50, "rationale": "API error", "spark": ""}

            # Store in matrix
            await state_manager.set_pair_score(ids[0], ids[1], score_data)
            calls_this_minute += 1

            logger.info(
                f"Backfill scored {pair_key}: {score_data['score']} "
                f"(queue: {await state_manager.scoring_queue_length()} remaining)"
            )

            # Check if this completes all scoring for a walk-up
            queue_len = await state_manager.scoring_queue_length()
            if queue_len == 0:
                # Mark all walk-ups as fully scored
                all_attendees = await state_manager.get_all_attendees()
                for att in all_attendees.values():
                    if att.source == "walk-up" and not att.has_full_scoring:
                        att.has_full_scoring = True
                        await state_manager.save_attendee(att)
                        logger.info(f"Walk-up {att.name} now fully scored")

        except asyncio.CancelledError:
            logger.info("Backfill worker shutting down")
            break
        except Exception as e:
            logger.error(f"Backfill worker error: {e}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
