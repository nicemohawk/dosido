"""Admin API routes — check-in, round control, walk-up, swap, settings."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.broadcaster import broadcaster
from app.config import settings
from app.models import (
    Attendee,
    AttendeeSource,
    AttendeeStatus,
    EventStatus,
)
from app.scoring import make_pair_key
from app.state import state_manager

router = APIRouter(prefix="/api/admin")


# --- Request models ---


class CheckInRequest(BaseModel):
    attendee_id: str
    action: str = "check-in"  # "check-in" or "check-out"


class AdvanceRoundRequest(BaseModel):
    pass


class PauseRequest(BaseModel):
    action: str = "pause"  # "pause" or "resume"


class SwapRequest(BaseModel):
    attendee_id_1: str
    attendee_id_2: str


class WalkUpRequest(BaseModel):
    name: str
    email: str = ""
    lane: str = "flexible"
    role: str = "engineering"
    role_needed: str = "engineering"
    climate_areas: list[str] = []
    top_climate_area: str = ""
    commitment: str = "exploring"
    arrangement: str = "remote-open"
    badge_slug: str = ""


class SettingsRequest(BaseModel):
    round_duration_minutes: int | None = None
    total_rounds: int | None = None


# --- Routes ---


@router.post("/check-in")
async def check_in(request: CheckInRequest):
    if request.action == "check-out":
        attendee = await state_manager.check_out(request.attendee_id)
    else:
        attendee = await state_manager.check_in(request.attendee_id)

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    counts = await state_manager.get_pool_counts()
    await broadcaster.broadcast(
        "checkin_update",
        {"attendee_id": attendee.id, "name": attendee.name, "action": request.action, "pool": counts},
    )

    return {"ok": True, "attendee": attendee.model_dump(), "pool": counts}


@router.post("/advance-round")
async def advance_round():
    state = await state_manager.get_state()

    if state.rounds_remaining <= 0:
        raise HTTPException(status_code=400, detail="No rounds remaining")

    result = await state_manager.advance_round()
    updated_state = await state_manager.get_state()

    # Build display data for broadcast
    attendees = await state_manager.get_all_attendees()
    pairing_display = []
    for p in result.pairings:
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
    if result.pit_stop:
        pit_attendee = attendees.get(result.pit_stop)
        pit_stop_name = pit_attendee.name if pit_attendee else None

    await broadcaster.broadcast(
        "round_update",
        {
            "round_number": result.round_number,
            "rounds_remaining": updated_state.rounds_remaining,
            "total_rounds": result.round_number + updated_state.rounds_remaining,
            "pairings": pairing_display,
            "pit_stop": {"id": result.pit_stop, "name": pit_stop_name},
            "average_score": result.average_score,
            "timer_end": updated_state.timer_end,
        },
    )

    return {
        "ok": True,
        "round": result.model_dump(),
        "state": updated_state.model_dump(),
    }


@router.post("/pause")
async def pause_timer(request: PauseRequest):
    if request.action == "resume":
        state = await state_manager.resume_timer()
        await broadcaster.broadcast(
            "timer_update",
            {"action": "resume", "timer_end": state.timer_end},
        )
    else:
        state = await state_manager.pause_timer()
        await broadcaster.broadcast(
            "timer_update",
            {"action": "pause", "timer_remaining": state.timer_remaining},
        )

    return {"ok": True, "state": state.model_dump()}


@router.post("/swap")
async def swap_override(request: SwapRequest):
    result = await state_manager.swap_pairing(
        request.attendee_id_1, request.attendee_id_2
    )
    if not result:
        raise HTTPException(status_code=400, detail="No active pairings to swap")

    # Broadcast updated pairings
    attendees = await state_manager.get_all_attendees()
    pairing_display = []
    for p in result.pairings:
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
    if result.pit_stop:
        pit_attendee = attendees.get(result.pit_stop)
        pit_stop_name = pit_attendee.name if pit_attendee else None

    state = await state_manager.get_state()
    await broadcaster.broadcast(
        "round_update",
        {
            "round_number": result.round_number,
            "rounds_remaining": state.rounds_remaining,
            "total_rounds": result.round_number + state.rounds_remaining,
            "pairings": pairing_display,
            "pit_stop": {"id": result.pit_stop, "name": pit_stop_name},
            "average_score": result.average_score,
            "timer_end": state.timer_end,
        },
    )

    return {"ok": True, "round": result.model_dump()}


@router.post("/walk-up")
async def add_walk_up(request: WalkUpRequest):
    attendee_id = str(uuid.uuid4())[:8]

    attendee = Attendee(
        id=attendee_id,
        name=request.name,
        email=request.email,
        lane=request.lane,
        role=request.role,
        role_needed=request.role_needed,
        climate_areas=request.climate_areas,
        top_climate_area=request.top_climate_area,
        commitment=request.commitment,
        arrangement=request.arrangement,
        status=AttendeeStatus.CHECKED_IN,
        source=AttendeeSource.WALK_UP,
        has_full_scoring=False,
        badge_slug=request.badge_slug,
    )

    # Assign walk-up badge token if slug provided
    if request.badge_slug:
        token = await state_manager.assign_walkup_badge(
            request.badge_slug, attendee_id
        )
        if token:
            attendee.token = token

    await state_manager.save_attendee(attendee)
    await state_manager.check_in(attendee_id)

    # Queue deterministic scoring against all active attendees is handled
    # by the backfill worker — for now, the walk-up gets deterministic-only
    # scores from the match_score function automatically (no matrix entry = fallback)

    # Queue LLM backfill scoring
    active_pool = await state_manager.get_active_pool()
    for other in active_pool:
        if other.id != attendee_id:
            pair_key = make_pair_key(attendee_id, other.id)
            await state_manager.enqueue_scoring(pair_key)

    counts = await state_manager.get_pool_counts()
    await broadcaster.broadcast(
        "checkin_update",
        {
            "attendee_id": attendee_id,
            "name": attendee.name,
            "action": "walk-up",
            "pool": counts,
        },
    )

    return {"ok": True, "attendee": attendee.model_dump(), "pool": counts}


@router.post("/settings")
async def update_settings(request: SettingsRequest):
    if request.round_duration_minutes is not None:
        settings.round_duration_minutes = request.round_duration_minutes
    if request.total_rounds is not None:
        state = await state_manager.get_state()
        delta = request.total_rounds - (state.round_number + state.rounds_remaining)
        state.rounds_remaining += delta
        await state_manager.set_state(state)

    return {
        "ok": True,
        "round_duration_minutes": settings.round_duration_minutes,
        "total_rounds": request.total_rounds,
    }
