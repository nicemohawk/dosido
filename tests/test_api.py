"""Tests for the web API — admin routes, public state, signals, views, and SSE."""

from __future__ import annotations

import pytest

from app.config import settings
from tests.conftest import check_in_all, seed_attendees, seed_matrix

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    async def test_health_check(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Check-in / Check-out
# ---------------------------------------------------------------------------


class TestCheckIn:
    async def test_check_in_attendee(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=2)
        resp = await client.post(
            "/api/admin/check-in",
            json={"attendee_id": attendees[0]["id"], "action": "check-in"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["pool"]["active"] == 1

    async def test_check_out_attendee(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=2)
        await check_in_all(client, attendees)

        resp = await client.post(
            "/api/admin/check-in",
            json={"attendee_id": attendees[0]["id"], "action": "check-out"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["pool"]["active"] == 1
        assert data["pool"]["departed"] == 1

    async def test_check_in_unknown_attendee(self, client):
        resp = await client.post(
            "/api/admin/check-in",
            json={"attendee_id": "nonexistent", "action": "check-in"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Advance round
# ---------------------------------------------------------------------------


class TestAdvanceRound:
    async def test_advance_round(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=6)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)

        resp = await client.post("/api/admin/advance-round", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["state"]["round_number"] == 1
        assert data["state"]["status"] == "round-active"
        assert len(data["round"]["pairings"]) == 3  # 6 attendees → 3 pairs

    async def test_advance_round_odd_pool(self, client, fake_redis):
        """Odd pool → one pit stop."""
        attendees = await seed_attendees(fake_redis, count=5)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)

        resp = await client.post("/api/admin/advance-round", json={})
        data = resp.json()
        assert len(data["round"]["pairings"]) == 2  # 5 → 2 pairs + 1 pit stop
        assert data["round"]["pit_stop"] is not None

    async def test_no_rounds_remaining(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)

        # Set rounds_remaining to 0 via settings
        prefix = f"event:{settings.event_slug}"
        from app.models import EventState

        state = EventState(rounds_remaining=0)
        await fake_redis.set(f"{prefix}:state", state.model_dump_json())

        resp = await client.post("/api/admin/advance-round", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Pause / Resume
# ---------------------------------------------------------------------------


class TestPauseResume:
    async def test_pause_timer(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})

        resp = await client.post("/api/admin/pause", json={"action": "pause"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"]["timer_paused"] is True
        assert data["state"]["timer_remaining"] is not None
        assert data["state"]["timer_end"] is None

    async def test_resume_timer(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})
        await client.post("/api/admin/pause", json={"action": "pause"})

        resp = await client.post("/api/admin/pause", json={"action": "resume"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"]["timer_paused"] is False
        assert data["state"]["timer_end"] is not None


# ---------------------------------------------------------------------------
# Undo round
# ---------------------------------------------------------------------------


class TestUndoRound:
    async def test_undo_round_1(self, client, fake_redis):
        """Undo the only round → back to pre-event."""
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})

        resp = await client.post("/api/admin/undo-round", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"]["round_number"] == 0
        assert data["state"]["status"] == "pre-event"

    async def test_undo_round_2(self, client, fake_redis):
        """Undo round 2 → back to round 1 between-rounds."""
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)

        await client.post("/api/admin/advance-round", json={})
        await client.post("/api/admin/advance-round", json={})

        resp = await client.post("/api/admin/undo-round", json={})
        data = resp.json()
        assert data["state"]["round_number"] == 1
        assert data["state"]["status"] == "between-rounds"

    async def test_undo_with_no_rounds(self, client):
        resp = await client.post("/api/admin/undo-round", json={})
        assert resp.status_code == 400

    async def test_undo_then_advance_again(self, client, fake_redis):
        """Undo then re-advance — should not repeat pairings from undone round."""
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)

        # Round 1
        await client.post("/api/admin/advance-round", json={})

        # Undo
        await client.post("/api/admin/undo-round", json={})

        # Round 1 again — should succeed (history was rolled back)
        r1b = await client.post("/api/admin/advance-round", json={})
        assert r1b.status_code == 200
        assert r1b.json()["state"]["round_number"] == 1


# ---------------------------------------------------------------------------
# Swap override
# ---------------------------------------------------------------------------


class TestSwap:
    async def test_swap_two_attendees(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)

        r1 = await client.post("/api/admin/advance-round", json={})
        pairings = r1.json()["round"]["pairings"]

        # Pick one attendee from each pairing
        a1 = pairings[0]["attendee_a"]
        a2 = pairings[1]["attendee_a"]

        resp = await client.post(
            "/api/admin/swap",
            json={"attendee_id_1": a1, "attendee_id_2": a2},
        )
        assert resp.status_code == 200
        new_pairings = resp.json()["round"]["pairings"]
        assert len(new_pairings) == len(pairings)

    async def test_swap_with_no_pairings(self, client):
        resp = await client.post(
            "/api/admin/swap",
            json={"attendee_id_1": "a", "attendee_id_2": "b"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Walk-up
# ---------------------------------------------------------------------------


class TestWalkUp:
    async def test_add_walk_up(self, client, fake_redis):
        # Seed one regular attendee so the walk-up has someone to be scored against
        await seed_attendees(fake_redis, count=1)

        resp = await client.post(
            "/api/admin/walk-up",
            json={
                "name": "Walk-Up Person",
                "lane": "flexible",
                "role": "engineering",
                "role_needed": "product",
                "top_climate_area": "energy",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["attendee"]["name"] == "Walk-Up Person"
        assert data["attendee"]["source"] == "walk-up"
        assert data["pool"]["active"] == 1


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class TestSettings:
    async def test_update_settings(self, client, fake_redis):
        # Initialize state so rounds_remaining exists
        from app.models import EventState

        prefix = f"event:{settings.event_slug}"
        state = EventState(rounds_remaining=10)
        await fake_redis.set(f"{prefix}:state", state.model_dump_json())

        resp = await client.post(
            "/api/admin/settings",
            json={"round_duration_minutes": 5, "total_rounds": 12},
        )
        assert resp.status_code == 200
        assert resp.json()["round_duration_minutes"] == 5


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class TestSignals:
    async def test_signal_no_mutual(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})

        resp = await client.post(
            "/api/signal",
            json={
                "from_attendee": attendees[0]["id"],
                "to_attendee": attendees[1]["id"],
                "round_number": 1,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["mutual"] is False

    async def test_mutual_signal(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})

        # A → B
        await client.post(
            "/api/signal",
            json={
                "from_attendee": attendees[0]["id"],
                "to_attendee": attendees[1]["id"],
                "round_number": 1,
            },
        )
        # B → A
        resp = await client.post(
            "/api/signal",
            json={
                "from_attendee": attendees[1]["id"],
                "to_attendee": attendees[0]["id"],
                "round_number": 1,
            },
        )
        assert resp.json()["mutual"] is True

    async def test_get_mutual_matches(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})

        # Create a mutual match
        await client.post(
            "/api/signal",
            json={
                "from_attendee": attendees[0]["id"],
                "to_attendee": attendees[1]["id"],
                "round_number": 1,
            },
        )
        await client.post(
            "/api/signal",
            json={
                "from_attendee": attendees[1]["id"],
                "to_attendee": attendees[0]["id"],
                "round_number": 1,
            },
        )

        resp = await client.get("/api/mutual-matches")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1


# ---------------------------------------------------------------------------
# Public state API
# ---------------------------------------------------------------------------


class TestPublicAPI:
    async def test_get_state(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await check_in_all(client, attendees)

        resp = await client.get("/api/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pool"]["active"] == 4
        assert data["state"]["round_number"] == 0

    async def test_get_state_with_pairings(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})

        resp = await client.get("/api/state")
        data = resp.json()
        assert data["state"]["round_number"] == 1
        assert len(data["pairings"]) == 2


# ---------------------------------------------------------------------------
# View routes — verify they render without errors
# ---------------------------------------------------------------------------


class TestViews:
    async def test_admin_panel(self, client, fake_redis):
        await seed_attendees(fake_redis, count=2)

        resp = await client.get("/test-event/admin/test-admin-token")
        assert resp.status_code == 200
        assert "Admin" in resp.text
        assert "Round Control" in resp.text

    async def test_admin_panel_wrong_token(self, client):
        resp = await client.get("/test-event/admin/wrong-token")
        assert resp.status_code == 404

    async def test_screen_view(self, client, fake_redis):
        await seed_attendees(fake_redis, count=2)

        resp = await client.get("/test-event/screen")
        assert resp.status_code == 200
        assert "timer-display" in resp.text

    async def test_general_mobile_view(self, client, fake_redis):
        await seed_attendees(fake_redis, count=2)

        resp = await client.get("/test-event")
        assert resp.status_code == 200
        assert "search-input" in resp.text

    async def test_badge_profile_card(self, client, fake_redis):
        """Badge QR shows profile card to non-owners."""
        prefix = f"event:{settings.event_slug}"
        attendees = await seed_attendees(fake_redis, count=1)
        await fake_redis.hset(f"{prefix}:tokens", "test-token", attendees[0]["id"])

        resp = await client.get("/test-event/a/test-token")
        assert resp.status_code == 200
        assert "Test Person 0" in resp.text
        assert "This is me" in resp.text

    async def test_personal_mobile_view(self, client, fake_redis):
        """Badge QR shows personal view when owner has claimed."""
        prefix = f"event:{settings.event_slug}"
        attendees = await seed_attendees(fake_redis, count=1)
        await fake_redis.hset(f"{prefix}:tokens", "test-token", attendees[0]["id"])

        client.cookies.set("claimed_id", attendees[0]["id"])
        resp = await client.get("/test-event/a/test-token")
        assert resp.status_code == 200
        assert "Welcome," in resp.text
        assert "Test Person 0" in resp.text

    async def test_personal_view_follow_up_list(self, client, fake_redis):
        """Follow-up list renders mutual matches on page load."""
        prefix = f"event:{settings.event_slug}"
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)

        # Set up tokens
        await fake_redis.hset(f"{prefix}:tokens", "token-0", attendees[0]["id"])
        await fake_redis.hset(f"{prefix}:tokens", "token-1", attendees[1]["id"])

        # Advance a round
        await client.post("/api/admin/advance-round", json={})

        # Create mutual signals
        await client.post(
            "/api/signal",
            json={
                "from_attendee": attendees[0]["id"],
                "to_attendee": attendees[1]["id"],
                "round_number": 1,
            },
        )
        await client.post(
            "/api/signal",
            json={
                "from_attendee": attendees[1]["id"],
                "to_attendee": attendees[0]["id"],
                "round_number": 1,
            },
        )

        # Verify mutual match exists in Redis
        mutuals = await fake_redis.smembers(f"{prefix}:mutual_matches")
        assert len(mutuals) == 1

        # Load personal view as attendee 0
        client.cookies.set("claimed_id", attendees[0]["id"])
        resp = await client.get("/test-event/a/token-0")
        assert resp.status_code == 200
        assert "Follow-Up List" in resp.text, (
            f"Follow-Up List not found in response. Mutual matches in Redis: {mutuals}"
        )
        assert "Test Person 1" in resp.text

        # "Reload" — load same page again, list should persist
        resp2 = await client.get("/test-event/a/token-0")
        assert resp2.status_code == 200
        assert "Follow-Up List" in resp2.text, "Follow-Up List lost on reload"
        assert "Test Person 1" in resp2.text, "Match name lost on reload"

        # Also verify attendee 1 sees it from their side
        client.cookies.set("claimed_id", attendees[1]["id"])
        resp3 = await client.get("/test-event/a/token-1")
        assert resp3.status_code == 200
        assert "Follow-Up List" in resp3.text, "Attendee 1 should also see follow-up list"
        assert "Test Person 0" in resp3.text, "Attendee 1 should see Person 0 in list"

    async def test_admin_partial_round_control(self, client, fake_redis):
        await seed_attendees(fake_redis, count=2)

        resp = await client.get("/test-event/admin/test-admin-token/partial/round-control")
        assert resp.status_code == 200
        assert "Start Round" in resp.text

    async def test_admin_partial_pool(self, client, fake_redis):
        attendees = await seed_attendees(fake_redis, count=2)
        await check_in_all(client, attendees)

        resp = await client.get("/test-event/admin/test-admin-token/partial/pool")
        assert resp.status_code == 200
        assert "Test Person" in resp.text

    async def test_admin_partial_pairings(self, client, fake_redis):
        resp = await client.get("/test-event/admin/test-admin-token/partial/pairings")
        assert resp.status_code == 200
        assert "No pairings" in resp.text


# ---------------------------------------------------------------------------
# Full round lifecycle
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    async def test_checkin_advance_pause_undo(self, client, fake_redis):
        """Walk through a full admin workflow."""
        attendees = await seed_attendees(fake_redis, count=6)
        await seed_matrix(fake_redis, attendees)

        # Check in all
        await check_in_all(client, attendees)

        # Verify pool
        state_resp = await client.get("/api/state")
        assert state_resp.json()["pool"]["active"] == 6

        # Start round 1
        r1 = await client.post("/api/admin/advance-round", json={})
        assert r1.json()["state"]["round_number"] == 1
        assert r1.json()["state"]["status"] == "round-active"

        # Pause timer
        pause = await client.post("/api/admin/pause", json={"action": "pause"})
        assert pause.json()["state"]["timer_paused"] is True

        # Resume timer
        resume = await client.post("/api/admin/pause", json={"action": "resume"})
        assert resume.json()["state"]["timer_paused"] is False
        assert resume.json()["state"]["timer_end"] is not None

        # Start round 2
        r2 = await client.post("/api/admin/advance-round", json={})
        assert r2.json()["state"]["round_number"] == 2

        # Undo round 2
        undo = await client.post("/api/admin/undo-round", json={})
        assert undo.json()["state"]["round_number"] == 1

        # Check out one attendee
        checkout = await client.post(
            "/api/admin/check-in",
            json={"attendee_id": attendees[0]["id"], "action": "check-out"},
        )
        assert checkout.json()["pool"]["active"] == 5

        # Round 2 with 5 people (odd pool → pit stop)
        r2b = await client.post("/api/admin/advance-round", json={})
        assert r2b.json()["round"]["pit_stop"] is not None
        assert len(r2b.json()["round"]["pairings"]) == 2

        # Admin panel still renders
        admin = await client.get("/test-event/admin/test-admin-token")
        assert admin.status_code == 200
        assert "Round 2" in admin.text
