"""Shared test fixtures — fakeredis, test client, attendee seeding."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.models import Attendee, AttendeeSource, AttendeeStatus
from app.scoring import make_pair_key


@pytest.fixture(autouse=True)
def _test_settings():
    """Ensure test-safe settings for every test."""
    original_slug = settings.event_slug
    original_key = settings.anthropic_api_key
    settings.event_slug = "test-event"
    settings.anthropic_api_key = ""
    settings.admin_token = "test-admin-token"
    yield
    settings.event_slug = original_slug
    settings.anthropic_api_key = original_key


@pytest.fixture
def fake_redis():
    """Fresh fakeredis instance per test."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest_asyncio.fixture
async def client(fake_redis):
    """FastAPI async test client backed by fakeredis."""
    with (
        patch("app.state.get_redis", return_value=fake_redis),
        patch("app.redis_client.get_redis", return_value=fake_redis),
        patch("app.redis_client.close_pool", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    await fake_redis.flushall()


async def seed_attendees(fake_redis, count: int = 6) -> list[dict]:
    """Seed attendees into fakeredis. Returns list of attendee dicts."""
    prefix = f"event:{settings.event_slug}"
    attendees = []

    for i in range(count):
        att = Attendee(
            id=f"att-{i:03d}",
            name=f"Test Person {i}",
            email=f"person{i}@test.com",
            lane="idea" if i % 2 == 0 else "joiner",
            role="engineering" if i % 3 == 0 else "product",
            role_needed="product" if i % 3 == 0 else "engineering",
            climate_areas=["energy", "agriculture"],
            top_climate_area="energy",
            commitment="full-time",
            arrangement="remote-open",
            location="SF",
            status=AttendeeStatus.NOT_ARRIVED,
            source=AttendeeSource.APPLICATION,
        )
        await fake_redis.hset(f"{prefix}:attendees", att.id, att.model_dump_json())
        attendees.append({"id": att.id, "name": att.name})

    return attendees


async def seed_matrix(fake_redis, attendees: list[dict], base_score: int = 65):
    """Seed a compatibility matrix for all pairs."""
    prefix = f"event:{settings.event_slug}"

    for i, a in enumerate(attendees):
        for b in attendees[i + 1 :]:
            pair_key = make_pair_key(a["id"], b["id"])
            score_data = {
                "score": base_score + (hash(pair_key) % 20),
                "rationale": "Test pairing",
                "spark": "Test topic",
            }
            await fake_redis.hset(f"{prefix}:matrix", pair_key, json.dumps(score_data))


async def check_in_all(client: AsyncClient, attendees: list[dict]):
    """Check in all attendees via the API."""
    for att in attendees:
        resp = await client.post(
            "/api/admin/check-in",
            json={"attendee_id": att["id"], "action": "check-in"},
        )
        assert resp.status_code == 200
