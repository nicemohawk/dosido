"""Pairwise compatibility scoring using Claude Batch API."""

from __future__ import annotations

import json
import time
from itertools import combinations
from pathlib import Path

import anthropic

from pipeline.prompts import PAIRWISE_PROMPT


def generate_batch_requests(attendees: list[dict]) -> list[dict]:
    """Generate batch API request objects for all pairs."""
    requests = []

    for a, b in combinations(attendees, 2):
        pair_key = ":".join(sorted([a["id"], b["id"]]))

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
) -> dict:
    """Submit pairwise scoring batch and poll for results."""
    with open(input_path) as f:
        attendees = json.load(f)

    pair_count = len(attendees) * (len(attendees) - 1) // 2
    print(f"Generating {pair_count} pair requests for {len(attendees)} attendees...")

    requests = generate_batch_requests(attendees)
    client = anthropic.Anthropic()

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

    # Retrieve results
    print("Retrieving results...")
    matrix: dict[str, dict] = {}

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
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(matrix, f, indent=2)

    print(f"Scored {len(matrix)} pairs → {output_path}")

    # Stats
    scores = [v["score"] for v in matrix.values()]
    if scores:
        print(f"  Score range: {min(scores)}-{max(scores)}")
        print(f"  Average: {sum(scores) / len(scores):.1f}")

    return matrix


if __name__ == "__main__":
    submit_batch()
