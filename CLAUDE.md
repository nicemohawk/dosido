# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Real-time cofounder matchmaking system for structured networking events (~40-80 attendees, ~10 rounds). Server-rendered FastAPI + HTMX + SSE. Redis for all state. NetworkX max-weight matching solver with multi-round lookahead.

## Commands

```bash
# Install
pip install -e ".[dev]"

# Dev server (requires Redis running locally)
fm-serve                    # uvicorn with auto-reload on :8000

# Pre-event data pipeline
fm-seed                     # Generate 60 fake attendees + matrix
fm-load                     # Load seed data into Redis
python scripts/run_pipeline.py --csv path/to/luma.csv  # Full real pipeline

# Tests
pytest tests/               # All tests (needs fakeredis, no real Redis required)
pytest tests/test_matching.py::TestMatchScore  # Single test class
pytest tests/test_api.py -k test_health  # Single test by name

# CI runs: pytest tests/ -q (with Redis 7 service container)
```

## Architecture

**Stack:** FastAPI, Jinja2 templates, HTMX, Tailwind (CDN), SSE via asyncio queues, Redis (async), NetworkX solver, Anthropic Claude API.

**Key data flow — round advance:**

1. Admin POST `/api/admin/advance-round`
2. `EventStateManager.advance_round()` records history → loads pool/matrix → calls `solve_round()` → saves pairings to Redis → updates state
3. `broadcaster.broadcast("round_update", ...)` pushes SSE to all connected clients
4. Clients receive SSE → admin does HTMX partial swaps, screen/mobile do `location.reload()`

**State is centralized in `EventStateManager`** (`app/state.py`) — all Redis operations go through this class. No direct Redis calls elsewhere in app code.

**Scoring** (`app/scoring.py:match_score`): LLM pairwise score (0-100) + deterministic bonuses (role complement +15, lane +10, climate overlap +5/+10, mutual signal +20). Hard constraints return -inf (already paired, colocated).

**Solver** (`app/matching.py:solve_round`): Solves all remaining rounds simultaneously via lookahead, returns only the first round's pairings. Handles odd pools via pit stop rotation.

**Pair keys are always canonical** — `make_pair_key(a, b)` sorts IDs so `abc:def` == `def:abc`.

## Key Patterns

- All modules use `from __future__ import annotations`
- Modern type hints (`dict[str, str]` not `Dict`)
- Pydantic models as pure data containers, enums as `StrEnum`
- Redis keys prefixed `event:{slug}:` (hashes for attendees/matrix, sets for pool/history, strings for state)
- Router registration order matters: API routes before view routes (views use catch-all `{slug}` patterns)
- SSE client (`sse.js`) dispatches `CustomEvent("sse:<name>")` on `document.body`; views listen with `addEventListener`
- Admin partials in `templates/partials/` are swapped via HTMX on SSE events
- All HTML responses include `Cache-Control: no-store` to prevent stale HTMX partial fetches
- Background backfill worker (`app/backfill_worker.py`) runs in lifespan, rate-limited at 15 calls/min

## Code Quality

- Use human readable variable and function naming, not abbreviations or not-well-known acronyms. (`largeString` not `lgStr`; `tempNumber` not `a`; `urlSlug` is okay, `eicString` isn't)
- Strive for thin diffs and file lengths that are <300 lines
- Don't add in-line comments unless they add meaningful self documentation. Better: use naming and decomposition to self-document the code.
- Make sure you don't reimplement functionality already implemented within the app. If it's been implemented already, refactor the implementation into a generalized location
- Keep README up to date with changes at all times, including deploy instructions and comprehensive development environment quick start and testing instructions.
- Keep the test suite up to date with new funcitonality
- Write modern, idiomatic code at all times
- Branch and make pull requests using a `{type}/claude-{branch}` branching strategy
- Never work on the `main`/`master` branch. Make clean commits locally, then check before pushing to remote.

## Configuration

Settings via Pydantic `BaseSettings` in `app/config.py`, loaded from `.env`. Key vars: `REDIS_URL`, `ADMIN_TOKEN`, `ANTHROPIC_API_KEY`, `EVENT_SLUG`, `LLM_PROVIDER` (claude/ollama/none).

## Views

- `/{slug}/screen` — Projector (pairings grid + timer)
- `/{slug}/a/{token}` — Badge QR (public profile card or personal view if claimed)
- `/{slug}` — General mobile (pairing list + search)
- `/{slug}/admin/{token}` — Admin panel (check-in, round control, swaps, walk-ups, signals)
