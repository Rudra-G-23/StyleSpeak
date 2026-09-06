"""Turn a user utterance into a validated :data:`Intent`.

Pipeline:  utterance (+ short context)  ->  Ollama JSON  ->  Pydantic  ->  Intent

The model never touches cart state directly; it only fills in this schema.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from src.assistant.ollama_client import chat_json
from src.assistant.schemas import (
    AddToCartIntent,
    Intent,
    ReplyIntent,
    SearchIntent,
)

SYSTEM_PROMPT = """\
You are the intent parser for a local fashion shopping assistant. You do NOT \
chat. You read the shopper's latest message and reply with ONE JSON object and \
nothing else.

Catalog facts:
- Fashion only, English only. Prices are in EUR.
- category is one of: shirt, t-shirt, jacket, coat, dress, jeans, trousers, \
sportswear, streetwear. Use null if unclear.
- color is a single common word (black, white, grey, blue, navy, red, green, \
yellow, orange, pink, purple, brown, beige, burgundy, teal, gold) or null.
- gender is men, women, or unisex, or null.

Choose exactly one action:

1) "search_products" - the shopper wants to see products, or refine/repeat a \
previous search (e.g. "show black pants", "something cheaper", "similar but in \
blue", "a casual outfit for a birthday dinner under 80").
   Shape:
   {"action":"search_products",
    "filters":{"category":null,"color":null,"gender":null,"min_price":null,"max_price":null},
    "keywords":[],
    "semantic_query":"short description of the vibe/occasion for similarity search",
    "response":"one short friendly sentence"}
   Rules:
   - Put hard constraints (colour, category, price, gender) in "filters".
   - "under 80" -> max_price 80. "over 40" -> min_price 40. "40 to 80" -> both.
   - "keywords" holds ONLY concrete garment nouns that are not a category \
(e.g. "pants","hoodie","shorts","blazer"). NEVER put generic words like \
"clothes","outfit","something","items" in keywords - leave it [].
   - "semantic_query" describes the occasion/feel ("smart casual dinner", \
"comfortable for long travel"). Leave "" for plain lookups like "black shirts".
   - For refinements, RE-STATE the full intended filters, adjusted.

2) "add_to_cart" - the shopper refers to something already shown \
("add the second one", "add the yellow one", "put the denim jacket in my cart").
   Shape:
   {"action":"add_to_cart",
    "reference":{"position":null,"color":null,"product_name":null},
    "response":"one short confirmation sentence"}
   Rules:
   - Ordinal words -> position number: first=1, second=2, third=3, last=<count>.
   - "the yellow one" -> color:"yellow". "the linen shirt" -> product_name:"linen shirt".

3) "respond" - anything else (greeting, unclear, off-topic).
   Shape: {"action":"respond","response":"one short helpful sentence"}

Output ONLY the JSON object.
"""

_FEWSHOT: list[tuple[str, dict]] = [
    (
        "show me black pants under 60",
        {
            "action": "search_products",
            "filters": {
                "category": "trousers",
                "color": "black",
                "gender": None,
                "min_price": None,
                "max_price": 60,
            },
            "keywords": ["pants"],
            "semantic_query": "",
            "response": "Here are some black trousers under 60 euros.",
        },
    ),
    (
        "i'm going to a friend's birthday dinner, something casual under 80",
        {
            "action": "search_products",
            "filters": {
                "category": None,
                "color": None,
                "gender": None,
                "min_price": None,
                "max_price": 80,
            },
            "keywords": [],
            "semantic_query": "casual smart outfit for a birthday dinner",
            "response": "A few relaxed options for the dinner, all under 80 euros.",
        },
    ),
    (
        "add the second one to my cart",
        {
            "action": "add_to_cart",
            "reference": {"position": 2, "color": None, "product_name": None},
            "response": "Added the second item to your cart.",
        },
    ),
    (
        "add the yellow one",
        {
            "action": "add_to_cart",
            "reference": {"position": None, "color": "yellow", "product_name": None},
            "response": "Adding the yellow one to your cart.",
        },
    ),
]


def _context_block(context: dict | None) -> str:
    """Compact, model-readable summary of what is currently on screen."""
    if not context:
        return "No previous results yet."
    lines = []
    last_filters = context.get("last_filters")
    if last_filters:
        lines.append(f"Previous search filters: {json.dumps(last_filters, default=str)}")
    results = context.get("last_results") or []
    if results:
        lines.append(f"Currently shown ({len(results)} items):")
        for item in results:
            lines.append(
                f"  {item['position']}. {item.get('name', '')} "
                f"[{item.get('color') or '?'}, EUR {item.get('promotional_price', '?')}]"
            )
    return "\n".join(lines) if lines else "No previous results yet."


def build_messages(text: str, context: dict | None) -> tuple[str, str]:
    examples = "\n".join(
        f'Example - user: "{utterance}"\n{json.dumps(payload)}' for utterance, payload in _FEWSHOT
    )
    user = (
        f"{examples}\n\n"
        f"--- Current screen ---\n{_context_block(context)}\n\n"
        f'Now parse this message:\nuser: "{text.strip()}"'
    )
    return SYSTEM_PROMPT, user


def parse_intent(text: str, context: dict | None = None) -> Intent:
    """Parse one utterance. Raises ``OllamaError`` or ``ValidationError``."""
    system, user = build_messages(text, context)
    raw = chat_json(system, user)
    action = raw.get("action")
    if action == "search_products":
        return SearchIntent.model_validate(raw)
    if action == "add_to_cart":
        return AddToCartIntent.model_validate(raw)
    if action == "respond":
        return ReplyIntent.model_validate(raw)
    raise ValidationError.from_exception_data(
        "Intent", [{"type": "value_error", "loc": ("action",), "input": action}]
    )
