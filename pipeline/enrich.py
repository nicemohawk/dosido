"""Per-applicant LLM enrichment using Claude API."""

from __future__ import annotations

import json
from pathlib import Path

import anthropic
import httpx

from pipeline.prompts import ENRICHMENT_PROMPT


def fetch_linkedin_text(url: str) -> str:
    """Attempt to fetch LinkedIn profile text. Returns empty string on failure."""
    if not url or "linkedin.com" not in url:
        return ""
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            },
        )
        if response.status_code == 200:
            # Extract text content (basic — LinkedIn blocks most scraping)
            text = response.text
            # Very basic extraction — in practice this may not work well
            if len(text) > 500:
                return text[:3000]
    except Exception:
        pass
    return ""


def enrich_attendee(attendee: dict, client: anthropic.Anthropic) -> dict:
    """Run LLM enrichment for a single attendee."""
    linkedin_text = fetch_linkedin_text(attendee.get("linkedin_url", ""))
    linkedin_section = (
        f"Here is their LinkedIn profile content:\n{linkedin_text}"
        if linkedin_text
        else "LinkedIn profile was not available. Enrich based on application data only."
    )

    prompt = ENRICHMENT_PROMPT.format(
        lane=attendee.get("lane", ""),
        role=attendee.get("role", ""),
        role_needed=attendee.get("role_needed", ""),
        climate_areas=", ".join(attendee.get("climate_areas", [])),
        top_area=attendee.get("top_climate_area", ""),
        commitment=attendee.get("commitment", ""),
        arrangement=attendee.get("arrangement", ""),
        location=attendee.get("location", ""),
        link_1=attendee.get("proof_link_1", ""),
        link_2=attendee.get("proof_link_2", ""),
        intention=attendee.get("intention_90_day", ""),
        linkedin_section=linkedin_section,
    )

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        result = json.loads(response.content[0].text)
        attendee["domain_tags"] = result.get("domain_tags", [])
        attendee["technical_depth"] = result.get("technical_depth", 0)
        attendee["stage"] = result.get("stage", "")
        attendee["superpower"] = result.get("superpower", "")
        attendee["matching_summary"] = result.get("matching_summary", "")
        attendee["red_flags"] = result.get("red_flags", [])
    except (json.JSONDecodeError, IndexError) as e:
        print(f"  Warning: Failed to parse enrichment for {attendee.get('name')}: {e}")

    return attendee


def enrich_all(
    input_path: str = "data/attendees.json",
    output_path: str = "data/enriched_attendees.json",
) -> list[dict]:
    """Enrich all attendees. Resumable — skips already-enriched."""
    with open(input_path) as f:
        attendees = json.load(f)

    # Load existing enriched data for resumability
    enriched_path = Path(output_path)
    existing: dict[str, dict] = {}
    if enriched_path.exists():
        with open(enriched_path) as f:
            for att in json.load(f):
                existing[att["id"]] = att

    client = anthropic.Anthropic()
    results = []

    for i, attendee in enumerate(attendees):
        if attendee["id"] in existing and existing[attendee["id"]].get("matching_summary"):
            print(f"  [{i+1}/{len(attendees)}] Skipping {attendee['name']} (already enriched)")
            results.append(existing[attendee["id"]])
            continue

        print(f"  [{i+1}/{len(attendees)}] Enriching {attendee['name']}...")
        enriched = enrich_attendee(attendee, client)
        results.append(enriched)

        # Save incrementally
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

    print(f"Enriched {len(results)} attendees → {output_path}")
    return results


if __name__ == "__main__":
    enrich_all()
