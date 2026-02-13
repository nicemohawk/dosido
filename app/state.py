"""Event state manager wrapping Redis for all read/write operations."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.config import settings
from app.matching import solve_round
from app.models import (
    Attendee,
    AttendeeStatus,
    EventState,
    EventStatus,
    Pairing,
    RoundResult,
)
from app.redis_client import get_redis
from app.scoring import make_pair_key


def _prefix() -> str:
    return f"event:{settings.event_slug}"


class EventStateManager:
    """Manages all event state in Redis."""

    # --- Event state ---

    async def get_state(self) -> EventState:
        r = get_redis()
        raw = await r.get(f"{_prefix()}:state")
        if raw:
            return EventState.model_validate_json(raw)
        return EventState(rounds_remaining=settings.total_rounds)

    async def set_state(self, state: EventState) -> None:
        r = get_redis()
        await r.set(f"{_prefix()}:state", state.model_dump_json())

    # --- Attendees ---

    async def get_attendee(self, attendee_id: str) -> Attendee | None:
        r = get_redis()
        raw = await r.hget(f"{_prefix()}:attendees", attendee_id)
        if raw:
            return Attendee.model_validate_json(raw)
        return None

    async def get_all_attendees(self) -> dict[str, Attendee]:
        r = get_redis()
        raw_map = await r.hgetall(f"{_prefix()}:attendees")
        return {
            aid: Attendee.model_validate_json(data)
            for aid, data in raw_map.items()
        }

    async def save_attendee(self, attendee: Attendee) -> None:
        r = get_redis()
        await r.hset(
            f"{_prefix()}:attendees", attendee.id, attendee.model_dump_json()
        )

    async def get_active_pool(self) -> list[Attendee]:
        r = get_redis()
        active_ids = await r.smembers(f"{_prefix()}:pool:active")
        if not active_ids:
            return []
        attendees = await self.get_all_attendees()
        return [attendees[aid] for aid in active_ids if aid in attendees]

    # --- Check-in / Check-out ---

    async def check_in(self, attendee_id: str) -> Attendee | None:
        attendee = await self.get_attendee(attendee_id)
        if not attendee:
            return None

        attendee.status = AttendeeStatus.CHECKED_IN
        await self.save_attendee(attendee)

        r = get_redis()
        await r.sadd(f"{_prefix()}:pool:active", attendee_id)
        await r.srem(f"{_prefix()}:pool:departed", attendee_id)
        return attendee

    async def check_out(self, attendee_id: str) -> Attendee | None:
        attendee = await self.get_attendee(attendee_id)
        if not attendee:
            return None

        attendee.status = AttendeeStatus.DEPARTED
        await self.save_attendee(attendee)

        r = get_redis()
        await r.srem(f"{_prefix()}:pool:active", attendee_id)
        await r.sadd(f"{_prefix()}:pool:departed", attendee_id)
        return attendee

    # --- Compatibility matrix ---

    async def get_compatibility_matrix(self) -> dict[str, dict]:
        r = get_redis()
        raw_map = await r.hgetall(f"{_prefix()}:matrix")
        return {key: json.loads(data) for key, data in raw_map.items()}

    async def set_pair_score(
        self, id_a: str, id_b: str, score_data: dict
    ) -> None:
        r = get_redis()
        pair_key = make_pair_key(id_a, id_b)
        await r.hset(f"{_prefix()}:matrix", pair_key, json.dumps(score_data))

    # --- Pairing history ---

    async def get_pairing_history(self) -> set[str]:
        r = get_redis()
        return await r.smembers(f"{_prefix()}:history")

    async def add_to_history(self, pair_key: str) -> None:
        r = get_redis()
        await r.sadd(f"{_prefix()}:history", pair_key)

    # --- Pit stop counts ---

    async def get_pit_stop_counts(self) -> dict[str, int]:
        r = get_redis()
        raw = await r.hgetall(f"{_prefix()}:pit_stops")
        return {k: int(v) for k, v in raw.items()}

    async def increment_pit_stop(self, attendee_id: str) -> None:
        r = get_redis()
        await r.hincrby(f"{_prefix()}:pit_stops", attendee_id, 1)

    # --- Current pairings ---

    async def get_current_pairings(self) -> RoundResult | None:
        r = get_redis()
        raw = await r.get(f"{_prefix()}:current_pairings")
        if raw:
            return RoundResult.model_validate_json(raw)
        return None

    async def set_current_pairings(self, result: RoundResult) -> None:
        r = get_redis()
        await r.set(f"{_prefix()}:current_pairings", result.model_dump_json())
        # Also store by round number for history
        await r.set(
            f"{_prefix()}:round:{result.round_number}:pairings",
            result.model_dump_json(),
        )

    # --- Round management ---

    async def advance_round(self) -> RoundResult:
        """Record current history, solve next round, update state."""
        state = await self.get_state()

        # Record current round's pairings into history
        current = await self.get_current_pairings()
        if current:
            for pairing in current.pairings:
                pair_key = make_pair_key(pairing.attendee_a, pairing.attendee_b)
                await self.add_to_history(pair_key)

        # Load all data needed for solver
        active_pool = await self.get_active_pool()
        matrix = await self.get_compatibility_matrix()
        history = await self.get_pairing_history()
        pit_stop_counts = await self.get_pit_stop_counts()
        signals = await self.get_all_signals_as_map()

        # Solve
        pairings, pit_stop_id = solve_round(
            active_pool=active_pool,
            compatibility_matrix=matrix,
            pairing_history=history,
            rounds_remaining=state.rounds_remaining,
            pit_stop_counts=pit_stop_counts,
            mutual_signals=signals if signals else None,
        )

        # Update pit stop counts
        if pit_stop_id:
            await self.increment_pit_stop(pit_stop_id)

        # Build round result
        avg_score = (
            sum(p.composite_score for p in pairings) / len(pairings)
            if pairings
            else 0.0
        )

        state.round_number += 1
        state.rounds_remaining -= 1
        state.status = EventStatus.ROUND_ACTIVE
        timer_end = datetime.now(timezone.utc).timestamp() + (
            settings.round_duration_minutes * 60
        )
        state.timer_end = datetime.fromtimestamp(
            timer_end, tz=timezone.utc
        ).isoformat()
        state.timer_paused = False
        state.timer_remaining = None

        result = RoundResult(
            round_number=state.round_number,
            pairings=pairings,
            pit_stop=pit_stop_id,
            average_score=round(avg_score, 1),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        await self.set_state(state)
        await self.set_current_pairings(result)

        return result

    async def pause_timer(self) -> EventState:
        state = await self.get_state()
        if state.timer_end and not state.timer_paused:
            now = datetime.now(timezone.utc).timestamp()
            end = datetime.fromisoformat(state.timer_end).timestamp()
            remaining = max(0, int(end - now))
            state.timer_paused = True
            state.timer_remaining = remaining
            state.timer_end = None
            await self.set_state(state)
        return state

    async def resume_timer(self) -> EventState:
        state = await self.get_state()
        if state.timer_paused and state.timer_remaining is not None:
            timer_end = datetime.now(timezone.utc).timestamp() + state.timer_remaining
            state.timer_end = datetime.fromtimestamp(
                timer_end, tz=timezone.utc
            ).isoformat()
            state.timer_paused = False
            state.timer_remaining = None
            await self.set_state(state)
        return state

    # --- Swap override ---

    async def swap_pairing(
        self, attendee_id_1: str, attendee_id_2: str
    ) -> RoundResult | None:
        """Swap two attendees in the current round's pairings."""
        result = await self.get_current_pairings()
        if not result:
            return None

        # Find which pairings contain these attendees
        idx_1 = idx_2 = None
        for i, p in enumerate(result.pairings):
            if p.attendee_a == attendee_id_1 or p.attendee_b == attendee_id_1:
                idx_1 = i
            if p.attendee_a == attendee_id_2 or p.attendee_b == attendee_id_2:
                idx_2 = i

        if idx_1 is None or idx_2 is None or idx_1 == idx_2:
            return result  # Can't swap — not found or same table

        p1 = result.pairings[idx_1]
        p2 = result.pairings[idx_2]

        # Identify the partners (the ones NOT being swapped)
        partner_1 = p1.attendee_b if p1.attendee_a == attendee_id_1 else p1.attendee_a
        partner_2 = p2.attendee_b if p2.attendee_a == attendee_id_2 else p2.attendee_a

        # Swap: attendee_1 goes with partner_2, attendee_2 goes with partner_1
        result.pairings[idx_1] = Pairing(
            table_number=p1.table_number,
            attendee_a=min(attendee_id_2, partner_1),
            attendee_b=max(attendee_id_2, partner_1),
            composite_score=0,  # Score no longer meaningful after manual swap
        )
        result.pairings[idx_2] = Pairing(
            table_number=p2.table_number,
            attendee_a=min(attendee_id_1, partner_2),
            attendee_b=max(attendee_id_1, partner_2),
            composite_score=0,
        )

        await self.set_current_pairings(result)
        return result

    # --- Walk-up badges ---

    async def get_available_walkup_badges(self) -> list[dict]:
        r = get_redis()
        raw = await r.hgetall(f"{_prefix()}:walkup_badges")
        badges = []
        for slug, data in raw.items():
            badge = json.loads(data)
            if not badge.get("assigned"):
                badges.append({"slug": slug, **badge})
        return badges

    async def assign_walkup_badge(
        self, slug: str, attendee_id: str
    ) -> str | None:
        """Assign a walk-up badge to an attendee. Returns the badge's token."""
        r = get_redis()
        raw = await r.hget(f"{_prefix()}:walkup_badges", slug)
        if not raw:
            return None
        badge = json.loads(raw)
        badge["assigned"] = True
        badge["attendee_id"] = attendee_id
        await r.hset(f"{_prefix()}:walkup_badges", slug, json.dumps(badge))

        # Register the token → attendee mapping
        await r.hset(f"{_prefix()}:tokens", badge["token"], attendee_id)

        return badge["token"]

    # --- Token lookups ---

    async def get_attendee_by_token(self, token: str) -> Attendee | None:
        r = get_redis()
        attendee_id = await r.hget(f"{_prefix()}:tokens", token)
        if not attendee_id:
            return None
        return await self.get_attendee(attendee_id)

    # --- Signals ---

    async def record_signal(
        self, round_number: int, from_id: str, to_id: str
    ) -> bool:
        """Record a signal and check for mutual match. Returns True if mutual."""
        r = get_redis()
        await r.hset(f"{_prefix()}:signals:{round_number}", from_id, to_id)

        # Check for mutual match
        reverse = await r.hget(
            f"{_prefix()}:signals:{round_number}", to_id
        )
        if reverse == from_id:
            pair_key = make_pair_key(from_id, to_id)
            await r.sadd(f"{_prefix()}:mutual_matches", pair_key)
            return True
        return False

    async def get_mutual_matches(self) -> set[str]:
        r = get_redis()
        return await r.smembers(f"{_prefix()}:mutual_matches")

    async def get_signals_for_round(self, round_number: int) -> dict[str, str]:
        r = get_redis()
        return await r.hgetall(f"{_prefix()}:signals:{round_number}")

    async def get_all_signals_as_map(self) -> dict[str, list[str]]:
        """Get all signals across all rounds as {from_id: [to_id, ...]}."""
        state = await self.get_state()
        result: dict[str, list[str]] = {}
        r = get_redis()
        for rnd in range(1, state.round_number + 1):
            signals = await r.hgetall(f"{_prefix()}:signals:{rnd}")
            for from_id, to_id in signals.items():
                result.setdefault(from_id, []).append(to_id)
        return result

    # --- Pool counts ---

    async def get_pool_counts(self) -> dict[str, int]:
        r = get_redis()
        active = await r.scard(f"{_prefix()}:pool:active")
        departed = await r.scard(f"{_prefix()}:pool:departed")
        total = await r.hlen(f"{_prefix()}:attendees")
        return {
            "active": active,
            "departed": departed,
            "not_arrived": total - active - departed,
            "total": total,
        }

    # --- Scoring queue (walk-up backfill) ---

    async def enqueue_scoring(self, pair_key: str) -> None:
        r = get_redis()
        await r.rpush(f"{_prefix()}:scoring_queue", pair_key)

    async def dequeue_scoring(self) -> str | None:
        r = get_redis()
        return await r.lpop(f"{_prefix()}:scoring_queue")

    async def scoring_queue_length(self) -> int:
        r = get_redis()
        return await r.llen(f"{_prefix()}:scoring_queue")


# Global instance
state_manager = EventStateManager()
