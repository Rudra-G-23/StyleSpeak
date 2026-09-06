import pytest
from pydantic import ValidationError

from src.assistant.schemas import (
    AddToCartIntent,
    ReplyIntent,
    SearchIntent,
)


class TestSearchIntent:
    def test_minimal_payload_fills_defaults(self):
        intent = SearchIntent.model_validate({"action": "search_products"})
        assert intent.filters.category is None
        assert intent.keywords == []
        assert intent.semantic_query == ""

    def test_blank_strings_become_none(self):
        intent = SearchIntent.model_validate(
            {"action": "search_products", "filters": {"category": "", "color": "  "}}
        )
        assert intent.filters.category is None
        assert intent.filters.color is None

    def test_category_alias_and_unknown(self):
        good = SearchIntent.model_validate(
            {"action": "search_products", "filters": {"category": "pants"}}
        )
        assert good.filters.category == "trousers"
        unknown = SearchIntent.model_validate(
            {"action": "search_products", "filters": {"category": "hats"}}
        )
        assert unknown.filters.category is None

    def test_generic_keywords_are_stripped(self):
        intent = SearchIntent.model_validate(
            {"action": "search_products", "keywords": ["clothes", "something", "hoodie"]}
        )
        assert intent.keywords == ["hoodie"]

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            SearchIntent.model_validate({"action": "search_products", "filters": {"max_price": -5}})

    def test_gender_normalised(self):
        intent = SearchIntent.model_validate(
            {"action": "search_products", "filters": {"gender": "ladies"}}
        )
        assert intent.filters.gender == "women"

    def test_wrong_action_rejected(self):
        with pytest.raises(ValidationError):
            SearchIntent.model_validate({"action": "add_to_cart"})


class TestAddToCartIntent:
    def test_position_reference(self):
        intent = AddToCartIntent.model_validate(
            {"action": "add_to_cart", "reference": {"position": 2}}
        )
        assert intent.reference.position == 2

    def test_position_zero_rejected(self):
        with pytest.raises(ValidationError):
            AddToCartIntent.model_validate({"action": "add_to_cart", "reference": {"position": 0}})

    def test_extra_fields_ignored(self):
        intent = AddToCartIntent.model_validate(
            {"action": "add_to_cart", "reference": {"position": 1, "size": "M"}}
        )
        assert intent.reference.position == 1


def test_reply_intent():
    intent = ReplyIntent.model_validate({"action": "respond", "response": "Hi!"})
    assert intent.response == "Hi!"
