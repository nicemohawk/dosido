"""Tests for the round timer expiry monitor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.config import settings
from app.models import EventState, EventStatus
from app.round_monitor import end_round_if_expired, round_timer_has_expired


def make_state(
    status: EventStatus = EventStatus.ROUND_ACTIVE,
    timer_seconds_from_now: float | None = -5,
    timer_paused: bool = False,
) -> EventState:
    timer_end = None
    if timer_seconds_from_now is not None:
        end = datetime.now(timezone.utc) + timedelta(seconds=timer_seconds_from_now)
        timer_end = end.isoformat()
    return EventState(
        round_number=1,
        rounds_remaining=9,
        status=status,
        timer_end=timer_end,
        timer_paused=timer_paused,
    )


class TestRoundTimerHasExpired:
    def test_expired_active_round(self):
        assert round_timer_has_expired(make_state(timer_seconds_from_now=-5)) is True

    def test_timer_still_running(self):
        assert round_timer_has_expired(make_state(timer_seconds_from_now=120)) is False

    def test_paused_timer_never_expires(self):
        state = make_state(timer_seconds_from_now=-5, timer_paused=True)
        assert round_timer_has_expired(state) is False

    def test_no_timer_set(self):
        assert round_timer_has_expired(make_state(timer_seconds_from_now=None)) is False

    def test_only_active_rounds_expire(self):
        for status in (
            EventStatus.PRE_EVENT,
            EventStatus.BETWEEN_ROUNDS,
            EventStatus.OPEN_NETWORKING,
        ):
            state = make_state(status=status, timer_seconds_from_now=-5)
            assert round_timer_has_expired(state) is False

    def test_explicit_now_argument(self):
        state = make_state(timer_seconds_from_now=60)
        future = datetime.now(timezone.utc) + timedelta(seconds=120)
        assert round_timer_has_expired(state, now=future) is True


class TestEndRoundIfExpired:
    @pytest.mark.asyncio
    async def test_expired_round_transitions_and_broadcasts(self, fake_redis, broadcast_spy):
        prefix = f"event:{settings.event_slug}"
        state = make_state(timer_seconds_from_now=-5)
        await fake_redis.set(f"{prefix}:state", state.model_dump_json())

        with patch("app.state.get_redis", return_value=fake_redis):
            updated = await end_round_if_expired()

            assert updated is not None
            assert updated.status == EventStatus.BETWEEN_ROUNDS
            assert updated.timer_end is None

            saved = EventState.model_validate_json(await fake_redis.get(f"{prefix}:state"))
            assert saved.status == EventStatus.BETWEEN_ROUNDS

        assert broadcast_spy == [
            {
                "event": "status_update",
                "data": {"status": "between-rounds", "round_number": 1},
            }
        ]

    @pytest.mark.asyncio
    async def test_running_round_is_left_alone(self, fake_redis, broadcast_spy):
        prefix = f"event:{settings.event_slug}"
        state = make_state(timer_seconds_from_now=120)
        await fake_redis.set(f"{prefix}:state", state.model_dump_json())

        with patch("app.state.get_redis", return_value=fake_redis):
            assert await end_round_if_expired() is None

            saved = EventState.model_validate_json(await fake_redis.get(f"{prefix}:state"))
            assert saved.status == EventStatus.ROUND_ACTIVE

        assert broadcast_spy == []
