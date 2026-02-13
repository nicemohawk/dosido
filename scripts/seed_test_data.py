"""Generate fake attendees and compatibility matrix for development testing."""

from __future__ import annotations

import json
import random
import uuid
from itertools import combinations
from pathlib import Path

FIRST_NAMES = [
    "Alice", "Ben", "Carlos", "Dana", "Emily", "Frank", "Grace", "Henry",
    "Iris", "Jack", "Kim", "Leo", "Maya", "Noah", "Olivia", "Pablo",
    "Quinn", "Rosa", "Sam", "Tara", "Uma", "Victor", "Wendy", "Xavier",
    "Yuki", "Zara", "Aaron", "Beth", "Chris", "Diane", "Elena", "Felix",
    "Gina", "Hugo", "Isla", "James", "Kira", "Liam", "Mia", "Nate",
    "Opal", "Priya", "Raj", "Sofia", "Tyler", "Uri", "Vera", "Will",
    "Xena", "Yara", "Zach", "Ava", "Blake", "Cleo", "Drew", "Eva",
    "Finn", "Gia", "Hank", "Ivy",
]

LAST_INITIALS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

ROLES = ["engineering", "product", "gtm", "science", "ops", "policy"]
LANES = ["idea", "joiner", "flexible"]
CLIMATE_AREAS = [
    "energy", "transport", "buildings", "food", "water", "carbon removal",
    "biodiversity", "circular economy", "climate finance", "policy",
    "grid infrastructure", "EVs", "solar", "wind", "hydrogen",
    "sustainable materials", "agriculture", "ocean", "forestry",
]
COMMITMENTS = ["full-time", "part-time", "exploring"]
ARRANGEMENTS = ["colocated", "remote-open"]
LOCATIONS = ["SF", "NYC", "LA", "Seattle", "Austin", "Boston", "Chicago", "Denver", "Remote"]


def generate_attendees(count: int = 60) -> list[dict]:
    attendees = []
    used_names = set()

    for i in range(count):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last_init = LAST_INITIALS[i % len(LAST_INITIALS)]
        name = f"{first} {last_init}."

        # Ensure unique names
        while name in used_names:
            last_init = random.choice(LAST_INITIALS)
            name = f"{first} {last_init}."
        used_names.add(name)

        role = random.choice(ROLES)
        # Role needed is usually different from own role
        role_needed = random.choice([r for r in ROLES if r != role])

        num_areas = random.randint(1, 4)
        climate_areas = random.sample(CLIMATE_AREAS, num_areas)
        top_area = climate_areas[0]

        attendee = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "email": f"{first.lower()}.{last_init.lower()}@test.com",
            "location": random.choice(LOCATIONS),
            "linkedin_url": "",
            "token": str(uuid.uuid4())[:8],
            "lane": random.choice(LANES),
            "role": role,
            "role_needed": role_needed,
            "climate_areas": climate_areas,
            "top_climate_area": top_area,
            "commitment": random.choice(COMMITMENTS),
            "arrangement": random.choice(ARRANGEMENTS),
            "proof_link_1": "",
            "proof_link_2": "",
            "intention_90_day": f"Looking to build in {top_area}",
            # Simulated enrichment
            "domain_tags": climate_areas[:2],
            "technical_depth": random.randint(1, 5),
            "stage": random.choice([
                "first-time-founder", "repeat-founder", "operator", "researcher"
            ]),
            "superpower": f"Deep expertise in {top_area} with {role} background",
            "matching_summary": (
                f"{name} is a {role} looking for a {role_needed} cofounder "
                f"focused on {top_area}. {random.choice(COMMITMENTS)} commitment."
            ),
            "red_flags": [],
            "status": "not-arrived",
            "source": "application",
            "has_full_scoring": True,
            "pit_stop_count": 0,
        }
        attendees.append(attendee)

    return attendees


def generate_matrix(attendees: list[dict]) -> dict[str, dict]:
    """Generate realistic-ish compatibility scores for all pairs."""
    matrix = {}

    for a, b in combinations(attendees, 2):
        pair_key = ":".join(sorted([a["id"], b["id"]]))

        # Base score — random but influenced by compatibility signals
        base = random.randint(25, 75)

        # Bonus for complementary roles
        if a["role"] != b["role"] and a["role_needed"] == b["role"]:
            base += random.randint(5, 15)
        if b["role_needed"] == a["role"]:
            base += random.randint(5, 10)

        # Bonus for lane complementarity
        if (a["lane"] == "idea" and b["lane"] == "joiner") or (
            a["lane"] == "joiner" and b["lane"] == "idea"
        ):
            base += random.randint(5, 10)

        # Bonus for climate overlap
        overlap = len(set(a["climate_areas"]) & set(b["climate_areas"]))
        base += overlap * random.randint(2, 5)

        # Top area match
        if a["top_climate_area"] == b["top_climate_area"]:
            base += random.randint(5, 10)

        # Penalty for incompatible arrangements
        if (
            a["arrangement"] == "colocated"
            and b["arrangement"] == "colocated"
            and a["location"] != b["location"]
        ):
            base -= 30

        score = max(0, min(100, base))

        climate_topics = list(set(a["climate_areas"]) & set(b["climate_areas"]))
        spark_topic = climate_topics[0] if climate_topics else a["top_climate_area"]

        matrix[pair_key] = {
            "score": score,
            "rationale": f"{'Strong' if score > 70 else 'Moderate' if score > 45 else 'Weak'} match based on {a['role']}/{b['role']} complementarity and {spark_topic} overlap.",
            "spark": f"Discuss approaches to {spark_topic} and potential co-founding synergies.",
        }

    return matrix


def generate_walkup_badges(count: int = 20) -> list[dict]:
    """Generate walk-up reserve badges with fun slugs."""
    adjectives = [
        "Pink", "Turquoise", "Golden", "Silver", "Cosmic", "Crimson",
        "Emerald", "Amber", "Sapphire", "Coral", "Indigo", "Scarlet",
        "Azure", "Violet", "Copper", "Jade", "Ruby", "Onyx", "Pearl", "Topaz",
    ]
    animals = [
        "Unicorn", "Armadillo", "Falcon", "Otter", "Phoenix", "Dolphin",
        "Panther", "Penguin", "Lynx", "Hummingbird", "Chameleon", "Fox",
        "Hawk", "Koala", "Narwhal", "Raven", "Toucan", "Wolf", "Zebra", "Crane",
    ]

    badges = []
    random.shuffle(adjectives)
    random.shuffle(animals)

    for i in range(min(count, len(adjectives))):
        slug = f"{adjectives[i]} {animals[i]}"
        badges.append({
            "slug": slug,
            "token": str(uuid.uuid4())[:8],
        })

    return badges


def seed(
    attendee_count: int = 60,
    output_dir: str = "data",
) -> None:
    """Generate all test data files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Generating {attendee_count} fake attendees...")
    attendees = generate_attendees(attendee_count)
    with open(out / "enriched_attendees.json", "w") as f:
        json.dump(attendees, f, indent=2)
    print(f"  → {out / 'enriched_attendees.json'}")

    pair_count = attendee_count * (attendee_count - 1) // 2
    print(f"Generating {pair_count} pair scores...")
    matrix = generate_matrix(attendees)
    with open(out / "matrix.json", "w") as f:
        json.dump(matrix, f, indent=2)
    print(f"  → {out / 'matrix.json'}")

    print("Generating 20 walk-up badges...")
    badges = generate_walkup_badges(20)
    with open(out / "walkup_badges.json", "w") as f:
        json.dump(badges, f, indent=2)
    print(f"  → {out / 'walkup_badges.json'}")

    print("Done!")


if __name__ == "__main__":
    import sys

    count = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed(attendee_count=count)
