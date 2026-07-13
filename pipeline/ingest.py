"""Ingest Luma CSV export and normalize into attendee records."""

from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path

# Map Luma CSV column headers to internal field names
COLUMN_MAP = {
    "name": "name",
    "email": "email",
    "location": "location",
    "linkedin url": "linkedin_url",
    "lane": "lane",
    "primary role": "role",
    "role needed": "role_needed",
    "climate areas (all that apply)": "climate_areas",
    "top climate area": "top_climate_area",
    "commitment": "commitment",
    "working arrangement": "arrangement",
    "proof link 1": "proof_link_1",
    "proof link 2": "proof_link_2",
    "90-day intention": "intention_90_day",
    "runway": "runway",
    "ambition": "ambition",
    "scale ambition": "ambition",
    "equity philosophy": "equity_philosophy",
    "equity split philosophy": "equity_philosophy",
    "edge": "edge",
    "your edge": "edge",
    "idea flexibility": "idea_flexibility",
    "decision style": "decision_style",
    "proof 1 summary": "proof_summary_1",
    "proof link 1 description": "proof_summary_1",
    "proof 2 summary": "proof_summary_2",
    "proof link 2 description": "proof_summary_2",
    "hardest thing": "hardest_thing",
}


def normalize_key(header: str) -> str | None:
    """Try to match a CSV header to an internal field name."""
    cleaned = header.strip().lower()
    return COLUMN_MAP.get(cleaned)


def normalize_lane(value: str) -> str:
    value = value.strip().lower()
    if "idea" in value:
        return "idea"
    if "join" in value:
        return "joiner"
    return "flexible"


def normalize_role(value: str) -> str:
    value = value.strip().lower()
    for role in ["engineering", "product", "gtm", "science", "ops", "policy"]:
        if role in value:
            return role
    if "sales" in value or "marketing" in value or "go-to-market" in value:
        return "gtm"
    return "engineering"


def normalize_commitment(value: str) -> str:
    value = value.strip().lower()
    conditional_markers = ["3 month", "three month", "if i find", "soon"]
    if any(marker in value for marker in conditional_markers):
        return "full-time-soon"
    if "part" in value:
        return "part-time"
    if "full" in value:
        return "full-time"
    return "exploring"


def normalize_runway(value: str) -> str:
    value = value.strip().lower()
    if "prefer not" in value or not value:
        return "undisclosed"
    if "12" in value and ("+" in value or "plus" in value or "more" in value or "over" in value):
        return "12-plus-months"
    if "3" in value and "12" in value:
        return "3-12-months"
    if "less than 3" in value or "under 3" in value or "<3" in value or "< 3" in value:
        return "under-3-months"
    if "12" in value:
        return "12-plus-months"
    return "undisclosed"


def normalize_ambition(value: str) -> str:
    value = value.strip().lower()
    if "bootstrap" in value or "lifestyle" in value:
        return "bootstrap"
    if "venture" in value or "go big" in value or "ipo" in value or "scale" in value:
        return "venture-scale"
    if "moderate" in value or "middle" in value or "between" in value:
        return "moderate"
    return "undecided"


def normalize_equity_philosophy(value: str) -> str:
    value = value.strip().lower()
    if "vest" in value:
        return "near-equal-vesting"
    if "equal" in value:
        return "equal"
    if "contribut" in value or "reflect" in value:
        return "contribution-based"
    return "no-strong-view"


def normalize_edge(value: str) -> str:
    value = value.strip().lower()
    if "technical" in value or "engineering" in value:
        return "technical"
    if "domain" in value or "industry" in value:
        return "domain"
    if "network" in value or "distribution" in value:
        return "network"
    return "unknown"


def normalize_idea_flexibility(value: str) -> str:
    value = value.strip().lower()
    if "commit" in value:
        return "committed"
    if "drop" in value or "flexib" in value:
        return "flexible"
    return "n/a"


def normalize_decision_style(value: str) -> str:
    value = value.strip().lower()
    if "debate" in value or "argue" in value or "talk it out" in value:
        return "debate"
    if "write" in value or "memo" in value:
        return "write-then-decide"
    if "defer" in value or "owner" in value:
        return "defer-to-owner"
    if "data" in value or "evidence" in value or "test" in value:
        return "data-driven"
    return "unknown"


def normalize_arrangement(value: str) -> str:
    value = value.strip().lower()
    if "coloc" in value or "in-person" in value or "on-site" in value:
        return "colocated"
    return "remote-open"


def parse_climate_areas(value: str) -> list[str]:
    """Parse comma or semicolon separated climate areas."""
    if not value:
        return []
    separators = [";", ","]
    for sep in separators:
        if sep in value:
            return [area.strip() for area in value.split(sep) if area.strip()]
    return [value.strip()] if value.strip() else []


def ingest_csv(csv_path: str, output_path: str = "data/attendees.json") -> list[dict]:
    """Parse a Luma CSV export and produce normalized attendee records."""
    attendees = []

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            record: dict = {"id": str(uuid.uuid4())[:8]}

            for header, value in row.items():
                field = normalize_key(header)
                if not field:
                    continue
                record[field] = value.strip() if value else ""

            # Normalize specific fields
            if "lane" in record:
                record["lane"] = normalize_lane(record["lane"])
            if "role" in record:
                record["role"] = normalize_role(record["role"])
            if "role_needed" in record:
                record["role_needed"] = normalize_role(record["role_needed"])
            if "commitment" in record:
                record["commitment"] = normalize_commitment(record["commitment"])
            if "arrangement" in record:
                record["arrangement"] = normalize_arrangement(record["arrangement"])
            if "climate_areas" in record:
                record["climate_areas"] = parse_climate_areas(record["climate_areas"])
            if "runway" in record:
                record["runway"] = normalize_runway(record["runway"])
            if "ambition" in record:
                record["ambition"] = normalize_ambition(record["ambition"])
            if "equity_philosophy" in record:
                record["equity_philosophy"] = normalize_equity_philosophy(
                    record["equity_philosophy"]
                )
            if "edge" in record:
                record["edge"] = normalize_edge(record["edge"])
            if "idea_flexibility" in record:
                record["idea_flexibility"] = normalize_idea_flexibility(record["idea_flexibility"])
            if "decision_style" in record:
                record["decision_style"] = normalize_decision_style(record["decision_style"])

            # Generate a unique token for badge QR codes
            record["token"] = str(uuid.uuid4())[:8]

            if record.get("name"):
                attendees.append(record)

    # Write output
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(attendees, f, indent=2)

    print(f"Ingested {len(attendees)} attendees from {csv_path}")
    print(f"Output: {output_path}")
    return attendees


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.ingest <path-to-luma-csv>")
        sys.exit(1)
    ingest_csv(sys.argv[1])
