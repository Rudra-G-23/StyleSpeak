"""Orchestration tests for handle_user_message with the LLM call stubbed out.

These exercise the search -> results -> reference -> cart pipeline without any
network: ``parse_intent`` is replaced, and searches use only hard filters
(no ``semantic_query``) so no embedding call is made.
"""

from __future__ import annotations

import pytest

from src.assistant import handler
from src.assistant.schemas import AddToCartIntent, ReplyIntent, SearchIntent


@pytest.fixture
def state():
    return handler.AssistantState(cart={})


def _stub(monkeypatch, intent):
    monkeypatch.setattr(handler, "parse_intent", lambda text, context=None: intent)


def test_search_then_add_by_position(monkeypatch, state):
    _stub(
        monkeypatch,
        SearchIntent.model_validate(
            {"action": "search_products", "filters": {"color": "black"}, "response": "Here."}
        ),
    )
    reply = handler.handle_user_message("black things", state)
    assert reply.kind == "results" and reply.results
    assert all(r["position"] == i + 1 for i, r in enumerate(reply.results))

    pos = 2 if len(reply.results) >= 2 else 1
    target_sku = state.last_results[pos - 1]["sku"]
    _stub(
        monkeypatch,
        AddToCartIntent.model_validate({"action": "add_to_cart", "reference": {"position": pos}}),
    )
    reply2 = handler.handle_user_message(f"add the number {pos}", state)
    assert reply2.kind == "cart"
    assert state.cart == {target_sku: 1}


def test_add_without_results_is_safe(monkeypatch, state):
    _stub(
        monkeypatch,
        AddToCartIntent.model_validate({"action": "add_to_cart", "reference": {"position": 1}}),
    )
    reply = handler.handle_user_message("add the first one", state)
    assert reply.kind == "error" and state.cart == {}


def test_impossible_search_returns_info_not_crash(monkeypatch, state):
    _stub(
        monkeypatch,
        SearchIntent.model_validate({"action": "search_products", "filters": {"max_price": 0.01}}),
    )
    reply = handler.handle_user_message("free designer coats", state)
    assert reply.kind == "info" and reply.results == []


def test_respond_intent_passthrough(monkeypatch, state):
    _stub(
        monkeypatch,
        ReplyIntent.model_validate(
            {"action": "respond", "response": "I help you shop for clothes."}
        ),
    )
    reply = handler.handle_user_message("who are you", state)
    assert reply.kind == "info" and "shop" in reply.text


def test_ollama_down_is_reported(monkeypatch, state):
    from src.assistant.ollama_client import OllamaError

    def boom(text, context=None):
        raise OllamaError("connection refused")

    monkeypatch.setattr(handler, "parse_intent", boom)
    reply = handler.handle_user_message("black jackets", state)
    assert reply.kind == "error" and "unavailable" in reply.text.lower()


def test_blank_message(state):
    reply = handler.handle_user_message("   ", state)
    assert reply.kind == "error"
