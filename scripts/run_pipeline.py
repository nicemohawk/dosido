"""Orchestrate the full pre-event pipeline.

Usage:
    python -m scripts.run_pipeline               # Seed test data + load to Redis
    python -m scripts.run_pipeline --csv <path>   # Full pipeline from Luma CSV
    python -m scripts.run_pipeline --seed-only    # Just generate test data (no Redis)
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def main():
    parser = argparse.ArgumentParser(description="Run the pre-event pipeline")
    parser.add_argument("--csv", help="Path to Luma CSV export")
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only generate test data, don't load to Redis",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=60,
        help="Number of fake attendees to generate (default: 60)",
    )
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="Skip LLM enrichment step (use for testing)",
    )
    parser.add_argument(
        "--skip-score",
        action="store_true",
        help="Skip LLM pairwise scoring step (use for testing)",
    )
    parser.add_argument(
        "--badges",
        action="store_true",
        help="Generate badge PDFs after loading data",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for badge QR codes",
    )
    args = parser.parse_args()

    if args.csv:
        # Full pipeline from real CSV
        print("=== Step 1: Ingest CSV ===")
        from pipeline.ingest import ingest_csv
        ingest_csv(args.csv)

        if not args.skip_enrich:
            print("\n=== Step 2: LLM Enrichment ===")
            from pipeline.enrich import enrich_all
            enrich_all()
        else:
            print("\n=== Step 2: Skipping enrichment ===")
            # Copy attendees.json as enriched_attendees.json
            import json
            import shutil
            shutil.copy("data/attendees.json", "data/enriched_attendees.json")

        if not args.skip_score:
            print("\n=== Step 3: Pairwise Scoring (Batch API) ===")
            from pipeline.score_pairs import submit_batch
            submit_batch()
        else:
            print("\n=== Step 3: Skipping scoring — generating fake matrix ===")
            import json
            from scripts.seed_test_data import generate_matrix
            with open("data/enriched_attendees.json") as f:
                attendees = json.load(f)
            matrix = generate_matrix(attendees)
            with open("data/matrix.json", "w") as f:
                json.dump(matrix, f, indent=2)
            print(f"  Generated {len(matrix)} fake pair scores")

    else:
        # Generate test data
        print("=== Generating test data ===")
        from scripts.seed_test_data import seed
        seed(attendee_count=args.count)

    if args.seed_only:
        print("\n=== Done (seed only, no Redis load) ===")
        return

    # Load to Redis
    print("\n=== Loading to Redis ===")
    from pipeline.load_to_redis import load_data
    asyncio.run(load_data())

    # Generate badges if requested
    if args.badges:
        print("\n=== Generating badge PDFs ===")
        from pipeline.generate_badges import (
            generate_attendee_badges,
            generate_walkup_badges,
        )
        slug = "climate-week-2026"  # from settings
        generate_attendee_badges(base_url=args.base_url, event_slug=slug)
        generate_walkup_badges(base_url=args.base_url, event_slug=slug)

    print("\n=== Pipeline complete! ===")
    print("Start the server: .venv/bin/uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
