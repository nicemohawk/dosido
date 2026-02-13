"""Public API routes — event state and SSE stream."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.broadcaster import broadcaster
from app.state import state_manager

router = APIRouter(prefix="/api")


@router.get("/state")
async def get_state():
    state = await state_manager.get_state()
    pairings = await state_manager.get_current_pairings()
    counts = await state_manager.get_pool_counts()
    attendees = await state_manager.get_all_attendees()

    # Build pairing display data with names
    pairing_display = []
    if pairings:
        for p in pairings.pairings:
            a = attendees.get(p.attendee_a)
            b = attendees.get(p.attendee_b)
            pairing_display.append(
                {
                    "table_number": p.table_number,
                    "attendee_a": {"id": p.attendee_a, "name": a.name if a else "?"},
                    "attendee_b": {"id": p.attendee_b, "name": b.name if b else "?"},
                    "composite_score": p.composite_score,
                }
            )

    pit_stop_name = None
    if pairings and pairings.pit_stop:
        pit_attendee = attendees.get(pairings.pit_stop)
        pit_stop_name = pit_attendee.name if pit_attendee else None

    return {
        "state": state.model_dump(),
        "pairings": pairing_display,
        "pit_stop": {
            "id": pairings.pit_stop if pairings else None,
            "name": pit_stop_name,
        },
        "average_score": pairings.average_score if pairings else 0,
        "pool": counts,
    }


@router.get("/state/stream")
async def state_stream():
    """SSE endpoint for real-time updates."""

    async def event_generator():
        # Send initial keepalive
        yield ": connected\n\n"
        async for message in broadcaster.subscribe():
            yield message

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
