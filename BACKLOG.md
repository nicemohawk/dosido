# Backlog

Improvement ideas and tech debt discovered during development. Pick these up when relevant or when the user asks. Remove items as they're completed.

## Unfinished Features (per README spec)

- [ ] **Mutual board never shown on projector** — `mutual_board.html` template exists and `OPEN_NETWORKING` status is defined, but nothing transitions to it. Need: admin "End Event / Open Networking" button, a view route that renders the mutual board on screen, and SSE event to trigger the transition. Currently mutual matches only visible on individual phones.
- [ ] **No automatic between-rounds state transition** — `BETWEEN_ROUNDS` status exists but is only set during `undo_last_round()`. When the timer hits zero, nothing happens server-side. Need: timer expiry should transition state to `BETWEEN_ROUNDS` (either server-side via background task or client-triggered), which would enable showing the signal prompt automatically and updating the projector.
- [ ] **Admin panel has no contextual help text** — README claims "every section has contextual help text" and "zero training" for ops volunteers. No tooltips, workflow hints, or explanatory text exist. Key gaps: what "Pit Stop" means, suggested check-in workflow, what signals do, when to use swap override.
- [ ] **LinkedIn scraping silently fails** — `enrich.py` attempts unauthenticated LinkedIn scrapes that are always blocked by authwall. Falls back gracefully to application data, but README presents it as a working feature. Either document the limitation or remove the scraping claim.

## Unfinished Features (per build spec)

- [ ] **"NEXT ROUND STARTING..." interstitial on projector** — Spec calls for a 5-second countdown overlay on the screen view before revealing new pairings. Currently the screen reloads directly on `round_update` with no transition.
- [ ] **Polling fallback for SSE drops** — Screen view should poll every 5 seconds and admin view every 15 seconds as a backup when SSE connection is lost. Other views (mobile) don't need polling — SSE reconnection is sufficient.
- [ ] **Clarify signal window dynamics** — Signal submissions have no round validation. A signal from a previous round could be submitted after the next round starts. Need to define and enforce when the signal window opens and closes relative to round transitions.
- [ ] **Review solver constraints — commitment and location as hard constraints** — Spec says commitments should be a hard constraint (must be paired). Currently only "arrangement" is enforced as hard. Location/colocated is also likely a hard constraint. Audit `solver.py` and confirm which constraints should be hard vs. soft (score bonus).

## Bugs

- [ ] **`advance_round` endpoint has no try/catch** — solver exception leaves state half-updated (round incremented, no pairings stored). Wrap in try/catch with rollback. (`admin_api.py:92`)
- [ ] **Backfill worker crashes on unexpected API response** — `response.content[0].text` assumed without bounds check. Same pattern in `enrich.py:79` and `score_pairs.py:103`. (`backfill_worker.py:103`)
- [ ] **Advance-round button gives no error feedback** — `hx-swap="none"` means admin sees nothing if solver fails mid-event. (`admin_round_control.html:29`)

## UX

- [ ] **Screen/mobile white flash on round change** — `location.reload()` causes visible flicker on projector. Replace with HTMX partial swaps for smooth transition. (`screen.html`, `mobile.html`)
- [ ] **No "scoring in progress" indicator for walk-ups** — admin can't tell if LLM backfill is running or stuck. Scores jump unexpectedly when backfill completes.
- [ ] **No accessibility for live updates** — only `connection-status` has `aria-live`. Screen reader users miss timer, match assignments, and signal results. Admin tabs lack `role="tab"`, `aria-selected`, and `role="tabpanel"` attributes. (`base.html:20`, `admin.html`)
- [ ] **Admin pool filter resets on tab switch** — search term lost when switching tabs or on checkin_update refresh. (`admin.html:83`)

## Tech Debt

- [ ] **Starlette `TemplateResponse` deprecation** — migrate from `TemplateResponse(name, {"request": request})` to `TemplateResponse(request, name)`. Affects all view endpoints.
- [ ] **`views.py` is ~330 lines** — split admin partial endpoints into their own router file.
- [ ] **Backfill worker has no health check** — if Redis connection dies silently, worker keeps polling forever and misses all walk-up scoring. (`backfill_worker.py:47`)
- [ ] **Redis connection pool has no reconnect logic** — long-running processes can get stale connections. (`redis_client.py`)
- [ ] **No client-side error logging in SSE** — network failures invisible in browser dev tools. (`sse.js`)
- [x] **CI only runs tests, no lint/format** — added ruff check + format to CI and pre-commit hooks

## Improvements

- [ ] **Pipeline scripts don't validate intermediate files** — `load_to_redis.py` and `enrich.py` crash with unhelpful errors if `data/*.json` files are missing.
- [ ] **Timer assumes UTC everywhere** — server uses `datetime.now(timezone.utc)` but no explicit timezone context passed to client templates. Could drift if deployed with non-UTC system clock. (`state.py:198`)
- [ ] **No CORS configured** — not needed today, but blocks future external API consumers. (`main.py`)
- [ ] **`.env.example` doesn't document LLM fallback behavior** — unclear what happens if `LLM_PROVIDER=claude` but no API key is set.

## Docs

- [ ] **No operational runbook** — README covers architecture but not "what if round advance fails?" or "how to recover stuck backfill worker?" scenarios.

## Future Additions

- [ ] **Bell/chime sound at timer zero** — Spec mentions an audible alert when the round timer expires. Nice-to-have for in-person events so attendees know time is up without watching the screen.
- [ ] **Post-event data export** — Export all pairings + scores + mutual signals as CSV for follow-up nudge emails ("You matched with 3 people — here are their LinkedIn profiles").
- [ ] **Multi-event learning** — If this runs again, use outcome data (which pairs actually met again) to fine-tune scoring prompts.
