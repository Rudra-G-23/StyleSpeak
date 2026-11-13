from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.stylespeak_api import conversation, repository
from backend.stylespeak_api.database import get_session, make_engine
from backend.stylespeak_api.main import app
from backend.stylespeak_api.models import Base


def seeded_client(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository.create_schema(session)
        repository.upsert_products(
            session,
            [
                {
                    "sku": "CARGO-BLACK",
                    "family_key": "cargo",
                    "name": "Utility cargo trousers - black",
                    "brand": "North",
                    "category": "pants",
                    "subcategory": "cargo",
                    "gender": "men",
                    "color": "black",
                    "sizes_json": '["M", "L"]',
                    "price": 79.95,
                    "original_price": 99.95,
                    "currency": "EUR",
                    "image_path": "missing.jpg",
                    "source_url": "",
                    "searchable_text": "utility cargo trousers black men",
                },
                {
                    "sku": "CARGO-NAVY",
                    "family_key": "cargo",
                    "name": "Utility cargo trousers - navy",
                    "brand": "North",
                    "category": "pants",
                    "subcategory": "cargo",
                    "gender": "men",
                    "color": "blue",
                    "sizes_json": '["M"]',
                    "price": 69.95,
                    "original_price": 69.95,
                    "currency": "EUR",
                    "image_path": "missing.jpg",
                    "source_url": "",
                    "searchable_text": "utility cargo trousers navy men",
                },
                {
                    "sku": "JEAN-BLACK",
                    "family_key": "jean",
                    "name": "Straight jeans - black",
                    "brand": "Denim",
                    "category": "pants",
                    "subcategory": "jeans",
                    "gender": "men",
                    "color": "black",
                    "sizes_json": '["32"]',
                    "price": 59.95,
                    "original_price": 59.95,
                    "currency": "EUR",
                    "image_path": "missing.jpg",
                    "source_url": "",
                    "searchable_text": "straight jeans black men",
                },
            ],
        )

    def override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override
    conversation.STATES.clear()
    return TestClient(app)


def test_search_hard_filters_and_cart_reference(tmp_path) -> None:
    with seeded_client(tmp_path) as client:
        headers = {"X-StyleSpeak-Session": "test-session"}
        response = client.post(
            "/api/search", json={"query": "black men's cargo pants under €100"}, headers=headers
        )
        assert response.status_code == 200
        assert [product["sku"] for product in response.json()["products"]] == ["CARGO-BLACK"]
        assert response.json()["total"] == 1
        assert (
            client.post(
                "/api/chat", json={"message": "black cargo pants under 100"}, headers=headers
            ).status_code
            == 200
        )
        add = client.post(
            "/api/chat", json={"message": "add the first one to my cart"}, headers=headers
        )
        assert add.status_code == 200
        assert add.json()["action"] == "cart"
        assert client.get("/api/cart", headers=headers).json()["item_count"] == 1


def test_invalid_size_is_rejected(tmp_path) -> None:
    with seeded_client(tmp_path) as client:
        response = client.post(
            "/api/cart/items",
            json={"sku": "CARGO-BLACK", "size": "XS"},
            headers={"X-StyleSpeak-Session": "size-test"},
        )
        assert response.status_code == 422
