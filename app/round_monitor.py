"""Background monitor that ends rounds when the round timer expires.

Runs as an asyncio task during the FastAPI app lifespan. Polls event state
and transitions ROUND_ACTIVE -> BETWEEN_ROUNDS once the timer passes zero,
broadcasting a "status_update" SSE event so clients refresh.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.broadcaster import broadcaster
from app.models import EventState, EventStatus
from app.state import state_manager

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 1.0


def round_timer_has_expired(state: EventState, now: datetime | None = None) -> bool:
    """True when an active, unpaused round's timer has run out."""
    if state.status != EventStatus.ROUND_ACTIVE or state.timer_paused or not state.timer_end:
        return False
    current_time = now or datetime.now(timezone.utc)
    return current_time >= datetime.fromisoformat(state.timer_end)


async def end_round_if_expired() -> EventState | None:
    """Transition to BETWEEN_ROUNDS and broadcast if the round timer expired.

    Returns the updated state when a transition happened, otherwise None.
    """
    state = await state_manager.get_state()
    if not round_timer_has_expired(state):
        return None

    updated = await state_manager.set_status(EventStatus.BETWEEN_ROUNDS)
    await broadcaster.broadcast(
        "status_update",
        {"status": updated.status.value, "round_number": updated.round_number},
    )
    logger.info(f"Round {updated.round_number} timer expired — now between rounds")
    return updated


async def run_round_monitor() -> None:
    """Poll event state and end rounds whose timer has expired."""
    logger.info("Round monitor started")
    while True:
        try:
            await end_round_if_expired()
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Round monitor shutting down")
            break
        except Exception as e:
            logger.error(f"Round monitor error: {e}")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
