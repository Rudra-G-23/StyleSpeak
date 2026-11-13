"""Deterministic query understanding and hybrid catalog retrieval."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from . import repository
from .normalizers import COLOR_TERMS
from .schemas import SearchFilters, SearchRequest

STOP_WORDS = {
    "show",
    "me",
    "for",
    "the",
    "a",
    "an",
    "of",
    "in",
    "under",
    "over",
    "with",
    "and",
    "to",
    "options",
    "something",
}


def parse_query(query: str, base: SearchFilters | None = None) -> SearchFilters:
    filters = base or SearchFilters()
    text = query.lower().replace("€", " eur ")
    gender = filters.gender
    if re.search(r"\b(men|mens|male|him)\b", text):
        gender = "men"
    elif re.search(r"\b(women|womens|female|ladies|her)\b", text):
        gender = "women"
    color = filters.color
    for canonical, terms in COLOR_TERMS.items():
        if any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms):
            color = canonical
            break
    category = (
        "pants"
        if re.search(r"\b(pants?|trousers|jeans|joggers?|chinos?)\b", text)
        else filters.category
    )
    subcategory = filters.subcategory
    for label, terms in {
        "cargo": ("cargo",),
        "jeans": ("jeans", "denim"),
        "joggers": ("jogger",),
        "chinos": ("chino",),
        "formal": ("formal", "tailored"),
        "casual": ("casual",),
    }.items():
        if any(term in text for term in terms):
            subcategory = label
            break
    maximum = filters.max_price
    minimum = filters.min_price
    under = re.search(
        r"\b(?:under|below|less than|up to|max(?:imum)?)\s*(?:eur\s*)?(\d+(?:\.\d+)?)", text
    )
    over = re.search(r"\b(?:over|above|more than|min(?:imum)?)\s*(?:eur\s*)?(\d+(?:\.\d+)?)", text)
    between = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\b", text)
    if between:
        minimum, maximum = float(between.group(1)), float(between.group(2))
    elif under:
        maximum = float(under.group(1))
    elif over:
        minimum = float(over.group(1))
    return SearchFilters(
        gender=gender,
        category=category,
        subcategory=subcategory,
        color=color,
        min_price=minimum,
        max_price=maximum,
        size=filters.size,
        brand=filters.brand,
    )


def query_words(query: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[a-z0-9]+", query.lower())
        if len(word) > 2 and word not in STOP_WORDS
    ]


def search(session: Session, request: SearchRequest):
    filters = parse_query(request.query, request.filters)
    candidates = list(session.scalars(repository.filtered_products(session, filters)))
    if not candidates:
        return filters, []
    candidate_skus = {candidate.sku for candidate in candidates}
    words = query_words(request.query)
    lexical = repository.fts_ranked_skus(session, words, candidate_skus, request.limit)
    lexical_rank = {sku: index + 1 for index, sku in enumerate(lexical)}

    def score(product) -> tuple[float, float, str]:  # type: ignore[no-untyped-def]
        token_hits = sum(word in product.searchable_text.lower() for word in words)
        rrf = 1 / (60 + lexical_rank[product.sku]) if product.sku in lexical_rank else 0
        return (rrf + token_hits / 100, -product.price, product.sku)

    ranked = sorted(candidates, key=score, reverse=True)
    return filters, ranked[: request.limit]
