from __future__ import annotations

import hashlib
from typing import TypeVar


T = TypeVar("T")


def seeded_choice(items: tuple[T, ...], *, seed_key: str) -> T:
    if not items:
        raise ValueError("seeded_choice requires at least one item.")
    digest = hashlib.sha256(seed_key.encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(items)
    return items[index]


def seeded_order(items: tuple[T, ...], *, seed_key: str, item_key) -> tuple[T, ...]:
    decorated = []
    for item in items:
        digest = hashlib.sha256(f"{seed_key}|{item_key(item)}".encode("utf-8")).hexdigest()
        decorated.append((digest, item))
    decorated.sort(key=lambda entry: entry[0])
    return tuple(item for _, item in decorated)


def seeded_cycled_choice(items: tuple[T, ...], *, seed_key: str, position: int) -> T:
    if not items:
        raise ValueError("seeded_cycled_choice requires at least one item.")
    if len(items) == 1:
        return items[0]
    digest = hashlib.sha256(seed_key.encode("utf-8")).digest()
    start_index = int.from_bytes(digest[:8], "big") % len(items)
    step_options = tuple(step for step in range(1, len(items) + 1) if _gcd(step, len(items)) == 1)
    step_seed = int.from_bytes(digest[8:16], "big") % len(step_options)
    step = step_options[step_seed]
    index = (start_index + (step * max(0, position))) % len(items)
    return items[index]


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)
