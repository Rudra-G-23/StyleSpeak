"""Evidence-based normalization for the raw Zalando metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass

COLOR_TERMS = {
    "black": ("black", "charcoal", "anthracite"),
    "blue": ("blue", "navy", "denim", "indigo"),
    "grey": ("grey", "gray", "silver"),
    "brown": ("brown", "camel", "cognac"),
    "beige": ("beige", "cream", "sand", "taupe"),
    "green": ("green", "olive", "khaki"),
    "white": ("white", "ivory"),
    "red": ("red", "burgundy", "bordeaux", "wine"),
}

PANTS_TERMS = ("trousers", "pants", "jeans", "joggers", "chino", "tracksuit bottoms")
WOMEN_TERMS = (" women", " women'", " ladies", " female", " w -", " w ", " girl")
UNISEX_TERMS = ("unisex",)
SUBCATEGORY_TERMS = {
    "cargo": ("cargo",),
    "jeans": ("jeans", "denim"),
    "joggers": ("jogger", "tracksuit bottoms", "sweatpant"),
    "chinos": ("chino",),
    "formal": ("suit trousers", "formal", "tailored", "smart trousers"),
    "casual": ("casual",),
}


@dataclass(frozen=True)
class NormalizedProduct:
    gender: str
    category: str
    subcategory: str | None
    color: str | None
    family_key: str


def _words(text: str) -> str:
    return f" {re.sub(r'[^a-z0-9]+', ' ', text.lower())} "


def normalize_color(text: str) -> str | None:
    words = _words(text)
    for color, terms in COLOR_TERMS.items():
        if any(f" {term} " in words for term in terms):
            return color
    return None


def normalize_subcategory(text: str) -> str | None:
    lowered = text.lower()
    for category, terms in SUBCATEGORY_TERMS.items():
        if any(term in lowered for term in terms):
            return category
    return None


def normalize_gender(name: str, source_url: str, category: str) -> str:
    evidence = _words(f"{name} {source_url} {category}")
    if any(term in evidence for term in WOMEN_TERMS):
        return "women"
    if any(term in evidence for term in UNISEX_TERMS):
        return "unisex"
    if " men " in evidence or " mens " in evidence or category == "Men T-Shirts & Polos":
        return "men"
    # The raw dataset does not provide an apparel-gender field. Do not turn a
    # missing signal into a men's claim: unknown products remain searchable only
    # without a gender constraint.
    return "unknown"


def normalize_product(
    name: str, source_url: str, category: str, brand: str
) -> NormalizedProduct | None:
    text = f"{name} {category}"
    parts = [part.strip().lower() for part in name.split(" - ") if part.strip()]
    product_type = parts[-2] if len(parts) >= 2 else name.lower()
    if not any(term in product_type for term in PANTS_TERMS):
        return None
    color = normalize_color(text)
    subcategory = normalize_subcategory(text)
    stem = _words(name)
    for term in (*[item for terms in COLOR_TERMS.values() for item in terms], *PANTS_TERMS):
        stem = stem.replace(f" {term} ", " ")
    stem = re.sub(r"\s+", " ", stem).strip()[:220]
    family_key = f"{brand.lower().strip()}:{stem or name.lower().strip()}"
    return NormalizedProduct(
        gender=normalize_gender(name, source_url, category),
        category="pants",
        subcategory=subcategory,
        color=color,
        family_key=family_key,
    )
