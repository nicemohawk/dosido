#!/usr/bin/env python3
"""Test LinkedIn scraping and profile enrichment.

Usage:
  python scripts/test_profile.py                                    # prompts for URL
  python scripts/test_profile.py https://linkedin.com/in/someone
  python scripts/test_profile.py --enrich                           # prompts for URL + questions
  python scripts/test_profile.py https://linkedin.com/in/someone --enrich
  python scripts/test_profile.py --enrich --provider ollama
  python scripts/test_profile.py --enrich --provider none
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

# Ensure project root is on sys.path
sys.path.insert(0, ".")

from pipeline.enrich import enrich_attendee, fetch_linkedin_text, strip_html


def fetch_and_display(url: str) -> str:
    """Fetch a LinkedIn URL and display results. Returns extracted text."""
    print(f"\nFetching: {url}")
    print("-" * 60)

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
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
    except Exception as e:
        print(f"Request failed: {e}")
        return ""

    print(f"Status:         {response.status_code}")
    print(f"Final URL:      {response.url}")
    print(f"Content length: {len(response.text):,} chars")

    login_wall = "authwall" in str(response.url) or "login" in str(response.url)
    if login_wall:
        print(
            "\n!! LinkedIn returned a login wall (expected).\n"
            "   LinkedIn blocks unauthenticated scraping. The enrichment\n"
            "   pipeline works fine without it — it uses application answers instead."
        )
        return ""

    text = strip_html(response.text)[:3000]
    print(f"Extracted text: {len(text):,} chars")
    if text:
        print()
        print(text[:2000])
        if len(text) > 2000:
            print(f"  ... ({len(text) - 2000} more chars)")
    else:
        print("  (no text extracted)")

    return text


def prompt_application_questions() -> dict:
    """Interactive CLI prompts for the application questions."""
    print("\n" + "=" * 60)
    print("  APPLICATION QUESTIONS")
    print("  (press Enter to skip any question)")
    print("=" * 60)

    fields = [
        ("name", "Full name"),
        ("lane", "Lane [idea / joiner / flexible]"),
        ("role", "Primary role [engineering / product / gtm / science / ops / policy]"),
        ("role_needed", "Role you need [engineering / product / gtm / science / ops / policy]"),
        ("top_climate_area", "Top climate area (e.g. energy, agriculture, carbon removal)"),
        ("climate_areas", "Other climate areas (comma-separated)"),
        ("commitment", "Commitment [full-time / part-time / exploring]"),
        ("arrangement", "Working arrangement [remote-open / colocated]"),
        ("location", "Location (e.g. San Francisco, CA)"),
        ("intention_90_day", "What do you want to accomplish in the next 90 days?"),
        ("proof_link_1", "Proof link 1 (portfolio, GitHub, etc.)"),
        ("proof_link_2", "Proof link 2"),
    ]

    answers: dict = {}
    for key, label in fields:
        value = input(f"\n  {label}: ").strip()
        if key == "climate_areas" and value:
            answers[key] = [a.strip() for a in value.split(",")]
        else:
            answers[key] = value

    # Defaults for empty values
    if not answers.get("lane"):
        answers["lane"] = "flexible"
    if not answers.get("commitment"):
        answers["commitment"] = "exploring"
    if not answers.get("arrangement"):
        answers["arrangement"] = "remote-open"
    if not answers.get("climate_areas"):
        answers["climate_areas"] = []

    return answers


def main():
    parser = argparse.ArgumentParser(
        description="Test LinkedIn scraping and profile enrichment"
    )
    parser.add_argument("url", nargs="?", default=None, help="LinkedIn profile URL (prompts if omitted)")
    parser.add_argument("--enrich", action="store_true", help="Also run enrichment (prompts for application questions)")
    parser.add_argument(
        "--provider",
        choices=["claude", "ollama", "none"],
        default=None,
        help="LLM provider (default: from LLM_PROVIDER env / config)",
    )
    parser.add_argument("--ollama-model", default=None, help="Ollama model name (default: from config)")
    parser.add_argument("--ollama-url", default=None, help="Ollama API URL (default: from config)")
    args = parser.parse_args()

    # Apply CLI overrides to settings
    from app.config import settings

    if args.provider:
        settings.llm_provider = args.provider
    if args.ollama_model:
        settings.ollama_model = args.ollama_model
    if args.ollama_url:
        settings.ollama_url = args.ollama_url

    provider = settings.llm_provider

    # Prompt for URL if not passed as argument
    url = args.url
    if not url:
        url = input("\nLinkedIn profile URL: ").strip()
        if not url:
            print("No URL provided — exiting.")
            sys.exit(0)

    # --- Step 1: Scrape ---
    print("\n" + "=" * 60)
    print("  LINKEDIN SCRAPE")
    print("=" * 60)
    linkedin_text = fetch_and_display(url)

    if not args.enrich:
        print("\n(pass --enrich to also test enrichment with application questions)")
        return

    # --- Step 2: Application questions ---
    attendee = prompt_application_questions()
    attendee["linkedin_url"] = url

    # --- Step 3: Enrich ---
    print("\n" + "=" * 60)
    print(f"  ENRICHMENT (provider: {provider})")
    print("=" * 60)

    try:
        enriched = enrich_attendee(dict(attendee), provider=provider)

        # Show only the enrichment fields
        enrichment_fields = {
            k: enriched[k]
            for k in (
                "domain_tags",
                "technical_depth",
                "stage",
                "superpower",
                "matching_summary",
                "red_flags",
            )
            if k in enriched
        }
        print("\nResult:")
        print(json.dumps(enrichment_fields, indent=2))

    except Exception as e:
        print(f"\nEnrichment failed: {e}")
        if provider == "claude":
            print("Make sure ANTHROPIC_API_KEY is set in your environment or .env file.")
        elif provider == "ollama":
            print(
                f"Make sure Ollama is running at {settings.ollama_url} "
                f"with model '{settings.ollama_model}' pulled.\n"
                f"  Install: https://ollama.com\n"
                f"  Then:    ollama pull {settings.ollama_model}"
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
