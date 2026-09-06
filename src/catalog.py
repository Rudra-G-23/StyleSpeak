"""Loading, filtering, sorting and pagination for the local product catalog.

Backed by Polars. Everything here operates on ``data/products/products.json``;
the app never contacts Hugging Face or the original Zalando URLs at runtime.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_JSON = PROJECT_ROOT / "data" / "products" / "products.json"

SORT_OPTIONS = (
    "Relevance",
    "Price: low to high",
    "Price: high to low",
    "Biggest discount",
    "Name (A-Z)",
)

# Canonical ordering for letter sizes so the size filter reads naturally.
_LETTER_ORDER = {
    label: index
    for index, label in enumerate(
        ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL", "6XL"]
    )
}


def _missing_data_error(path: Path) -> FileNotFoundError:
    return FileNotFoundError(
        f"{path} not found.\n"
        "Build the catalog first:\n"
        "    uv run python scripts/download_dataset.py"
    )


def load_products(path: str | Path = PRODUCTS_JSON) -> pl.DataFrame:
    """Load the cleaned catalog into a normalised Polars DataFrame."""
    path = Path(path)
    if not path.exists():
        raise _missing_data_error(path)

    with path.open(encoding="utf-8") as handle:
        records = json.load(handle)

    if not records:
        return pl.DataFrame()

    df = pl.DataFrame(records)

    for column, dtype in (
        ("original_price", pl.Float64),
        ("promotional_price", pl.Float64),
    ):
        df = df.with_columns(pl.col(column).cast(dtype, strict=False))

    df = df.with_columns(
        pl.col("promotional_price").fill_null(pl.col("original_price")).fill_null(0.0),
        pl.col("original_price").fill_null(pl.col("promotional_price")).fill_null(0.0),
        pl.col("discount_percentage").cast(pl.Int64, strict=False).fill_null(0),
        pl.col("name").fill_null(""),
        pl.col("brand").fill_null(""),
        pl.col("category").fill_null("Uncategorized"),
    )
    for column in ("sizes", "classification", "categories"):
        if column in df.columns:
            df = df.with_columns(pl.col(column).fill_null([]))
    return df


def category_options(df: pl.DataFrame) -> list[str]:
    if df.is_empty():
        return []
    return sorted(c for c in df.get_column("category").unique().to_list() if c)


def brand_options(df: pl.DataFrame) -> list[str]:
    if df.is_empty():
        return []
    return sorted(b for b in df.get_column("brand").unique().to_list() if b)


def _size_sort_key(label: str) -> tuple:
    if label in _LETTER_ORDER:
        return (0, _LETTER_ORDER[label], "")
    plain = re.fullmatch(r"\d+", label)
    if plain:
        return (1, int(label), "")
    combo = re.fullmatch(r"(\d+)\s*[xX]\s*(\d+)", label)
    if combo:
        return (2, int(combo.group(1)) * 1000 + int(combo.group(2)), "")
    return (3, 0, label.lower())


def size_options(df: pl.DataFrame) -> list[str]:
    if df.is_empty() or "sizes" not in df.columns:
        return []
    labels = (
        df.select(pl.col("sizes").explode(empty_as_null=False))
        .drop_nulls()
        .unique()
        .to_series()
        .to_list()
    )
    return sorted((str(label) for label in labels if str(label).strip()), key=_size_sort_key)


def price_bounds(df: pl.DataFrame) -> tuple[float, float]:
    if df.is_empty():
        return (0.0, 0.0)
    lo = float(df.get_column("promotional_price").min() or 0.0)
    hi = float(df.get_column("promotional_price").max() or 0.0)
    return (lo, hi)


def filter_products(
    df: pl.DataFrame,
    *,
    query: str = "",
    categories: Iterable[str] | None = None,
    brands: Iterable[str] | None = None,
    sizes: Iterable[str] | None = None,
    price_range: tuple[float, float] | None = None,
    only_discounted: bool = False,
) -> pl.DataFrame:
    """Apply search + facet filters, returning a filtered DataFrame."""
    if df.is_empty():
        return df

    predicates: list[pl.Expr] = []

    query = (query or "").strip()
    if query:
        predicates.append(
            pl.col("name").str.to_lowercase().str.contains(query.lower(), literal=True)
        )

    categories = list(categories or [])
    if categories:
        predicates.append(pl.col("category").is_in(categories))

    brands = list(brands or [])
    if brands:
        predicates.append(pl.col("brand").is_in(brands))

    sizes = list(sizes or [])
    if sizes:
        predicates.append(pl.col("sizes").list.eval(pl.element().is_in(sizes)).list.any())

    if price_range is not None:
        low, high = price_range
        predicates.append(pl.col("promotional_price").is_between(low, high))

    if only_discounted:
        predicates.append(pl.col("discount_percentage") > 0)

    if not predicates:
        return df

    combined = predicates[0]
    for predicate in predicates[1:]:
        combined = combined & predicate
    return df.filter(combined)


def sort_products(df: pl.DataFrame, sort_by: str) -> pl.DataFrame:
    if df.is_empty():
        return df
    if sort_by == "Price: low to high":
        return df.sort(["promotional_price", "sku"])
    if sort_by == "Price: high to low":
        return df.sort(["promotional_price", "sku"], descending=[True, False])
    if sort_by == "Biggest discount":
        return df.sort(["discount_percentage", "sku"], descending=[True, False])
    if sort_by == "Name (A-Z)":
        return df.sort(["name", "sku"])
    return df


def paginate(df: pl.DataFrame, page: int, page_size: int) -> tuple[pl.DataFrame, int, int, int]:
    """Return ``(page_df, clamped_page, total_pages, total_items)``."""
    total_items = df.height
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = max(1, min(int(page), total_pages))
    start = (page - 1) * page_size
    return df.slice(start, page_size), page, total_pages, total_items
