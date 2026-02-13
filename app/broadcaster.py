"""SSE broadcaster for real-time updates to all connected clients."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator


class Broadcaster:
    """In-process pub/sub using asyncio queues.

    Each connected client gets its own queue. When an event is broadcast,
    it is pushed to all subscriber queues.
    """

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[str]] = []

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Subscribe to events. Yields SSE-formatted strings."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            self._subscribers.remove(queue)

    async def broadcast(self, event: str, data: dict | str) -> None:
        """Broadcast an event to all subscribers.

        Args:
            event: SSE event name (e.g., "round_update", "timer_update").
            data: Event payload — dict is JSON-serialized, string sent as-is.
        """
        if isinstance(data, dict):
            payload = json.dumps(data)
        else:
            payload = data

        message = f"event: {event}\ndata: {payload}\n\n"

        dead_queues: list[asyncio.Queue[str]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        for queue in dead_queues:
            self._subscribers.remove(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Global broadcaster instance
broadcaster = Broadcaster()
