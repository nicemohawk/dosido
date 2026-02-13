# Cofounder Matchmaking

Real-time cofounder matchmaking system for structured networking events. Pre-computes pairwise compatibility via LLM scoring, dynamically assigns optimal pairings each round using maximum weight matching, and displays results live on a projector screen and attendees' phones.

Built for SF Climate Week 2026 (40-80 attendees, ~10 rounds of 8-minute conversations).

## How It Works

1. **Pre-event**: Ingest attendee applications from Luma CSV, enrich profiles with Claude, score all pairs via Claude Batch API
2. **Event day**: Admin checks in attendees, starts rounds. The solver assigns optimal pairings (no repeats, fair pit stops for odd pools). Results display instantly on the projector and each attendee's phone
3. **Between rounds**: Attendees signal "want to follow up?" — mutual matches are revealed at open networking

## Architecture

```
FastAPI + Jinja2 + HTMX  →  Railway (persistent process)
         │
    Redis (state store)
         │
    networkx (max weight matching solver)
```

- **Server-rendered HTML** with HTMX for live updates via SSE — no JS framework, no build step
- **Tailwind CSS** via CDN
- **Badge QR codes** link each attendee to their personal mobile view (`/{slug}/a/{token}`)
- Walk-up attendees get fun-slug badges ("Pink Unicorn", "Curious Armadillo") with pre-generated QR codes

### Views

| URL | Purpose |
|-----|---------|
| `/{slug}/screen` | Projector — table grid, countdown timer, pit stop |
| `/{slug}/a/{token}` | Personal mobile — your match, table number, signal prompt |
| `/{slug}` | General mobile — full pairing list with name search/pin |
| `/{slug}/admin/{token}` | Admin panel — round control, check-in, walk-ups, swaps |

## Setup

### Prerequisites

- Python 3.12+
- Redis

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Configure

```bash
cp .env.example .env
# Edit .env with your Redis URL, Anthropic API key, admin token, etc.
```

### Seed test data (for development)

```bash
python scripts/seed_test_data.py
python scripts/run_pipeline.py --seed-only
```

This generates 60 fake attendees with a randomized compatibility matrix and loads them into Redis.

### Run

```bash
# Start Redis (if not already running)
brew services start redis  # macOS

# Start the server
uvicorn app.main:app --reload
```

Open:
- Admin: http://localhost:8000/climate-week-2026/admin/change-me-to-a-random-32-char-hex-string
- Screen: http://localhost:8000/climate-week-2026/screen
- Mobile: http://localhost:8000/climate-week-2026

## Pre-Event Pipeline

For a real event, run the full pipeline to process attendee applications:

```bash
# 1. Ingest Luma CSV export
python scripts/run_pipeline.py --csv path/to/luma_export.csv

# 2. Enrich profiles via Claude API (resumable)
python pipeline/enrich.py

# 3. Score all pairs via Claude Batch API (resumable)
python pipeline/score_pairs.py

# 4. Load everything to Redis
python pipeline/load_to_redis.py

# 5. Generate printable badge PDFs (Avery 5395 labels)
python scripts/run_pipeline.py --badges
```

### Badge System

- **Pre-registered attendees**: Name + QR code sticker badges, printed at home on Avery labels
- **Walk-up reserve**: ~20 badges with fun slugs + QR codes. Admin assigns a badge to each walk-up via the admin panel
- Walk-ups get deterministic-only scoring immediately; LLM scoring backfills between rounds

## Event Day Operations

The admin panel is designed so an ops volunteer can run the event with zero training. Every section has contextual help text.

### Typical flow

1. Lay out pre-printed badges alphabetically at check-in table
2. As attendees arrive and grab their badge, check them in via admin panel
3. When ready, click "Start Round 1" — solver assigns pairings in ~1 second
4. Projector shows table assignments, phones show individual matches
5. Timer counts down. Between rounds, attendees signal interest on their phones
6. Repeat for ~10 rounds
7. At open networking: mutual matches revealed on screen and phones

### Admin capabilities

- **Check in/out** attendees (included in next round's solver)
- **Start/pause/undo** rounds
- **Swap override** if two matched attendees already know each other
- **Add walk-ups** with a reserve badge assignment
- **Adjust settings** (round duration, total rounds) on the fly

## LLM Provider Config

The system supports three LLM providers, configured via `LLM_PROVIDER` in `.env`:

| Provider | Use case | Requires |
|----------|----------|----------|
| `claude` (default) | Production — highest quality enrichment and scoring | `ANTHROPIC_API_KEY` |
| `ollama` | Local dev — free, no API key, runs on your machine | [Ollama](https://ollama.com) + `ollama pull llama3.2` |
| `none` | Testing — stub enrichment from application data only | Nothing |

### Test profile script

Interactively test LinkedIn scraping and enrichment:

```bash
# Scrape a LinkedIn profile (see what data we can extract)
python scripts/test_profile.py https://linkedin.com/in/someone

# Scrape + enrich with Claude
python scripts/test_profile.py https://linkedin.com/in/someone --enrich

# Scrape + enrich with local Ollama (no API key needed)
python scripts/test_profile.py https://linkedin.com/in/someone --enrich --provider ollama

# Scrape + enrich with stub data (no LLM at all)
python scripts/test_profile.py --enrich --provider none
```

## Testing

```bash
pytest tests/
```

Tests cover:
- Matching engine correctness (no repeat pairings, hard constraints, pit stop fairness)
- Composite scoring function (LLM primary signal, deterministic bonuses, walk-up fallback)
- Full simulation: 60 attendees x 10 rounds, 80-attendee performance (<2s solve time)

## Deployment (Railway)

1. Create a Railway project with a Redis add-on
2. Set environment variables (see `.env.example`)
3. Deploy — Railway auto-detects the `Procfile`

```
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Project Structure

```
app/
  main.py              # FastAPI entry point + lifespan
  config.py            # Settings via pydantic-settings
  models.py            # Pydantic models (Attendee, PairScore, RoundResult, etc.)
  redis_client.py      # Async Redis connection pool
  state.py             # EventStateManager — all Redis read/write operations
  matching.py          # Solver (networkx max weight matching + lookahead)
  scoring.py           # Composite scoring function
  broadcaster.py       # SSE pub/sub via asyncio queues
  backfill_worker.py   # Background LLM scoring for walk-ups
  routes/
    views.py           # HTML page routes + admin partial endpoints
    admin_api.py       # POST routes: check-in, advance, pause, swap, walk-up
    public_api.py      # GET /api/state, SSE stream
    signal_api.py      # POST /api/signal, GET /api/mutual-matches
  templates/           # Jinja2 templates (base, admin, screen, mobile)
  static/js/           # Timer, search, connection status indicator

pipeline/
  ingest.py            # Luma CSV → normalized JSON
  enrich.py            # Per-attendee enrichment (Claude, Ollama, or stub)
  score_pairs.py       # Pairwise scoring via Claude Batch API
  load_to_redis.py     # Push profiles + matrix to Redis
  generate_badges.py   # Avery-label badge PDFs with QR codes
  fun_slugs.py         # Adjective + animal word lists for walk-up slugs
  prompts.py           # LLM prompt templates

scripts/
  seed_test_data.py    # Generate fake attendees + matrix for dev
  run_pipeline.py      # CLI orchestrator for the full pipeline
  test_profile.py      # Interactive LinkedIn scrape + enrichment tester

tests/
  test_matching.py     # Unit tests for scoring + matching
  test_simulation.py   # Integration tests (multi-round, performance)
```
