"""Fun slug generator for walk-up badges (Google Docs style naming)."""

ADJECTIVES = [
    "Pink", "Turquoise", "Golden", "Silver", "Cosmic", "Crimson",
    "Emerald", "Amber", "Sapphire", "Coral", "Indigo", "Scarlet",
    "Azure", "Violet", "Copper", "Jade", "Ruby", "Onyx", "Pearl", "Topaz",
    "Neon", "Rustic", "Frosty", "Blazing", "Mystic", "Stellar",
    "Velvet", "Electric", "Radiant", "Bold",
]

ANIMALS = [
    "Unicorn", "Armadillo", "Falcon", "Otter", "Phoenix", "Dolphin",
    "Panther", "Penguin", "Lynx", "Hummingbird", "Chameleon", "Fox",
    "Hawk", "Koala", "Narwhal", "Raven", "Toucan", "Wolf", "Zebra", "Crane",
    "Octopus", "Jaguar", "Owl", "Parrot", "Salamander", "Starling",
    "Turtle", "Wombat", "Ibis", "Lemur",
]


def generate_slugs(count: int = 20) -> list[str]:
    """Generate unique fun slugs like 'Pink Unicorn', 'Cosmic Falcon'."""
    import random

    pairs = []
    adj_pool = list(ADJECTIVES)
    animal_pool = list(ANIMALS)
    random.shuffle(adj_pool)
    random.shuffle(animal_pool)

    for i in range(min(count, len(adj_pool), len(animal_pool))):
        pairs.append(f"{adj_pool[i]} {animal_pool[i]}")

    return pairs
