"""Session-scoped conversational shopping operations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from . import repository
from .retrieval import parse_query, search
from .schemas import SearchFilters, SearchRequest


@dataclass
class ConversationState:
    filters: SearchFilters = field(default_factory=SearchFilters)
    result_skus: list[str] = field(default_factory=list)


STATES: dict[str, ConversationState] = {}
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}


def _state(session_id: str) -> ConversationState:
    return STATES.setdefault(session_id, ConversationState())


def handle_message(session: Session, session_id: str, message: str):
    state = _state(session_id)
    text = message.lower().strip()
    ordinal = next(
        (position for word, position in ORDINALS.items() if re.search(rf"\b{word}\b", text)), None
    )
    if ordinal and re.search(r"\b(show|open|select)\b", text):
        if ordinal <= len(state.result_skus):
            product = repository.get_product(session, state.result_skus[ordinal - 1])
            return (
                "select",
                f"Opening option {ordinal}.",
                [product] if product else [],
                product.sku if product else None,
            )
        return "info", f"I only have {len(state.result_skus)} current results.", [], None
    if ordinal and re.search(r"\b(add|bag|cart)\b", text):
        if ordinal > len(state.result_skus):
            return "info", f"I only have {len(state.result_skus)} current results.", [], None
        sku = state.result_skus[ordinal - 1]
        product = repository.get_product(session, sku)
        if product is None:
            return "info", "That product is no longer available in this local catalog.", [], None
        repository.add_cart_item(session, session_id, sku, None, 1)
        return "cart", f"Added {product.name} to your cart.", [], sku
    if "what" in text and "cart" in text:
        return "info", "Your cart is ready in the bag drawer.", [], None
    base = state.filters
    if "cheaper" in text and state.result_skus:
        prices = [
            repository.get_product(session, sku).price
            for sku in state.result_skus
            if repository.get_product(session, sku)
        ]
        if prices:
            base = base.model_copy(update={"max_price": min(prices)})
    parsed = parse_query(message, base)
    filters, products = search(session, SearchRequest(query=message, filters=parsed, limit=5))
    state.filters = filters
    state.result_skus = [product.sku for product in products]
    if not products:
        return "search", "I couldn't find products matching those exact constraints.", [], None
    return (
        "search",
        f"I found {len(products)} matching option{'s' if len(products) != 1 else ''}.",
        products,
        None,
    )
