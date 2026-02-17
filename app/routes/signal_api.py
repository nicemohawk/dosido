"""Signal API routes — follow-up interest signaling and mutual matches."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.broadcaster import broadcaster
from app.state import state_manager

router = APIRouter(prefix="/api")


class SignalRequest(BaseModel):
    from_attendee: str
    to_attendee: str
    round_number: int


@router.post("/signal")
async def record_signal(request: SignalRequest):
    is_mutual = await state_manager.record_signal(
        round_number=request.round_number,
        from_id=request.from_attendee,
        to_id=request.to_attendee,
    )

    attendees = await state_manager.get_all_attendees()
    a = attendees.get(request.from_attendee)
    b = attendees.get(request.to_attendee)

    await broadcaster.broadcast(
        "signal_update",
        {
            "mutual": is_mutual,
            "attendee_a": {
                "id": request.from_attendee,
                "name": a.name if a else "?",
                "token": a.token if a else "",
            },
            "attendee_b": {
                "id": request.to_attendee,
                "name": b.name if b else "?",
                "token": b.token if b else "",
            },
        },
    )

    if is_mutual:
        return {"ok": True, "mutual": True, "match_token": b.token if b else ""}

    return {"ok": True, "mutual": False}


@router.get("/mutual-matches")
async def get_mutual_matches():
    match_keys = await state_manager.get_mutual_matches()
    attendees = await state_manager.get_all_attendees()

    matches = []
    for key in match_keys:
        ids = key.split(":")
        if len(ids) == 2:
            a = attendees.get(ids[0])
            b = attendees.get(ids[1])
            matches.append(
                {
                    "attendee_a": {"id": ids[0], "name": a.name if a else "?"},
                    "attendee_b": {"id": ids[1], "name": b.name if b else "?"},
                }
            )

    return {"matches": matches, "count": len(matches)}
