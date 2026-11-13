"""Catalog page: filterable, paginated product grid with Add-to-Cart."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.cart import add_to_cart, cart_subtotal
from src.catalog import (
    PRODUCTS_JSON,
    SORT_OPTIONS,
    brand_options,
    category_options,
    filter_products,
    load_products,
    paginate,
    price_bounds,
    size_options,
    sort_products,
)
from src.ui import (
    DEFAULT_FILTERS,
    cart_count,
    ensure_session_state,
    euro,
    image_src,
    offer_label,
)

GRID_COLUMNS = 4
PAGE_SIZE_CHOICES = [12, 24, 48, 96]

ensure_session_state()

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
        height: 300px;
        object-fit: contain;
        background: #f6f6f6;
        border-radius: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Data (cached; busts when products.json changes)
# --------------------------------------------------------------------------- #
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
    st.title("StyleSpeak Catalog")
    st.error(str(exc))
    st.stop()

if df.is_empty():
    st.title("StyleSpeak Catalog")
    st.warning("The catalog is empty. Run `uv run python scripts/download_dataset.py`.")
    st.stop()

price_lo, price_hi = price_bounds(df)


# --------------------------------------------------------------------------- #
# Sidebar - cart pointer (kept above the filters) then the filter form
# --------------------------------------------------------------------------- #
def _sku_lookup(skus):
    skus = list(skus)
    if not skus:
        return {}
    rows = df.filter(df["sku"].is_in(skus)).iter_rows(named=True)
    return {row["sku"]: row for row in rows}


cart = st.session_state.cart
with st.sidebar:
    with st.container(border=True):
        st.markdown("#### Cart")
        st.caption(
            f"{cart_count(cart)} item(s) - {euro(cart_subtotal(cart, _sku_lookup(cart.keys())))}"
        )
        st.caption("Your cart lives here across pages. Open it to review items and images.")
        st.page_link("views/cart.py", label="Open cart", icon=":material/shopping_cart:")

    st.divider()

    active = st.session_state.filters
    with st.form("filter_form", border=False):
        st.subheader("Filters")
        f_query = st.text_input("Search by product name", value=active["query"])
        f_categories = st.multiselect(
            "Category", options=category_options(df), default=active["categories"]
        )
        f_brands = st.multiselect("Brand", options=brand_options(df), default=active["brands"])
        f_sizes = st.multiselect("Size", options=size_options(df), default=active["sizes"])

        default_range = active["price_range"] or (price_lo, price_hi)
        if price_hi > price_lo:
            f_price = st.slider(
                "Promotional price (EUR)",
                min_value=float(price_lo),
                max_value=float(price_hi),
                value=(float(default_range[0]), float(default_range[1])),
            )
        else:
            f_price = (price_lo, price_hi)
            st.caption(f"All products priced at {euro(price_lo)}")

        f_discounted = st.checkbox("Only discounted", value=active["only_discounted"])

        apply_col, reset_col = st.columns(2)
        applied = apply_col.form_submit_button("Apply", type="primary", use_container_width=True)
        reset = reset_col.form_submit_button("Reset", use_container_width=True)

    if applied:
        st.session_state.filters = {
            "query": f_query,
            "categories": f_categories,
            "brands": f_brands,
            "sizes": f_sizes,
            "price_range": [float(f_price[0]), float(f_price[1])],
            "only_discounted": f_discounted,
        }
        st.session_state.page = 1
        st.rerun()
    if reset:
        st.session_state.filters = dict(DEFAULT_FILTERS)
        st.session_state.page = 1
        st.rerun()

    st.divider()
    sort_by = st.selectbox("Sort by", SORT_OPTIONS, key="f_sort")
    page_size = st.selectbox("Products per page", PAGE_SIZE_CHOICES, index=1, key="f_page_size")


# --------------------------------------------------------------------------- #
# Main - results grid
# --------------------------------------------------------------------------- #
st.title("StyleSpeak Catalog")

active = st.session_state.filters
filtered = filter_products(
    df,
    query=active["query"],
    categories=active["categories"],
    brands=active["brands"],
    sizes=active["sizes"],
    price_range=tuple(active["price_range"]) if active["price_range"] else None,
    only_discounted=active["only_discounted"],
)
filtered = sort_products(filtered, sort_by)

page_df, current_page, total_pages, total_items = paginate(
    filtered, st.session_state.page, page_size
)
st.session_state.page = current_page

applied_bits = []
if active["query"]:
    applied_bits.append(f'name "{active["query"]}"')
if active["categories"]:
    applied_bits.append(f"{len(active['categories'])} category")
if active["brands"]:
    applied_bits.append(f"{len(active['brands'])} brand")
if active["sizes"]:
    applied_bits.append(f"{len(active['sizes'])} size")
if active["only_discounted"]:
    applied_bits.append("discounted only")
summary = " | ".join(applied_bits) if applied_bits else "no filters applied"
st.caption(
    f"{total_items:,} of {df.height:,} products - page {current_page} of {total_pages}  ({summary})"
)

if total_items == 0:
    st.info("No products match the current filters. Adjust them and press Apply.")
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


def on_add(sku: str, name: str) -> None:
    add_to_cart(st.session_state.cart, sku, 1)
    st.toast(f"Added to cart: {name}")


render_pagination("top")

records = list(page_df.iter_rows(named=True))
for row_start in range(0, len(records), GRID_COLUMNS):
    cols = st.columns(GRID_COLUMNS)
    for col, product in zip(cols, records[row_start : row_start + GRID_COLUMNS], strict=False):
        with col, st.container(border=True):
            st.image(image_src(product["image_path"]), use_container_width=True)
            st.markdown(f"**{product['name'] or 'Unnamed product'}**")

            original = product["original_price"]
            promo = product["promotional_price"]
            discount = int(product["discount_percentage"] or 0)
            if discount > 0 and promo and original and promo < original:
                st.markdown(f"~~{euro(original)}~~ &nbsp; **{euro(promo)}**")
                st.markdown(f":green-background[{offer_label(discount)}]")
            else:
                st.markdown(f"**{euro(promo or original)}**")

            st.button(
                "Add to Cart",
                key=f"add_{product['sku']}",
                on_click=on_add,
                args=(product["sku"], product["name"] or product["sku"]),
                use_container_width=True,
            )

st.divider()
render_pagination("bottom")
