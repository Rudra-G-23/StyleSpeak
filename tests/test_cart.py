from src.cart import (
    add_to_cart,
    cart_item_count,
    cart_line_items,
    cart_subtotal,
    clear_cart,
    remove_from_cart,
    set_quantity,
)

PRODUCTS = {
    "A": {
        "name": "Alpha",
        "brand": "BrandA",
        "promotional_price": 10.0,
        "original_price": 20.0,
        "image_path": "a.jpg",
    },
    "B": {
        "name": "Beta",
        "brand": "BrandB",
        "promotional_price": None,
        "original_price": 5.5,
        "image_path": "b.jpg",
    },
}


def test_add_increments():
    cart = {}
    add_to_cart(cart, "A")
    add_to_cart(cart, "A")
    add_to_cart(cart, "B", 3)
    assert cart == {"A": 2, "B": 3}


def test_add_non_positive_is_noop():
    cart = {}
    add_to_cart(cart, "A", 0)
    add_to_cart(cart, "A", -2)
    assert cart == {}


def test_set_quantity_and_removal():
    cart = {"A": 5}
    set_quantity(cart, "A", 2)
    assert cart == {"A": 2}
    set_quantity(cart, "A", 0)
    assert cart == {}


def test_remove_and_clear():
    cart = {"A": 1, "B": 2}
    remove_from_cart(cart, "A")
    assert cart == {"B": 2}
    clear_cart(cart)
    assert cart == {}


def test_item_count():
    assert cart_item_count({"A": 2, "B": 3}) == 5
    assert cart_item_count({}) == 0


def test_line_items_resolve_price_fallback():
    cart = {"A": 2, "B": 1}
    lines = {line["sku"]: line for line in cart_line_items(cart, PRODUCTS)}
    assert lines["A"]["unit_price"] == 10.0
    assert lines["A"]["line_total"] == 20.0
    # B has no promotional_price -> falls back to original_price
    assert lines["B"]["unit_price"] == 5.5
    assert lines["B"]["line_total"] == 5.5


def test_line_items_skip_unknown_sku():
    lines = cart_line_items({"UNKNOWN": 3}, PRODUCTS)
    assert lines == []


def test_subtotal():
    assert cart_subtotal({"A": 2, "B": 1}, PRODUCTS) == 25.5
    assert cart_subtotal({}, PRODUCTS) == 0
