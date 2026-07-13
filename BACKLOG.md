# Backlog

Improvement ideas and tech debt discovered during development. Pick these up when relevant or when the user asks. Remove items as they're completed.

## Unfinished Features (per README spec)

- [ ] **Admin panel has no contextual help text** — README claims "every section has contextual help text" and "zero training" for ops volunteers. No tooltips, workflow hints, or explanatory text exist. Key gaps: what "Pit Stop" means, suggested check-in workflow, what signals do, when to use swap override.
- [ ] **LinkedIn scraping silently fails** — `enrich.py` attempts unauthenticated LinkedIn scrapes that are always blocked by authwall. Falls back gracefully to application data, but README presents it as a working feature. Either document the limitation or remove the scraping claim.

## Unfinished Features (per build spec)

- [ ] **Clarify signal window dynamics** — Signal submissions have no round validation. A signal from a previous round could be submitted after the next round starts. Need to define and enforce when the signal window opens and closes relative to round transitions.
- [ ] **Review solver constraints — commitment and location as hard constraints** — Spec says commitments should be a hard constraint (must be paired). Currently only "arrangement" is enforced as hard. Location/colocated is also likely a hard constraint. Audit `app/matching.py` and confirm which constraints should be hard vs. soft (score bonus).
- [ ] **Multiple simultaneous sit-outs are underreported** — `solve_round` now reports any unmatched attendee as the pit stop, but `RoundResult.pit_stop` holds a single ID. In the pathological case where several attendees have no valid partners left in the same round, only the first is surfaced. Consider making `pit_stop` a list end-to-end.

## Security

- [ ] **Admin API endpoints don't verify the admin token** — every `POST /api/admin/*` route (advance-round, open-networking, check-in, swap, etc.) is unauthenticated; the only gate is the unguessable admin panel URL. Anyone who learns the API paths can drive the event. Add a shared admin-token dependency across the admin router.

## UX

- [ ] **Mobile white flash on round change** — projector now covers the transition with the "NEXT ROUND STARTING…" interstitial, but `mobile.html` still does a bare `location.reload()`. Replace with an HTMX partial swap or a similar overlay.
- [ ] **Screen header stale during open networking** — the projector shows the mutual board but the header still reads "Round N of M". Cosmetic; swap to an "Open Networking" heading.
- [ ] **No "scoring in progress" indicator for walk-ups** — admin can't tell if LLM backfill is running or stuck. Scores jump unexpectedly when backfill completes.
- [ ] **No accessibility for live updates** — only `connection-status` has `aria-live`. Screen reader users miss timer, match assignments, and signal results. Admin tabs lack `role="tab"`, `aria-selected`, and `role="tabpanel"` attributes. (`base.html:20`, `admin.html`)
- [ ] **Admin pool filter resets on tab switch** — search term lost when switching tabs or on checkin_update refresh. (`admin.html:83`)

## Tech Debt

- [ ] **Starlette `TemplateResponse` deprecation** — migrate from `TemplateResponse(name, {"request": request})` to `TemplateResponse(request, name)`. Affects all view endpoints.
- [ ] **`views.py` is ~330 lines** — split admin partial endpoints into their own router file.
- [ ] **Backfill worker has no health check** — if Redis connection dies silently, worker keeps polling forever and misses all walk-up scoring. (`backfill_worker.py`)
- [ ] **Redis connection pool has no reconnect logic** — long-running processes can get stale connections. (`redis_client.py`)
- [ ] **`enrich.py` and `score_pairs.py` still assume `content[0].text`** — the backfill worker now guards empty/textless API responses, but the offline pipeline scripts keep the unguarded pattern (lower stakes: they run pre-event and are resumable).
- [x] **CI only runs tests, no lint/format** — added ruff check + format to CI and pre-commit hooks

## Improvements

- [ ] **Timer assumes UTC everywhere** — server uses `datetime.now(timezone.utc)` but no explicit timezone context passed to client templates. Could drift if deployed with non-UTC system clock. (`state.py`)
- [ ] **No CORS configured** — not needed today, but blocks future external API consumers. (`main.py`)
- [ ] **Resumability files traceback if present-but-malformed** — required pipeline inputs now fail helpfully, but an existing-but-corrupt `matrix.json` (score_pairs resume) or `enriched_attendees.json` (enrich resume) still raises raw JSON errors.

## Docs

- [ ] **No operational runbook** — README covers architecture but not "what if round advance fails?" or "how to recover stuck backfill worker?" scenarios.

## Research Follow-ups (from cofounder-complementarity research, 2026-07-13)

- [ ] **Signal budget + forced choice** — cap "strong yes" signals (3-4 per event) or make each round's signal a forced {strong yes / maybe / no}; scarcity makes signals informative (dyadic-desire research). Selectivity weighting is already in `_signal_boost`; the UI still allows unlimited signals.
- [ ] **"Would you spend a full day working with this person?"** — add as a post-round binary sub-question; a mutual yes is the strongest chemistry datum available (EF trial-project logic) and should outweigh the LLM score.
- [ ] **Decay the LLM prior as revealed signals accumulate** — by round 5+, signal-derived adjustments should be able to dominate the pre-scored matrix for pairs with data (stated preferences predict poorly; revealed interest predicts well).
- [ ] **Per-round escalating spark prompts** — sparks are generated once per pair at scoring time; research favors escalation across the event (early rounds concrete/low-stakes, late rounds the breakup topics: pivot conversation, mock equity negotiation). Needs round-aware spark selection.
- [ ] **Post-event follow-up kit** — convert mutual strong-yeses into a suggested next step (1-day trial task + YC's 10 questions / First Round's 50 questions); the 24-48h follow-up is where match value is realized.

## Future Additions

- [ ] **Bell/chime sound at timer zero** — Spec mentions an audible alert when the round timer expires. Nice-to-have for in-person events so attendees know time is up without watching the screen.
- [ ] **Post-event data export** — Export all pairings + scores + mutual signals as CSV for follow-up nudge emails ("You matched with 3 people — here are their LinkedIn profiles").
- [ ] **Multi-event learning** — If this runs again, use outcome data (which pairs actually met again) to fine-tune scoring prompts.

## Completed (2026-07-13)

- [x] Mutual board on projector via admin "Open Networking" button + `status_update` SSE
- [x] Automatic `BETWEEN_ROUNDS` transition on timer expiry (`app/round_monitor.py` background task)
- [x] "NEXT ROUND STARTING…" interstitial on projector (survives reload via sessionStorage)
- [x] Polling fallback for SSE drops (screen 5s, admin 15s) + client-side SSE error logging
- [x] `advance_round` atomicity — no Redis writes until the solve succeeds; endpoint returns clear 500
- [x] Advance-round (and all admin action) error feedback via inline alert
- [x] Backfill worker guards empty/textless API responses; reuses fenced-JSON parser
- [x] Pipeline input validation with actionable errors; `.env.example` documents all settings + LLM fallback
- [x] Dead lookahead removed from solver (6× faster round advance); solver-chosen pit stop; heuristic 0-100 fallback scoring
