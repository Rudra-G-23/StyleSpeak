"""Persistence adapter for normalized catalog and session carts."""

from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import Select, func, select, text
from sqlalchemy.orm import Session, joinedload

from .models import Cart, CartItem, Product


def create_schema(session: Session) -> None:
    from .models import Base

    Base.metadata.create_all(session.get_bind())
    if session.get_bind().dialect.name == "sqlite":
        session.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS products_fts "
                "USING fts5(sku UNINDEXED, name, brand, searchable_text)"
            )
        )
        session.commit()


def get_product(session: Session, sku: str) -> Product | None:
    return session.get(Product, sku)


def list_products(session: Session, limit: int = 24) -> list[Product]:
    return list(session.scalars(select(Product).order_by(Product.name).limit(limit)))


def filtered_products(session: Session, filters) -> Select[tuple[Product]]:  # type: ignore[no-untyped-def]
    query = select(Product)
    if filters.gender:
        # Unisex items are appropriate for a requested gender and are disclosed in response.
        genders = [filters.gender] if filters.gender == "unisex" else [filters.gender, "unisex"]
        query = query.where(Product.gender.in_(genders))
    if filters.category:
        query = query.where(Product.category == filters.category)
    if filters.subcategory:
        query = query.where(Product.subcategory == filters.subcategory)
    if filters.color:
        query = query.where(Product.color == filters.color)
    if filters.min_price is not None:
        query = query.where(Product.price >= filters.min_price)
    if filters.max_price is not None:
        query = query.where(Product.price <= filters.max_price)
    if filters.brand:
        query = query.where(func.lower(Product.brand) == filters.brand)
    if filters.size:
        query = query.where(Product.sizes_json.like(f'%"{filters.size}"%'))
    return query


def count_filtered(session: Session, filters) -> int:  # type: ignore[no-untyped-def]
    candidates = filtered_products(session, filters).subquery()
    return int(session.scalar(select(func.count()).select_from(candidates)) or 0)


def fts_ranked_skus(
    session: Session, words: list[str], candidate_skus: set[str], limit: int
) -> list[str]:
    if not words or not candidate_skus or session.get_bind().dialect.name != "sqlite":
        return []
    expression = " OR ".join(f'"{word.replace(chr(34), "")}"' for word in words if word)
    if not expression:
        return []
    rows = session.execute(
        text(
            "SELECT sku FROM products_fts WHERE products_fts MATCH :query "
            "ORDER BY rank LIMIT :limit"
        ),
        {"query": expression, "limit": limit * 4},
    ).scalars()
    return [str(row) for row in rows if str(row) in candidate_skus][:limit]


def get_or_create_cart(session: Session, session_id: str) -> Cart:
    cart = session.scalar(select(Cart).where(Cart.session_id == session_id))
    if cart is None:
        cart = Cart(session_id=session_id)
        session.add(cart)
        session.flush()
    return cart


def cart_items(session: Session, session_id: str) -> list[CartItem]:
    cart = get_or_create_cart(session, session_id)
    session.flush()
    statement = (
        select(CartItem).where(CartItem.cart_id == cart.id).options(joinedload(CartItem.product))
    )
    return list(session.scalars(statement))


def add_cart_item(
    session: Session, session_id: str, sku: str, size: str | None, quantity: int
) -> None:
    product = get_product(session, sku)
    if product is None:
        raise KeyError("Product not found")
    sizes = json.loads(product.sizes_json)
    if size and size not in sizes:
        raise ValueError("Selected size is not available for this product")
    cart = get_or_create_cart(session, session_id)
    item = session.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.sku == sku, CartItem.size == size
        )
    )
    if item:
        item.quantity = min(10, item.quantity + quantity)
    else:
        session.add(CartItem(cart_id=cart.id, sku=sku, size=size, quantity=quantity))
    session.commit()


def update_cart_item(session: Session, session_id: str, sku: str, quantity: int) -> bool:
    cart = get_or_create_cart(session, session_id)
    items = list(
        session.scalars(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.sku == sku))
    )
    if not items:
        return False
    if quantity == 0:
        for item in items:
            session.delete(item)
    else:
        for item in items:
            item.quantity = quantity
    session.commit()
    return True


def delete_cart_item(session: Session, session_id: str, sku: str) -> bool:
    return update_cart_item(session, session_id, sku, 0)


def rebuild_fts(session: Session) -> None:
    """Refresh the SQLite lexical index after a completed ingestion batch."""
    if session.get_bind().dialect.name == "sqlite":
        session.execute(text("DELETE FROM products_fts"))
        session.execute(
            text(
                "INSERT INTO products_fts(sku, name, brand, searchable_text) "
                "SELECT sku, name, brand, searchable_text FROM products"
            )
        )


def upsert_products(
    session: Session, products: Iterable[dict], *, refresh_index: bool = True
) -> int:
    inserted = 0
    for data in products:
        session.merge(Product(**data))
        inserted += 1
    session.flush()
    if refresh_index:
        rebuild_fts(session)
    session.commit()
    return inserted
