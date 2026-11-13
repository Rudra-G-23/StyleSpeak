import json

import polars as pl
import pytest

from src.catalog import (
    brand_options,
    category_options,
    filter_products,
    load_products,
    paginate,
    price_bounds,
    size_options,
    sort_products,
)

SAMPLE = [
    {
        "sku": "A",
        "name": "Blue Running Shoes",
        "brand": "Nike",
        "category": "Sportswear",
        "categories": ["Sportswear"],
        "sizes": ["40", "41"],
        "classification": ["NEW"],
        "original_price": 100.0,
        "discount_percentage": 20,
        "promotional_price": 80.0,
        "currency": "EUR",
        "image_path": "data/products/images/A.jpg",
        "source_url": "u1",
    },
    {
        "sku": "B",
        "name": "Red Dress",
        "brand": "Mango",
        "category": "Women Dresses",
        "categories": ["Women Dresses"],
        "sizes": ["S", "M"],
        "classification": [],
        "original_price": 50.0,
        "discount_percentage": 0,
        "promotional_price": 50.0,
        "currency": "EUR",
        "image_path": "data/products/images/B.jpg",
        "source_url": "u2",
    },
    {
        "sku": "C",
        "name": "Blue Jeans",
        "brand": "Levi's",
        "category": "Jeans",
        "categories": ["Jeans"],
        "sizes": ["32x32", "M"],
        "classification": ["DEAL"],
        "original_price": 90.0,
        "discount_percentage": 50,
        "promotional_price": 45.0,
        "currency": "EUR",
        "image_path": "data/products/images/C.jpg",
        "source_url": "u3",
    },
]


@pytest.fixture
def catalog_file(tmp_path):
    path = tmp_path / "products.json"
    path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    return path


def test_load_products(catalog_file):
    df = load_products(catalog_file)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 3
    assert set(df["sku"].to_list()) == {"A", "B", "C"}
    assert df.filter(pl.col("sku") == "A")["sizes"].to_list()[0] == ["40", "41"]


def test_load_products_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_products(tmp_path / "nope.json")


def test_option_helpers(catalog_file):
    df = load_products(catalog_file)
    assert category_options(df) == ["Jeans", "Sportswear", "Women Dresses"]
    assert brand_options(df) == ["Levi's", "Mango", "Nike"]
    assert price_bounds(df) == (45.0, 80.0)


def test_size_options_natural_order(catalog_file):
    df = load_products(catalog_file)
    # letter sizes before plain numbers before WxL combos
    assert size_options(df) == ["S", "M", "40", "41", "32x32"]


def test_search_by_name_case_insensitive(catalog_file):
    df = load_products(catalog_file)
    result = filter_products(df, query="BLUE")
    assert set(result["sku"].to_list()) == {"A", "C"}


def test_category_and_brand_filter(catalog_file):
    df = load_products(catalog_file)
    assert set(filter_products(df, categories=["Jeans"])["sku"].to_list()) == {"C"}
    assert set(filter_products(df, brands=["Nike", "Mango"])["sku"].to_list()) == {"A", "B"}


def test_size_filter_matches_any(catalog_file):
    df = load_products(catalog_file)
    assert set(filter_products(df, sizes=["M"])["sku"].to_list()) == {"B", "C"}
    assert set(filter_products(df, sizes=["40"])["sku"].to_list()) == {"A"}


def test_price_range_filter(catalog_file):
    df = load_products(catalog_file)
    result = filter_products(df, price_range=(0, 49))
    assert set(result["sku"].to_list()) == {"C"}


def test_only_discounted(catalog_file):
    df = load_products(catalog_file)
    assert set(filter_products(df, only_discounted=True)["sku"].to_list()) == {"A", "C"}


def test_combined_filters(catalog_file):
    df = load_products(catalog_file)
    result = filter_products(df, query="blue", sizes=["M"], only_discounted=True)
    assert result["sku"].to_list() == ["C"]


def test_sort_products(catalog_file):
    df = load_products(catalog_file)
    assert sort_products(df, "Price: low to high")["sku"].to_list() == ["C", "B", "A"]
    assert sort_products(df, "Price: high to low")["sku"].to_list() == ["A", "B", "C"]
    assert sort_products(df, "Biggest discount")["sku"].to_list() == ["C", "A", "B"]
    assert sort_products(df, "Name (A-Z)")["sku"].to_list() == ["C", "A", "B"]


def test_paginate(catalog_file):
    df = load_products(catalog_file)
    page_df, page, total_pages, total = paginate(df, page=1, page_size=2)
    assert (page, total_pages, total) == (1, 2, 3)
    assert page_df.height == 2

    page_df, page, total_pages, total = paginate(df, page=99, page_size=2)
    assert page == 2
    assert page_df.height == 1
