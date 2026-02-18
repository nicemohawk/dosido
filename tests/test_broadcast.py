"""Tests that admin/signal actions broadcast the correct SSE events."""

from __future__ import annotations

import pytest

from tests.conftest import check_in_all, seed_attendees, seed_matrix

pytestmark = pytest.mark.asyncio


class TestCheckInBroadcast:
    async def test_checkin_broadcasts_checkin_update(self, client, fake_redis, broadcast_spy):
        attendees = await seed_attendees(fake_redis, count=2)

        await client.post(
            "/api/admin/check-in",
            json={"attendee_id": attendees[0]["id"], "action": "check-in"},
        )

        assert len(broadcast_spy) == 1
        event = broadcast_spy[0]
        assert event["event"] == "checkin_update"
        assert event["data"]["attendee_id"] == attendees[0]["id"]
        assert event["data"]["action"] == "check-in"
        assert event["data"]["pool"]["active"] == 1

    async def test_checkout_broadcasts_checkin_update(self, client, fake_redis, broadcast_spy):
        attendees = await seed_attendees(fake_redis, count=2)
        await check_in_all(client, attendees)
        broadcast_spy.clear()

        await client.post(
            "/api/admin/check-in",
            json={"attendee_id": attendees[0]["id"], "action": "check-out"},
        )

        assert len(broadcast_spy) == 1
        event = broadcast_spy[0]
        assert event["event"] == "checkin_update"
        assert event["data"]["action"] == "check-out"
        assert event["data"]["pool"]["departed"] == 1


class TestRoundBroadcast:
    async def test_advance_round_broadcasts_round_update(self, client, fake_redis, broadcast_spy):
        attendees = await seed_attendees(fake_redis, count=6)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        broadcast_spy.clear()

        await client.post("/api/admin/advance-round", json={})

        round_events = [e for e in broadcast_spy if e["event"] == "round_update"]
        assert len(round_events) == 1
        data = round_events[0]["data"]
        assert data["round_number"] == 1
        assert isinstance(data["pairings"], list)
        assert len(data["pairings"]) == 3
        assert data["timer_end"] is not None

    async def test_undo_round_broadcasts_round_update(self, client, fake_redis, broadcast_spy):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})
        broadcast_spy.clear()

        await client.post("/api/admin/undo-round", json={})

        round_events = [e for e in broadcast_spy if e["event"] == "round_update"]
        assert len(round_events) == 1
        data = round_events[0]["data"]
        assert data["undone"] is True
        assert data["round_number"] == 0
        assert data["pairings"] == []

    async def test_swap_broadcasts_round_update(self, client, fake_redis, broadcast_spy):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        r1 = await client.post("/api/admin/advance-round", json={})
        pairings = r1.json()["round"]["pairings"]
        broadcast_spy.clear()

        await client.post(
            "/api/admin/swap",
            json={
                "attendee_id_1": pairings[0]["attendee_a"],
                "attendee_id_2": pairings[1]["attendee_a"],
            },
        )

        round_events = [e for e in broadcast_spy if e["event"] == "round_update"]
        assert len(round_events) == 1
        assert isinstance(round_events[0]["data"]["pairings"], list)


class TestTimerBroadcast:
    async def test_pause_broadcasts_timer_update(self, client, fake_redis, broadcast_spy):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})
        broadcast_spy.clear()

        await client.post("/api/admin/pause", json={"action": "pause"})

        timer_events = [e for e in broadcast_spy if e["event"] == "timer_update"]
        assert len(timer_events) == 1
        data = timer_events[0]["data"]
        assert data["action"] == "pause"
        assert "timer_remaining" in data

    async def test_resume_broadcasts_timer_update(self, client, fake_redis, broadcast_spy):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})
        await client.post("/api/admin/pause", json={"action": "pause"})
        broadcast_spy.clear()

        await client.post("/api/admin/pause", json={"action": "resume"})

        timer_events = [e for e in broadcast_spy if e["event"] == "timer_update"]
        assert len(timer_events) == 1
        data = timer_events[0]["data"]
        assert data["action"] == "resume"
        assert "timer_end" in data


class TestWalkUpBroadcast:
    async def test_walkup_broadcasts_checkin_update(self, client, fake_redis, broadcast_spy):
        await seed_attendees(fake_redis, count=1)
        broadcast_spy.clear()

        await client.post(
            "/api/admin/walk-up",
            json={
                "name": "Walk-Up Person",
                "lane": "flexible",
                "role": "engineering",
                "role_needed": "product",
                "top_climate_area": "energy",
            },
        )

        checkin_events = [e for e in broadcast_spy if e["event"] == "checkin_update"]
        assert len(checkin_events) == 1
        data = checkin_events[0]["data"]
        assert data["action"] == "walk-up"
        assert data["name"] == "Walk-Up Person"
        assert data["pool"]["active"] == 1


class TestSignalBroadcast:
    async def test_signal_broadcasts_signal_update(self, client, fake_redis, broadcast_spy):
        attendees = await seed_attendees(fake_redis, count=4)
        await seed_matrix(fake_redis, attendees)
        await check_in_all(client, attendees)
        await client.post("/api/admin/advance-round", json={})
        broadcast_spy.clear()

        await client.post(
            "/api/signal",
            json={
                "from_attendee": attendees[0]["id"],
                "to_attendee": attendees[1]["id"],
                "round_number": 1,
            },
        )

        signal_events = [e for e in broadcast_spy if e["event"] == "signal_update"]
        assert len(signal_events) == 1
        data = signal_events[0]["data"]
        assert "mutual" in data
        assert data["attendee_a"]["id"] == attendees[0]["id"]
        assert data["attendee_b"]["id"] == attendees[1]["id"]
