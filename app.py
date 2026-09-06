"""StyleSpeak - local Zalando product catalog.

Run with:
    streamlit run app.py

The app reads only local files (``data/products/products.json`` and the images
under ``data/products/images/``). It never contacts Hugging Face and never
depends on the original Zalando URLs, which are kept purely as ``source_url``.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.cart import (
    add_to_cart,
    cart_item_count,
    cart_line_items,
    cart_subtotal,
    clear_cart,
    remove_from_cart,
    set_quantity,
)
from src.catalog import (
    PRODUCTS_JSON,
    PROJECT_ROOT,
    SORT_OPTIONS,
    brand_options,
    category_options,
    filter_products,
    load_products,
    paginate,
    price_bounds,
    sort_products,
)

GRID_COLUMNS = 4
PAGE_SIZE_CHOICES = [12, 24, 48, 96]
MAX_SIZES_SHOWN = 12
# Shown only if a product's local image file is missing (never a Hugging Face URL).
PLACEHOLDER = "https://placehold.co/300x430/eeeeee/999999?text=No+image"


st.set_page_config(page_title="StyleSpeak Catalog", page_icon=None, layout="wide")

# Grid polish: equal-height product cards per row and a consistent image box.
# Selectors are scoped so the cart in the sidebar is unaffected.
st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"] { align-items: stretch; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]
        > div[data-testid="stVerticalBlockBorderWrapper"] { height: 100%; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]
        > div[data-testid="stVerticalBlockBorderWrapper"] > div
        > div[data-testid="stVerticalBlock"] {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]
        div[data-testid="stVerticalBlock"]
        > div[data-testid="stElementContainer"]:last-child:has(div[data-testid="stButton"]) {
        margin-top: auto;
    }
    div[data-testid="stColumn"] div[data-testid="stImage"] img {
        height: 280px;
        object-fit: contain;
        background: #f6f6f6;
        border-radius: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Data loading (cached, busted when products.json changes)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading catalog...")
def load_catalog(path: str, mtime: float):
    return load_products(path)


def lookup_products(df, skus) -> dict:
    skus = list(skus)
    if not skus:
        return {}
    subset = df[df["sku"].isin(skus)]
    return {rec["sku"]: rec for rec in subset.to_dict("records")}


def image_src(image_path: str) -> str:
    if image_path:
        resolved = (PROJECT_ROOT / image_path).resolve()
        if resolved.is_file():
            return str(resolved)
    return PLACEHOLDER


def euro(value) -> str:
    try:
        return f"€ {float(value):,.2f}"
    except (TypeError, ValueError):
        return "€ -"


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "page" not in st.session_state:
    st.session_state.page = 1


def reset_page() -> None:
    st.session_state.page = 1


def on_add(sku: str, name: str) -> None:
    add_to_cart(st.session_state.cart, sku, 1)
    st.toast(f"Added to cart: {name}")


def on_inc(sku: str) -> None:
    set_quantity(st.session_state.cart, sku, st.session_state.cart.get(sku, 0) + 1)


def on_dec(sku: str) -> None:
    set_quantity(st.session_state.cart, sku, st.session_state.cart.get(sku, 0) - 1)


def on_remove(sku: str) -> None:
    remove_from_cart(st.session_state.cart, sku)


def on_clear() -> None:
    clear_cart(st.session_state.cart)


# --------------------------------------------------------------------------- #
# Load catalog
# --------------------------------------------------------------------------- #
try:
    mtime = Path(PRODUCTS_JSON).stat().st_mtime
except OSError:
    mtime = 0.0

try:
    df = load_catalog(str(PRODUCTS_JSON), mtime)
except FileNotFoundError as exc:
    st.title("StyleSpeak Catalog")
    st.error(str(exc))
    st.stop()

if df.empty:
    st.title("StyleSpeak Catalog")
    st.warning("The catalog is empty. Run `uv run python scripts/download_dataset.py`.")
    st.stop()


# --------------------------------------------------------------------------- #
# Sidebar - filters
# --------------------------------------------------------------------------- #
st.sidebar.title("Filters")
query = st.sidebar.text_input("Search by product name", key="f_query", on_change=reset_page)
selected_categories = st.sidebar.multiselect(
    "Category", options=category_options(df), key="f_categories", on_change=reset_page
)
selected_brands = st.sidebar.multiselect(
    "Brand", options=brand_options(df), key="f_brands", on_change=reset_page
)

low, high = price_bounds(df)
price_range = (low, high)
if high > low:
    price_range = st.sidebar.slider(
        "Promotional price (EUR)",
        min_value=float(low),
        max_value=float(high),
        value=(float(low), float(high)),
        key="f_price",
        on_change=reset_page,
    )
else:
    st.sidebar.caption(f"All products priced at {euro(low)}")

only_discounted = st.sidebar.checkbox("Only discounted", key="f_discounted", on_change=reset_page)

sort_by = st.sidebar.selectbox("Sort by", SORT_OPTIONS, key="f_sort", on_change=reset_page)
page_size = st.sidebar.selectbox(
    "Products per page", PAGE_SIZE_CHOICES, index=1, key="f_page_size", on_change=reset_page
)


# --------------------------------------------------------------------------- #
# Sidebar - cart
# --------------------------------------------------------------------------- #
cart = st.session_state.cart
cart_products = lookup_products(df, cart.keys())
lines = cart_line_items(cart, cart_products)

with st.sidebar:
    st.divider()
    st.title(f"Cart ({cart_item_count(cart)})")
    if not lines:
        st.caption("Your cart is empty. Add products from the catalog.")
    else:
        for line in lines:
            with st.container(border=True):
                st.markdown(f"**{line['name']}**")
                st.caption(f"{line['brand']} - {line['sku']}")
                c1, c2, c3 = st.columns([1, 1, 1])
                c1.button("-", key=f"dec_{line['sku']}", on_click=on_dec, args=(line["sku"],))
                c2.markdown(
                    f"<div style='text-align:center'>{line['quantity']}</div>",
                    unsafe_allow_html=True,
                )
                c3.button("+", key=f"inc_{line['sku']}", on_click=on_inc, args=(line["sku"],))
                st.caption(
                    f"{euro(line['unit_price'])} x {line['quantity']} = {euro(line['line_total'])}"
                )
                st.button(
                    "Remove", key=f"rm_{line['sku']}", on_click=on_remove, args=(line["sku"],)
                )
        st.subheader(f"Subtotal: {euro(cart_subtotal(cart, cart_products))}")
        st.button("Clear cart", on_click=on_clear, type="secondary")


# --------------------------------------------------------------------------- #
# Main - catalog grid
# --------------------------------------------------------------------------- #
st.title("StyleSpeak Catalog")

filtered = filter_products(
    df,
    query=query,
    categories=selected_categories,
    brands=selected_brands,
    price_range=price_range,
)
if only_discounted:
    filtered = filtered[filtered["discount_percentage"] > 0]

filtered = sort_products(filtered, sort_by)

page_df, current_page, total_pages, total_items = paginate(
    filtered, st.session_state.page, page_size
)
st.session_state.page = current_page

st.caption(f"{total_items:,} of {len(df):,} products - page {current_page} of {total_pages}")

if total_items == 0:
    st.info("No products match the current filters.")
    st.stop()


def _goto_page(page: int) -> None:
    st.session_state.page = max(1, min(int(page), total_pages))


def render_pagination(key_prefix: str) -> None:
    prev_col, mid_col, next_col = st.columns([1, 2, 1])
    prev_col.button(
        "Previous",
        key=f"{key_prefix}_prev",
        disabled=current_page <= 1,
        on_click=_goto_page,
        args=(current_page - 1,),
        use_container_width=True,
    )
    next_col.button(
        "Next",
        key=f"{key_prefix}_next",
        disabled=current_page >= total_pages,
        on_click=_goto_page,
        args=(current_page + 1,),
        use_container_width=True,
    )
    mid_col.markdown(
        f"<div style='text-align:center;padding-top:0.4rem'>"
        f"Page {current_page} of {total_pages}</div>",
        unsafe_allow_html=True,
    )


render_pagination("top")

records = page_df.to_dict("records")
for row_start in range(0, len(records), GRID_COLUMNS):
    cols = st.columns(GRID_COLUMNS)
    for col, product in zip(cols, records[row_start : row_start + GRID_COLUMNS], strict=False):
        with col, st.container(border=True):
            st.image(image_src(product["image_path"]), use_container_width=True)
            st.markdown(f"**{product['name'] or 'Unnamed product'}**")
            st.caption(f"{product['brand'] or 'Unknown brand'}  -  {product['category']}")

            original = product["original_price"]
            promo = product["promotional_price"]
            discount = int(product["discount_percentage"] or 0)
            if discount > 0 and promo and original and promo < original:
                st.markdown(
                    f"~~{euro(original)}~~ &nbsp; **{euro(promo)}** &nbsp; :red[-{discount}%]"
                )
            else:
                st.markdown(f"**{euro(promo or original)}**")

            classification = product.get("classification") or []
            if classification:
                st.caption(" ".join(f"`{tag}`" for tag in classification))

            sizes = [str(s) for s in (product.get("sizes") or [])]
            if not sizes:
                sizes_text = "n/a"
            elif len(sizes) > MAX_SIZES_SHOWN:
                sizes_text = (
                    ", ".join(sizes[:MAX_SIZES_SHOWN]) + f" +{len(sizes) - MAX_SIZES_SHOWN} more"
                )
            else:
                sizes_text = ", ".join(sizes)
            st.caption(f"Sizes: {sizes_text}")

            st.button(
                "Add to Cart",
                key=f"add_{product['sku']}",
                on_click=on_add,
                args=(product["sku"], product["name"] or product["sku"]),
                use_container_width=True,
            )

st.divider()
render_pagination("bottom")
