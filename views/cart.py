"""Cart page: full-size review of selected products, with images."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.cart import (
    cart_item_count,
    cart_line_items,
    cart_subtotal,
    clear_cart,
    remove_from_cart,
    set_quantity,
)
from src.catalog import PRODUCTS_JSON, load_products
from src.ui import ensure_session_state, euro, image_src

ensure_session_state()


@st.cache_data(show_spinner="Loading catalog...")
def load_catalog(path: str, mtime: float):
    return load_products(path)


try:
    mtime = Path(PRODUCTS_JSON).stat().st_mtime
except OSError:
    mtime = 0.0

try:
    df = load_catalog(str(PRODUCTS_JSON), mtime)
except FileNotFoundError as exc:
    st.title("Your Cart")
    st.error(str(exc))
    st.stop()

cart = st.session_state.cart


def _sku_lookup(skus):
    skus = list(skus)
    if df.is_empty() or not skus:
        return {}
    rows = df.filter(df["sku"].is_in(skus)).iter_rows(named=True)
    return {row["sku"]: row for row in rows}


products = _sku_lookup(cart.keys())
lines = cart_line_items(cart, products)

st.title("Your Cart")
st.page_link("views/catalog.py", label="Continue shopping", icon=":material/arrow_back:")

if not lines:
    st.info("Your cart is empty. Add products from the catalog.")
    st.stop()


def _qty_key(sku: str) -> str:
    return f"qty_{sku}"


def on_set_qty(sku: str) -> None:
    value = int(st.session_state.get(_qty_key(sku), 0))
    set_quantity(st.session_state.cart, sku, value)
    if value <= 0:
        st.session_state.pop(_qty_key(sku), None)


def on_remove(sku: str) -> None:
    remove_from_cart(st.session_state.cart, sku)
    st.session_state.pop(_qty_key(sku), None)


def on_clear() -> None:
    for sku in list(st.session_state.cart):
        st.session_state.pop(_qty_key(sku), None)
    clear_cart(st.session_state.cart)


st.caption(f"{cart_item_count(cart)} item(s) across {len(lines)} product(s)")

for line in lines:
    sku = line["sku"]
    product = products.get(sku, {})
    with st.container(border=True):
        img_col, info_col, qty_col, total_col = st.columns([1, 3, 2, 2])

        with img_col:
            st.image(image_src(product.get("image_path")), use_container_width=True)

        with info_col:
            st.markdown(f"**{line['name']}**")
            meta = " - ".join(x for x in (line["brand"], product.get("category")) if x)
            if meta:
                st.caption(meta)
            st.caption(f"SKU {sku}")
            original = product.get("original_price")
            discount = int(product.get("discount_percentage") or 0)
            if discount > 0 and original and original > line["unit_price"]:
                st.markdown(
                    f"~~{euro(original)}~~ &nbsp; **{euro(line['unit_price'])}** &nbsp; "
                    f":green-background[-{discount}%]"
                )
            else:
                st.markdown(f"**{euro(line['unit_price'])}**")

        with qty_col:
            # Seed the widget from the authoritative cart quantity every run so it
            # stays in sync even if the item was re-added from the catalog page.
            st.session_state[_qty_key(sku)] = line["quantity"]
            st.number_input(
                "Quantity",
                min_value=0,
                max_value=99,
                step=1,
                key=_qty_key(sku),
                on_change=on_set_qty,
                args=(sku,),
            )
            st.button(
                "Remove",
                key=f"rm_{sku}",
                on_click=on_remove,
                args=(sku,),
                use_container_width=True,
            )

        with total_col:
            st.markdown("Line total")
            st.subheader(euro(line["line_total"]))

st.divider()
left, right = st.columns([3, 1])
with left:
    st.button("Clear cart", on_click=on_clear, type="secondary")
with right:
    st.markdown("### Subtotal")
    st.title(euro(cart_subtotal(cart, products)))
st.caption("This is a demo catalog - checkout is not implemented.")
