"""Load pipeline output (attendees + matrix) into Redis."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import redis.asyncio as aioredis


async def load_data(
    attendees_path: str = "data/enriched_attendees.json",
    matrix_path: str = "data/matrix.json",
    walkup_badges_path: str = "data/walkup_badges.json",
    redis_url: str = "redis://localhost:6379",
    event_slug: str = "climate-week-2026",
) -> None:
    """Load all pre-event data into Redis."""
    prefix = f"event:{event_slug}"

    r = aioredis.from_url(redis_url, decode_responses=True)

    # Load attendees
    with open(attendees_path) as f:
        attendees = json.load(f)

    print(f"Loading {len(attendees)} attendees...")
    pipe = r.pipeline()
    for att in attendees:
        att_id = att["id"]
        att.setdefault("status", "not-arrived")
        att.setdefault("source", "application")
        att.setdefault("has_full_scoring", True)
        att.setdefault("pit_stop_count", 0)
        pipe.hset(f"{prefix}:attendees", att_id, json.dumps(att))
        # Map token → attendee ID
        if att.get("token"):
            pipe.hset(f"{prefix}:tokens", att["token"], att_id)
    await pipe.execute()
    print(f"  Loaded {len(attendees)} attendees")

    # Load compatibility matrix
    with open(matrix_path) as f:
        matrix = json.load(f)

    print(f"Loading {len(matrix)} pair scores...")
    pipe = r.pipeline()
    for pair_key, score_data in matrix.items():
        pipe.hset(f"{prefix}:matrix", pair_key, json.dumps(score_data))
    await pipe.execute()
    print(f"  Loaded {len(matrix)} pair scores")

    # Load walk-up badges (if file exists)
    try:
        with open(walkup_badges_path) as f:
            walkup_badges = json.load(f)

        print(f"Loading {len(walkup_badges)} walk-up badges...")
        pipe = r.pipeline()
        for badge in walkup_badges:
            pipe.hset(
                f"{prefix}:walkup_badges",
                badge["slug"],
                json.dumps({"token": badge["token"], "assigned": False}),
            )
        await pipe.execute()
        print(f"  Loaded {len(walkup_badges)} walk-up badges")
    except FileNotFoundError:
        print("  No walk-up badges file found, skipping")

    # Initialize event state
    from app.config import settings

    state = {
        "roundNumber": 0,
        "roundsRemaining": settings.total_rounds,
        "status": "pre-event",
        "timerEnd": None,
        "timerPaused": False,
        "timerRemaining": None,
    }
    await r.set(f"{prefix}:state", json.dumps(state))

    # Set config
    config = {
        "roundDuration": settings.round_duration_minutes,
        "totalRounds": settings.total_rounds,
        "adminToken": settings.admin_token,
        "eventName": settings.event_name,
    }
    await r.set(f"{prefix}:config", json.dumps(config))

    print("Event state initialized")
    await r.aclose()


async def _check_existing(redis_url: str, event_slug: str) -> bool:
    """Check if event data already exists in Redis. Returns True if safe to proceed."""
    from app.config import settings

    prefix = f"event:{event_slug}"
    r = aioredis.from_url(redis_url, decode_responses=True)
    count = await r.hlen(f"{prefix}:attendees")
    await r.aclose()

    if count == 0:
        return True

    print(f"Found {count} existing attendees in Redis for '{event_slug}'.")
    print("  [w] Wipe existing data and reload")
    print("  [r] Run anyway (overwrite/merge)")
    print("  [x] Exit")
    choice = input("  > ").strip().lower()

    if choice == "w":
        r = aioredis.from_url(redis_url, decode_responses=True)
        keys = []
        async for key in r.scan_iter(f"{prefix}:*"):
            keys.append(key)
        if keys:
            await r.delete(*keys)
        await r.aclose()
        print(f"  Wiped {len(keys)} keys")
        return True
    elif choice == "r":
        return True
    else:
        print("  Exiting.")
        return False


def main():
    redis_url = sys.argv[1] if len(sys.argv) > 1 else "redis://localhost:6379"
    from app.config import settings

    if not asyncio.run(_check_existing(redis_url, settings.event_slug)):
        return
    asyncio.run(load_data(redis_url=redis_url))


if __name__ == "__main__":
    main()
