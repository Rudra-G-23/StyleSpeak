"""Resolve a conversational reference to a single product in the last results.

Handles "the second one", "the yellow one", "the linen shirt". Ambiguity is
never guessed: if two shown products match, the caller is told to ask which one.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.assistant.schemas import CartReference
from src.demo_catalog import CANONICAL_COLORS


@dataclass
class Resolution:
    sku: str | None
    product: dict | None
    error: str | None

    @property
    def ok(self) -> bool:
        return self.sku is not None


def _ordinal(n: int) -> str:
    return {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}.get(n, f"#{n}")


def resolve_reference(reference: CartReference, last_results: list[dict]) -> Resolution:
    if not last_results:
        return Resolution(
            None, None, "There are no results on screen yet - search for something first."
        )

    # 1) explicit position wins
    if reference.position is not None:
        pos = reference.position
        if 1 <= pos <= len(last_results):
            product = last_results[pos - 1]
            return Resolution(product["sku"], product, None)
        return Resolution(
            None,
            None,
            f"I only see {len(last_results)} item(s), so there is no item {pos}.",
        )

    # 2) colour reference, matched against the shown products
    if reference.color:
        color = reference.color.lower().strip()
        # normalise a raw word to a canonical colour if possible
        color = next((c for c in CANONICAL_COLORS if c == color), color)
        matches = [
            p for p in last_results if p.get("color") == color or color in p.get("name", "").lower()
        ]
        return _from_matches(matches, f'"{reference.color}"')

    # 3) name reference
    if reference.product_name:
        needle = reference.product_name.lower().strip()
        matches = [p for p in last_results if needle in p.get("name", "").lower()]
        if not matches:
            tokens = [t for t in needle.split() if len(t) > 2]
            matches = [
                p
                for p in last_results
                if tokens and all(t in p.get("name", "").lower() for t in tokens)
            ]
        return _from_matches(matches, f'"{reference.product_name}"')

    # 4) nothing specific - only safe if there is exactly one result
    if len(last_results) == 1:
        product = last_results[0]
        return Resolution(product["sku"], product, None)
    return Resolution(
        None,
        None,
        'Which one would you like - tell me the position (e.g. "the second one") or a colour.',
    )


def _from_matches(matches: list[dict], label: str) -> Resolution:
    if not matches:
        return Resolution(None, None, f"I don't see a {label} item in the current results.")
    if len(matches) == 1:
        product = matches[0]
        return Resolution(product["sku"], product, None)
    if len(matches) <= 3:
        positions = " or ".join(_ordinal(p["position"]) for p in matches)
        return Resolution(
            None, None, f"I see {len(matches)} {label} items - the {positions}. Which one?"
        )
    lo, hi = matches[0]["position"], matches[-1]["position"]
    return Resolution(
        None,
        None,
        f"I see {len(matches)} {label} items (positions {lo}-{hi}). "
        'Tell me the position, e.g. "add the third one".',
    )
