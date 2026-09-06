"""Single entry point shared by the text box and the microphone.

``handle_user_message(text, state)`` is the only function ``views/assistant.py``
calls. Voice input just converts audio -> text first, then calls this exact
function, so there is one code path for both.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import ValidationError

from src.assistant.intent import parse_intent
from src.assistant.ollama_client import OllamaError
from src.assistant.resolve import resolve_reference
from src.assistant.schemas import AddToCartIntent, ReplyIntent, SearchIntent
from src.cart import add_to_cart
from src.demo_catalog import search

MAX_RESULTS = 6


@dataclass
class AssistantState:
    """The conversational memory the UI keeps in ``st.session_state``."""

    cart: dict[str, int]
    last_results: list[dict] = field(default_factory=list)
    last_filters: dict | None = None

    def context(self) -> dict:
        return {"last_results": self.last_results, "last_filters": self.last_filters}


@dataclass
class AssistantReply:
    text: str
    results: list[dict] = field(default_factory=list)
    added_sku: str | None = None
    kind: str = "info"  # info | results | cart | error


def handle_user_message(text: str, state: AssistantState) -> AssistantReply:
    """Parse the message and run the one allowed action (search or add-to-cart)."""
    text = (text or "").strip()
    if not text:
        return AssistantReply("I didn't catch that - could you say it again?", kind="error")

    try:
        intent = parse_intent(text, state.context())
    except OllamaError as exc:
        return AssistantReply(f"The local assistant model is unavailable. {exc}", kind="error")
    except (ValidationError, ValueError):
        return AssistantReply(
            'Sorry, I didn\'t understand that. Try "show me black jackets under 100" '
            'or "add the second one".',
            kind="error",
        )

    if isinstance(intent, SearchIntent):
        return _do_search(intent, state)
    if isinstance(intent, AddToCartIntent):
        return _do_add_to_cart(intent, state)
    if isinstance(intent, ReplyIntent):
        return AssistantReply(intent.response or "How can I help you shop today?", kind="info")
    return AssistantReply("Something went wrong parsing that. Please rephrase.", kind="error")


def _do_search(intent: SearchIntent, state: AssistantState) -> AssistantReply:
    f = intent.filters
    try:
        results = search(
            category=f.category,
            color=f.color,
            gender=f.gender,
            min_price=f.min_price,
            max_price=f.max_price,
            keywords=intent.keywords,
            semantic_query=intent.semantic_query,
            top_k=MAX_RESULTS,
        )
    except OllamaError as exc:
        return AssistantReply(f"Couldn't run the search: {exc}", kind="error")
    except FileNotFoundError as exc:
        return AssistantReply(str(exc), kind="error")

    state.last_results = results
    state.last_filters = {
        "category": f.category,
        "color": f.color,
        "gender": f.gender,
        "min_price": f.min_price,
        "max_price": f.max_price,
        "keywords": intent.keywords,
        "semantic_query": intent.semantic_query,
    }

    if not results:
        return AssistantReply(
            "I couldn't find anything matching that in the demo catalog. "
            "Try loosening the colour or price.",
            kind="info",
        )
    count = len(results)
    base = intent.response.strip() or (
        f"Here {'is' if count == 1 else 'are'} {count} option{'' if count == 1 else 's'}."
    )
    return AssistantReply(base, results=results, kind="results")


def _do_add_to_cart(intent: AddToCartIntent, state: AssistantState) -> AssistantReply:
    resolution = resolve_reference(intent.reference, state.last_results)
    if not resolution.ok:
        return AssistantReply(
            resolution.error or "I couldn't tell which item you meant.", kind="error"
        )

    add_to_cart(state.cart, resolution.sku, 1)
    product = resolution.product or {}
    name = product.get("name") or resolution.sku
    confirm = intent.response.strip() or f"Added {name} to your cart."
    return AssistantReply(confirm, added_sku=resolution.sku, kind="cart")
