"""HTML view routes — screen, mobile, admin panel."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.state import state_manager

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/{slug}/screen", response_class=HTMLResponse)
async def projector_screen(request: Request, slug: str):
    state = await state_manager.get_state()
    pairings = await state_manager.get_current_pairings()
    attendees = await state_manager.get_all_attendees()
    counts = await state_manager.get_pool_counts()

    pairing_display = _build_pairing_display(pairings, attendees)
    pit_stop_name = _get_pit_stop_name(pairings, attendees)

    return templates.TemplateResponse(
        "screen.html",
        {
            "request": request,
            "slug": slug,
            "state": state,
            "pairings": pairing_display,
            "pit_stop_name": pit_stop_name,
            "counts": counts,
            "attendees": attendees,
            "settings": settings,
        },
    )


@router.get("/{slug}/a/{token}", response_class=HTMLResponse)
async def badge_view(
    request: Request,
    slug: str,
    token: str,
    claimed_id: str = Cookie(default=None),
):
    """Badge QR view — public profile card, or personal view if claimed."""
    attendee = await state_manager.get_attendee_by_token(token)
    if not attendee:
        return HTMLResponse("Badge not found", status_code=404)

    is_owner = claimed_id == attendee.id

    if not is_owner:
        # Public profile card
        is_claimed = await state_manager.is_badge_claimed(attendee.id)
        return templates.TemplateResponse(
            "profile_card.html",
            {
                "request": request,
                "slug": slug,
                "token": token,
                "attendee": attendee,
                "is_claimed": is_claimed,
                "settings": settings,
            },
        )

    # Personal view — owner has claimed this badge
    state = await state_manager.get_state()
    pairings = await state_manager.get_current_pairings()
    attendees = await state_manager.get_all_attendees()

    my_match = None
    my_match_id = None
    my_table = None
    if pairings:
        for p in pairings.pairings:
            if p.attendee_a == attendee.id:
                partner = attendees.get(p.attendee_b)
                my_match = partner.name if partner else "?"
                my_match_id = p.attendee_b
                my_table = p.table_number
                break
            elif p.attendee_b == attendee.id:
                partner = attendees.get(p.attendee_a)
                my_match = partner.name if partner else "?"
                my_match_id = p.attendee_a
                my_table = p.table_number
                break

    is_pit_stop = pairings and pairings.pit_stop == attendee.id

    # Check if user already submitted feedback this round
    already_signaled = False
    if state.round_number > 0:
        round_signals = await state_manager.get_signals_for_round(state.round_number)
        already_signaled = attendee.id in round_signals

    mutual_matches = []
    all_mutuals = await state_manager.get_mutual_matches()
    for key in all_mutuals:
        ids = key.split(":")
        if attendee.id in ids:
            other_id = ids[0] if ids[1] == attendee.id else ids[1]
            other = attendees.get(other_id)
            if other:
                mutual_matches.append({"name": other.name, "token": other.token})

    response = templates.TemplateResponse(
        "mobile.html",
        {
            "request": request,
            "slug": slug,
            "token": token,
            "attendee": attendee,
            "state": state,
            "my_match": my_match,
            "my_match_id": my_match_id,
            "my_table": my_table,
            "is_pit_stop": is_pit_stop,
            "already_signaled": already_signaled,
            "mutual_matches": mutual_matches,
            "is_personal": True,
            "settings": settings,
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/{slug}/a/{token}/claim")
async def claim_badge(slug: str, token: str):
    """Claim a badge as your own — sets cookie and records in Redis."""
    attendee = await state_manager.get_attendee_by_token(token)
    if not attendee:
        return HTMLResponse("Badge not found", status_code=404)

    await state_manager.claim_badge(attendee.id)
    response = RedirectResponse(f"/{slug}/a/{token}", status_code=303)
    response.set_cookie("claimed_id", attendee.id, max_age=86400, samesite="lax")
    return response


@router.get("/{slug}", response_class=HTMLResponse)
async def general_mobile(request: Request, slug: str):
    """General mobile view — name search/pin fallback."""
    state = await state_manager.get_state()
    pairings = await state_manager.get_current_pairings()
    attendees = await state_manager.get_all_attendees()
    counts = await state_manager.get_pool_counts()

    pairing_display = _build_pairing_display(pairings, attendees)
    pit_stop_name = _get_pit_stop_name(pairings, attendees)

    return templates.TemplateResponse(
        "mobile.html",
        {
            "request": request,
            "slug": slug,
            "token": None,
            "attendee": None,
            "state": state,
            "pairings": pairing_display,
            "pit_stop_name": pit_stop_name,
            "counts": counts,
            "is_personal": False,
            "settings": settings,
        },
    )


@router.get("/{slug}/admin/{token}", response_class=HTMLResponse)
async def admin_panel(request: Request, slug: str, token: str):
    if token != settings.admin_token:
        return HTMLResponse("Not found", status_code=404)

    state = await state_manager.get_state()
    pairings = await state_manager.get_current_pairings()
    attendees = await state_manager.get_all_attendees()
    counts = await state_manager.get_pool_counts()
    walkup_badges = await state_manager.get_available_walkup_badges()

    pairing_display = _build_pairing_display(pairings, attendees)
    pit_stop_name = _get_pit_stop_name(pairings, attendees)

    # Signal stats for current round
    signal_stats = None
    if state.round_number > 0:
        signals = await state_manager.get_signals_for_round(state.round_number)
        mutual_matches = await state_manager.get_mutual_matches()
        signal_stats = {
            "submitted": len(signals),
            "total_active": counts["active"],
            "mutual_total": len(mutual_matches),
        }

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "slug": slug,
            "admin_token": token,
            "state": state,
            "pairings": pairing_display,
            "pit_stop_name": pit_stop_name,
            "counts": counts,
            "attendees": attendees,
            "walkup_badges": walkup_badges,
            "signal_stats": signal_stats,
            "settings": settings,
        },
    )


# --- Admin partial endpoints for live refresh ---


@router.get("/{slug}/admin/{token}/partial/round-control", response_class=HTMLResponse)
async def admin_partial_round_control(request: Request, slug: str, token: str):
    if token != settings.admin_token:
        return HTMLResponse("", status_code=404)
    state = await state_manager.get_state()
    counts = await state_manager.get_pool_counts()
    return templates.TemplateResponse(
        "partials/admin_round_control.html",
        {"request": request, "state": state, "counts": counts, "settings": settings},
    )


@router.get("/{slug}/admin/{token}/partial/pool", response_class=HTMLResponse)
async def admin_partial_pool(request: Request, slug: str, token: str):
    if token != settings.admin_token:
        return HTMLResponse("", status_code=404)
    attendees = await state_manager.get_all_attendees()
    counts = await state_manager.get_pool_counts()
    return templates.TemplateResponse(
        "partials/admin_pool.html",
        {"request": request, "slug": slug, "attendees": attendees, "counts": counts},
    )


@router.get("/{slug}/admin/{token}/partial/pairings", response_class=HTMLResponse)
async def admin_partial_pairings(request: Request, slug: str, token: str):
    if token != settings.admin_token:
        return HTMLResponse("", status_code=404)
    state = await state_manager.get_state()
    pairings = await state_manager.get_current_pairings()
    attendees = await state_manager.get_all_attendees()
    pairing_display = _build_pairing_display(pairings, attendees)
    pit_stop_name = _get_pit_stop_name(pairings, attendees)
    return templates.TemplateResponse(
        "partials/admin_pairings.html",
        {
            "request": request,
            "state": state,
            "pairings": pairing_display,
            "pit_stop_name": pit_stop_name,
            "attendees": attendees,
        },
    )


def _build_pairing_display(pairings, attendees):
    display = []
    if pairings:
        for p in pairings.pairings:
            a = attendees.get(p.attendee_a)
            b = attendees.get(p.attendee_b)
            display.append(
                {
                    "table_number": p.table_number,
                    "name_a": a.name if a else "?",
                    "name_b": b.name if b else "?",
                    "id_a": p.attendee_a,
                    "id_b": p.attendee_b,
                    "score": round(p.composite_score, 1),
                }
            )
    return display


def _get_pit_stop_name(pairings, attendees):
    if pairings and pairings.pit_stop:
        pit = attendees.get(pairings.pit_stop)
        return pit.name if pit else None
    return None
