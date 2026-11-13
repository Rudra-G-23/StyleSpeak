"""StyleSpeak - local Zalando product catalog.

Run with:
    streamlit run app.py

Two pages (Catalog + Cart) share a single cart in ``st.session_state``. The app
reads only local files (``data/products/products.json`` and the images under
``data/products/images/``): it never contacts Hugging Face and never depends on
the original Zalando URLs, which are kept purely as ``source_url``.
"""

from __future__ import annotations

import streamlit as st

from src.ui import ensure_session_state, logo_path, wide_logo_path

_icon = logo_path()
st.set_page_config(
    page_title="StyleSpeak Catalog",
    page_icon=_icon or ":material/storefront:",
    layout="wide",
)

ensure_session_state()

_wide = wide_logo_path()
if _wide and _icon:
    st.logo(_wide, icon_image=_icon, size="large")
elif _icon:
    st.logo(_icon, size="large")

navigation = st.navigation(
    [
        st.Page("views/catalog.py", title="Catalog", icon=":material/storefront:", default=True),
        st.Page("views/cart.py", title="Cart", icon=":material/shopping_cart:"),
    ]
)
navigation.run()
