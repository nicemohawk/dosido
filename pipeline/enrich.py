"""Per-applicant LLM enrichment — supports Claude, Ollama, or no-LLM stub."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

from app.config import settings
from pipeline.prompts import ENRICHMENT_PROMPT


def fetch_linkedin_text(url: str) -> str:
    """Attempt to fetch LinkedIn profile text. Returns empty string on failure.

    LinkedIn blocks most unauthenticated scraping, so this will typically
    return limited or no content. The enrichment prompt handles this gracefully.
    """
    if not url or "linkedin.com" not in url:
        return ""
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        login_wall = "authwall" in str(response.url) or "login" in str(response.url)
        if login_wall:
            return ""
        if response.status_code == 200 and len(response.text) > 500:
            return strip_html(response.text)[:3000]
    except Exception:
        pass
    return ""


def strip_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def llm_complete(prompt: str, *, provider: str | None = None) -> str:
    """Send a prompt to the configured LLM provider and return the raw text response.

    Args:
        prompt: The full prompt text.
        provider: "claude", "ollama", or "none". Defaults to settings.llm_provider.

    Returns:
        Raw text response from the model.
    """
    provider = provider or settings.llm_provider

    if provider == "claude":
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    if provider == "ollama":
        model = settings.ollama_model
        url = settings.ollama_url
        response = httpx.post(
            f"{url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"]

    # provider == "none" — should not be called, but return empty JSON as safety net
    return "{}"


def _parse_json_response(text: str) -> dict:
    """Extract JSON from an LLM response, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to finding the first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise json.JSONDecodeError("No JSON found in response", text, 0)


def _build_stub_enrichment(attendee: dict) -> dict:
    """Generate enrichment data without an LLM, using only application fields."""
    climate_areas = attendee.get("climate_areas", [])
    top_area = attendee.get("top_climate_area", "climate")
    tags = [top_area] if top_area else []
    tags.extend(a for a in climate_areas if a and a != top_area)

    role = attendee.get("role", "generalist")
    intention = attendee.get("intention_90_day", "")

    summary_parts = []
    if attendee.get("lane"):
        summary_parts.append(f"{attendee['lane'].replace('-', ' ').title()} lane.")
    if role:
        summary_parts.append(f"Background in {role}.")
    if intention:
        summary_parts.append(intention[:200])

    return {
        "domain_tags": tags[:5],
        "technical_depth": 2,
        "stage": "first-time-founder",
        "superpower": f"{role} with interest in {top_area or 'climate tech'}",
        "matching_summary": " ".join(summary_parts) or "No detailed profile available.",
        "red_flags": [],
    }


def enrich_attendee(attendee: dict, client=None, *, provider: str | None = None) -> dict:
    """Run enrichment for a single attendee.

    Args:
        attendee: Attendee dict with application fields.
        client: Deprecated — ignored. Kept for backward compatibility.
        provider: "claude", "ollama", or "none". Defaults to settings.llm_provider.
    """
    provider = provider or settings.llm_provider

    if provider == "none":
        stub = _build_stub_enrichment(attendee)
        attendee.update(stub)
        return attendee

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

    try:
        raw = llm_complete(prompt, provider=provider)
        result = _parse_json_response(raw)
        attendee["domain_tags"] = result.get("domain_tags", [])
        attendee["technical_depth"] = result.get("technical_depth", 0)
        attendee["stage"] = result.get("stage", "")
        attendee["superpower"] = result.get("superpower", "")
        attendee["matching_summary"] = result.get("matching_summary", "")
        attendee["red_flags"] = result.get("red_flags", [])
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        print(f"  Warning: Failed to parse enrichment for {attendee.get('name')}: {e}")

    return attendee


def enrich_all(
    input_path: str = "data/attendees.json",
    output_path: str = "data/enriched_attendees.json",
    *,
    provider: str | None = None,
) -> list[dict]:
    """Enrich all attendees. Resumable — skips already-enriched."""
    provider = provider or settings.llm_provider

    with open(input_path) as f:
        attendees = json.load(f)

    # Load existing enriched data for resumability
    enriched_path = Path(output_path)
    existing: dict[str, dict] = {}
    if enriched_path.exists():
        with open(enriched_path) as f:
            for att in json.load(f):
                existing[att["id"]] = att

    results = []

    for i, attendee in enumerate(attendees):
        if attendee["id"] in existing and existing[attendee["id"]].get("matching_summary"):
            print(f"  [{i+1}/{len(attendees)}] Skipping {attendee['name']} (already enriched)")
            results.append(existing[attendee["id"]])
            continue

        print(f"  [{i+1}/{len(attendees)}] Enriching {attendee['name']} (provider: {provider})...")
        enriched = enrich_attendee(attendee, provider=provider)
        results.append(enriched)

        # Save incrementally
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

    print(f"Enriched {len(results)} attendees → {output_path}")
    return results


if __name__ == "__main__":
    enrich_all()
