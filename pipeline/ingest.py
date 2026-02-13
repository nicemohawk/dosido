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
    if "full" in value:
        return "full-time"
    if "part" in value:
        return "part-time"
    return "exploring"


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
