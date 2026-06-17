"""Fuzzy name matching for drivers and circuits using difflib (no extra deps)."""

from collections.abc import Callable
from difflib import SequenceMatcher


def _score(query: str, candidate: str) -> float:
    """Ratio of longest common subsequence; case-insensitive."""
    return SequenceMatcher(None, query.lower(), candidate.lower()).ratio()


def best_match[T](query: str, items: list[T], key_fns: list[Callable[[T], str | None]]) -> T | None:
    """Return the item whose best field score against query is highest (>= 0.6 threshold)."""
    if not items:
        return None

    best_item = None
    best_score = 0.0

    for item in items:
        # Score against each field; take the max
        item_score = max(
            (_score(query, fn(item)) for fn in key_fns if fn(item)),
            default=0.0,
        )
        if item_score > best_score:
            best_score = item_score
            best_item = item

    return best_item if best_score >= 0.6 else None


def match_driver(query: str, drivers):
    """Find the closest driver to a free-text query."""
    return best_match(
        query,
        drivers,
        [
            lambda d: d.family_name,
            lambda d: d.given_name,
            lambda d: d.full_name,
            lambda d: d.code,
            lambda d: d.driver_id,
            lambda d: d.permanent_number,
        ],
    )


def match_circuit(query: str, circuits):
    """Find the closest circuit to a free-text query."""
    return best_match(
        query,
        circuits,
        [
            lambda c: c.name,
            lambda c: c.locality,
            lambda c: c.country,
            lambda c: c.circuit_id,
        ],
    )
