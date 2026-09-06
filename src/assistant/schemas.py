"""Pydantic schema for the LLM's structured output.

The model is only ever an intent parser. Its raw JSON is validated here before
any Python business logic runs - an invalid or surprising payload can never
reach the cart. Unknown ``action`` values or malformed fields raise
``ValidationError``, which the handler turns into a safe "I didn't catch that".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Category slugs the model is allowed to use (mapped to real data in
# ``src.demo_catalog._CATEGORY_MATCHERS``).
CATEGORY_SLUGS = (
    "shirt",
    "t-shirt",
    "jacket",
    "coat",
    "dress",
    "jeans",
    "trousers",
    "sportswear",
    "streetwear",
)
GENDERS = ("men", "women", "unisex")

# Words the model sometimes emits as "keywords" that carry no filtering signal;
# an AND-match on these would wrongly empty every result set.
_GENERIC_KEYWORDS = frozenset(
    {
        "clothes",
        "clothing",
        "apparel",
        "fashion",
        "outfit",
        "outfits",
        "wear",
        "garment",
        "garments",
        "item",
        "items",
        "thing",
        "things",
        "something",
        "anything",
        "stuff",
        "piece",
        "pieces",
        "option",
        "options",
        "products",
        "product",
        "style",
        "styles",
        "look",
        "looks",
        "one",
        "ones",
        "some",
    }
)


class SearchFilters(BaseModel):
    model_config = {"extra": "ignore"}

    category: str | None = None
    color: str | None = None
    gender: str | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)

    @field_validator("category", "color", "gender", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator("category")
    @classmethod
    def _known_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        aliases = {
            "tshirt": "t-shirt",
            "tee": "t-shirt",
            "polo": "t-shirt",
            "pants": "trousers",
            "trouser": "trousers",
            "denim": "jeans",
            "jacket": "jacket",
            "coats": "coat",
            "dresses": "dress",
        }
        value = aliases.get(value, value)
        return value if value in CATEGORY_SLUGS else None

    @field_validator("gender")
    @classmethod
    def _known_gender(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = {
            "man": "men",
            "male": "men",
            "woman": "women",
            "female": "women",
            "ladies": "women",
        }.get(value, value)
        return value if value in GENDERS else None


class SearchIntent(BaseModel):
    model_config = {"extra": "ignore"}

    action: Literal["search_products"]
    filters: SearchFilters = Field(default_factory=SearchFilters)
    keywords: list[str] = Field(default_factory=list)
    semantic_query: str = ""
    response: str = ""

    @field_validator("keywords", mode="before")
    @classmethod
    def _clean_keywords(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned = []
        for item in value:
            token = str(item).strip().lower()
            if token and token not in _GENERIC_KEYWORDS and len(token) > 1:
                cleaned.append(token)
        return cleaned[:6]


class CartReference(BaseModel):
    model_config = {"extra": "ignore"}

    position: int | None = Field(default=None, ge=1, le=50)
    color: str | None = None
    product_name: str | None = None

    @field_validator("color", "product_name", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class AddToCartIntent(BaseModel):
    model_config = {"extra": "ignore"}

    action: Literal["add_to_cart"]
    reference: CartReference = Field(default_factory=CartReference)
    response: str = ""


class ReplyIntent(BaseModel):
    """Neither a search nor a cart action - just say something back."""

    model_config = {"extra": "ignore"}

    action: Literal["respond"]
    response: str = ""


Intent = SearchIntent | AddToCartIntent | ReplyIntent
