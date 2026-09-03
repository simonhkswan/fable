"""Every roll in the game comes from one seed, and the seed comes from the
event. Same PR, same rolls, forever."""
import hashlib
import random


def seed_of(text):
    return int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)


def rng_for(text, salt=""):
    return random.Random(seed_of(text + "|" + salt))


def weighted(rng, table):
    """table: dict name -> weight, or list of [name, weight]."""
    pairs = list(table.items()) if isinstance(table, dict) else [tuple(p) for p in table]
    total = sum(w for _, w in pairs)
    if total <= 0:
        return pairs[0][0]
    r = rng.uniform(0, total)
    acc = 0.0
    for name, w in pairs:
        acc += w
        if r <= acc:
            return name
    return pairs[-1][0]
