"""Loading, filtering, sorting and pagination for the local product catalog.

Everything here operates on ``data/products/products.json`` - the app never
touches Hugging Face or the original Zalando URLs at runtime.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_JSON = PROJECT_ROOT / "data" / "products" / "products.json"

SORT_OPTIONS = (
    "Relevance",
    "Price: low to high",
    "Price: high to low",
    "Biggest discount",
    "Name (A-Z)",
)


def _missing_data_error(path: Path) -> FileNotFoundError:
    return FileNotFoundError(
        f"{path} not found.\n"
        "Build the catalog first:\n"
        "    uv run python scripts/download_dataset.py"
    )


def load_products(path: str | Path = PRODUCTS_JSON) -> pd.DataFrame:
    """Load the cleaned catalog into a normalised DataFrame."""
    path = Path(path)
    if not path.exists():
        raise _missing_data_error(path)

    with path.open(encoding="utf-8") as handle:
        records = json.load(handle)

    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df

    for column in ("original_price", "promotional_price"):
        df[column] = pd.to_numeric(df.get(column), errors="coerce")

    # Every card needs a price: fall back promo -> original, then 0.
    df["promotional_price"] = df["promotional_price"].fillna(df["original_price"]).fillna(0.0)
    df["original_price"] = df["original_price"].fillna(df["promotional_price"]).fillna(0.0)
    df["discount_percentage"] = (
        pd.to_numeric(df.get("discount_percentage"), errors="coerce").fillna(0).astype(int)
    )

    for column in ("name", "brand"):
        df[column] = df.get(column, "").fillna("").astype(str)
    df["category"] = df.get("category", "Uncategorized").fillna("Uncategorized").astype(str)
    for column in ("sizes", "classification"):
        df[column] = df.get(column).apply(lambda v: v if isinstance(v, list) else [])

    return df


def category_options(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    return sorted(c for c in df["category"].dropna().unique() if c)


def brand_options(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    return sorted(b for b in df["brand"].dropna().unique() if b)


def price_bounds(df: pd.DataFrame) -> tuple[float, float]:
    if df.empty:
        return (0.0, 0.0)
    lo = float(df["promotional_price"].min())
    hi = float(df["promotional_price"].max())
    return (lo, hi)


def filter_products(
    df: pd.DataFrame,
    *,
    query: str = "",
    categories: Iterable[str] | None = None,
    brands: Iterable[str] | None = None,
    price_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Apply search + facet filters, returning a filtered view."""
    out = df
    query = (query or "").strip()
    if query:
        out = out[out["name"].str.contains(query, case=False, na=False, regex=False)]

    categories = list(categories or [])
    if categories:
        out = out[out["category"].isin(categories)]

    brands = list(brands or [])
    if brands:
        out = out[out["brand"].isin(brands)]

    if price_range is not None:
        low, high = price_range
        out = out[out["promotional_price"].between(low, high)]

    return out


def sort_products(df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
    if df.empty:
        return df
    if sort_by == "Price: low to high":
        return df.sort_values("promotional_price", kind="stable")
    if sort_by == "Price: high to low":
        return df.sort_values("promotional_price", ascending=False, kind="stable")
    if sort_by == "Biggest discount":
        return df.sort_values("discount_percentage", ascending=False, kind="stable")
    if sort_by == "Name (A-Z)":
        return df.sort_values("name", kind="stable")
    return df


def paginate(df: pd.DataFrame, page: int, page_size: int) -> tuple[pd.DataFrame, int, int, int]:
    """Return ``(page_df, clamped_page, total_pages, total_items)``."""
    total_items = len(df)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = max(1, min(int(page), total_pages))
    start = (page - 1) * page_size
    return df.iloc[start : start + page_size], page, total_pages, total_items
