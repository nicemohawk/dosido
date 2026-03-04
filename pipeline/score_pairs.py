"""Pairwise compatibility scoring using Claude Batch API."""

from __future__ import annotations

import argparse
import json
import time
from itertools import combinations
from pathlib import Path

import anthropic

from app.config import settings
from pipeline.prompts import PAIRWISE_PROMPT


def generate_batch_requests(
    attendees: list[dict],
    existing_keys: set[str] | None = None,
) -> list[dict]:
    """Generate batch API request objects for all pairs.

    Skips pairs already present in existing_keys (resumability).
    """
    requests = []

    for a, b in combinations(attendees, 2):
        pair_key = ":".join(sorted([a["id"], b["id"]]))

        if existing_keys and pair_key in existing_keys:
            continue

        prompt = PAIRWISE_PROMPT.format(
            a_role=a.get("role", ""),
            a_role_needed=a.get("role_needed", ""),
            a_lane=a.get("lane", ""),
            a_climate_areas=", ".join(a.get("climate_areas", [])),
            a_top_area=a.get("top_climate_area", ""),
            a_commitment=a.get("commitment", ""),
            a_arrangement=a.get("arrangement", ""),
            a_location=a.get("location", ""),
            a_matching_summary=a.get("matching_summary", ""),
            a_superpower=a.get("superpower", ""),
            a_domain_tags=", ".join(a.get("domain_tags", [])),
            a_intention=a.get("intention_90_day", ""),
            b_role=b.get("role", ""),
            b_role_needed=b.get("role_needed", ""),
            b_lane=b.get("lane", ""),
            b_climate_areas=", ".join(b.get("climate_areas", [])),
            b_top_area=b.get("top_climate_area", ""),
            b_commitment=b.get("commitment", ""),
            b_arrangement=b.get("arrangement", ""),
            b_location=b.get("location", ""),
            b_matching_summary=b.get("matching_summary", ""),
            b_superpower=b.get("superpower", ""),
            b_domain_tags=", ".join(b.get("domain_tags", [])),
            b_intention=b.get("intention_90_day", ""),
        )

        requests.append(
            {
                "custom_id": pair_key,
                "params": {
                    "model": "claude-sonnet-4-5-20250929",
                    "max_tokens": 300,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": prompt}],
                },
            }
        )

    return requests


def submit_batch(
    input_path: str = "data/enriched_attendees.json",
    output_path: str = "data/matrix.json",
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """Submit pairwise scoring batch and poll for results.

    Resumes from existing matrix.json by default — only scores new pairs.
    Pass force=True to re-score everything.
    Pass dry_run=True to preview what would be scored without calling the API.
    """
    with open(input_path) as f:
        attendees = json.load(f)

    # Load existing scores for resumability
    output_file = Path(output_path)
    existing_matrix: dict[str, dict] = {}
    if not force and output_file.exists():
        with open(output_file) as f:
            existing_matrix = json.load(f)
        print(f"Found {len(existing_matrix)} existing scores in {output_path}")

    existing_keys = set(existing_matrix.keys()) if not force else None
    requests = generate_batch_requests(attendees, existing_keys)

    total_pairs = len(attendees) * (len(attendees) - 1) // 2
    print(f"{total_pairs} total pairs, {len(requests)} to score")

    if not requests:
        print("All pairs already scored. Use --force to re-score.")
        return existing_matrix

    if dry_run:
        print(f"Dry run — would submit {len(requests)} requests to Claude Batch API.")
        return existing_matrix

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    print(f"Submitting batch of {len(requests)} requests...")
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch submitted: {batch_id}")

    # Poll for completion
    while True:
        status = client.messages.batches.retrieve(batch_id)
        print(
            f"  Status: {status.processing_status} "
            f"({status.request_counts.succeeded}/{status.request_counts.processing}/"
            f"{status.request_counts.errored})"
        )
        if status.processing_status == "ended":
            break
        time.sleep(30)

    # Retrieve results and merge with existing
    print("Retrieving results...")
    matrix = dict(existing_matrix)

    for result in client.messages.batches.results(batch_id):
        pair_key = result.custom_id
        if result.result.type == "succeeded":
            try:
                text = result.result.message.content[0].text
                data = json.loads(text)
                matrix[pair_key] = {
                    "score": data.get("score", 0),
                    "rationale": data.get("rationale", ""),
                    "spark": data.get("spark", ""),
                }
            except (json.JSONDecodeError, IndexError, AttributeError) as e:
                print(f"  Warning: Failed to parse result for {pair_key}: {e}")
                matrix[pair_key] = {"score": 50, "rationale": "Parse error", "spark": ""}
        else:
            print(f"  Warning: Request failed for {pair_key}: {result.result.type}")
            matrix[pair_key] = {"score": 50, "rationale": "API error", "spark": ""}

    # Save
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(matrix, f, indent=2)

    print(f"Scored {len(matrix)} pairs → {output_path}")

    # Stats
    scores = [v["score"] for v in matrix.values()]
    if scores:
        print(f"  Score range: {min(scores)}-{max(scores)}")
        print(f"  Average: {sum(scores) / len(scores):.1f}")

    return matrix


def main():
    parser = argparse.ArgumentParser(description="Score all attendee pairs via Claude Batch API")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-score all pairs (default: skip already-scored pairs)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be scored without calling the API",
    )
    parser.add_argument(
        "--input", default="data/enriched_attendees.json", help="Attendee JSON path"
    )
    parser.add_argument("--output", default="data/matrix.json", help="Matrix output path")
    args = parser.parse_args()

    submit_batch(
        input_path=args.input,
        output_path=args.output,
        force=args.force,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
