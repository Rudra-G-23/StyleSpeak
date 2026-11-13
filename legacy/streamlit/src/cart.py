"""Pure shopping-cart logic.

The cart is a plain ``{sku: quantity}`` dict. In the Streamlit app this dict
lives in ``st.session_state`` so it survives reruns for the browser session.
Keeping the logic here (framework-free) makes it unit-testable.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

Cart = dict[str, int]


def add_to_cart(cart: Cart, sku: str, quantity: int = 1) -> Cart:
    """Add ``quantity`` of ``sku`` (increments if already present)."""
    if quantity <= 0:
        return cart
    cart[sku] = cart.get(sku, 0) + quantity
    return cart


def set_quantity(cart: Cart, sku: str, quantity: int) -> Cart:
    """Set an absolute quantity; a quantity of 0 or less removes the line."""
    if quantity <= 0:
        cart.pop(sku, None)
    else:
        cart[sku] = int(quantity)
    return cart


def remove_from_cart(cart: Cart, sku: str) -> Cart:
    cart.pop(sku, None)
    return cart


def clear_cart(cart: Cart) -> Cart:
    cart.clear()
    return cart


def cart_item_count(cart: Cart) -> int:
    """Total number of units across all lines."""
    return sum(cart.values())


def _unit_price(product: Mapping[str, Any]) -> float:
    for key in ("promotional_price", "original_price"):
        value = product.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return 0.0


def cart_line_items(
    cart: Cart, products_by_sku: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Resolve the cart against the catalog into displayable line items."""
    lines: list[dict[str, Any]] = []
    for sku, quantity in cart.items():
        product = products_by_sku.get(sku)
        if product is None:
            continue
        unit = _unit_price(product)
        lines.append(
            {
                "sku": sku,
                "name": product.get("name") or sku,
                "brand": product.get("brand") or "",
                "quantity": quantity,
                "unit_price": round(unit, 2),
                "line_total": round(unit * quantity, 2),
                "image_path": product.get("image_path") or "",
            }
        )
    return lines


def cart_subtotal(cart: Cart, products_by_sku: Mapping[str, Mapping[str, Any]]) -> float:
    """Sum of every line total."""
    return round(sum(line["line_total"] for line in cart_line_items(cart, products_by_sku)), 2)
