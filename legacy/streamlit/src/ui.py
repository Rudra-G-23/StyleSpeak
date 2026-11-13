"""Small shared UI helpers used by the Streamlit pages."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.catalog import PROJECT_ROOT

# Shown only if a product's local image file is missing (never a Hugging Face URL).
PLACEHOLDER_IMAGE = "https://placehold.co/300x430/eeeeee/999999?text=No+image"

DEFAULT_FILTERS: dict[str, Any] = {
    "query": "",
    "categories": [],
    "brands": [],
    "sizes": [],
    "price_range": None,  # (low, high); None means "no bound yet"
    "only_discounted": False,
}


def ensure_session_state() -> None:
    """Initialise session state shared across pages (cart + active filters)."""
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    if "page" not in st.session_state:
        st.session_state.page = 1
    if "filters" not in st.session_state:
        st.session_state.filters = dict(DEFAULT_FILTERS)


def euro(value: Any) -> str:
    try:
        return f"€ {float(value):,.2f}"
    except (TypeError, ValueError):
        return "€ -"


def image_src(image_path: str | None) -> str:
    """Resolve a stored relative image path to an absolute local path."""
    if image_path:
        resolved = (PROJECT_ROOT / image_path).resolve()
        if resolved.is_file():
            return str(resolved)
    return PLACEHOLDER_IMAGE


def cart_count(cart: dict[str, int]) -> int:
    return sum(cart.values())


def logo_path() -> str | None:
    path = PROJECT_ROOT / "assets" / "logo.png"
    return str(path) if path.is_file() else None


def wide_logo_path() -> str | None:
    path = PROJECT_ROOT / "assets" / "logo_wide.png"
    return str(path) if path.is_file() else None


def offer_label(discount: int) -> str:
    """Short 'good to have' offer tag for a product card."""
    if discount >= 50:
        return f"MEGA DEAL -{discount}%"
    if discount > 0:
        return f"OFFER -{discount}%"
    return ""
