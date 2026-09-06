"""StyleSpeak - local voice-powered fashion shopping assistant.

Run with:
    streamlit run app.py

Three pages (Assistant + Catalog + Cart) share a single cart in
``st.session_state``. The app reads only local files and talks only to a local
Ollama server: it never contacts Hugging Face, OpenAI, or any cloud service.
The original Zalando URLs are kept purely as ``source_url``.
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
        st.Page("views/assistant.py", title="Assistant", icon=":material/mic:", default=True),
        st.Page("views/catalog.py", title="Catalog", icon=":material/storefront:"),
        st.Page("views/cart.py", title="Cart", icon=":material/shopping_cart:"),
    ]
)
navigation.run()
