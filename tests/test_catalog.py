import json

import pytest

from src.catalog import (
    brand_options,
    category_options,
    filter_products,
    load_products,
    paginate,
    price_bounds,
    sort_products,
)

SAMPLE = [
    {
        "sku": "A",
        "name": "Blue Running Shoes",
        "brand": "Nike",
        "category": "Sportswear",
        "sizes": ["40", "41"],
        "classification": ["NEW"],
        "original_price": 100.0,
        "discount_percentage": 20,
        "promotional_price": 80.0,
        "image_path": "data/products/images/A.jpg",
        "source_url": "u1",
    },
    {
        "sku": "B",
        "name": "Red Dress",
        "brand": "Mango",
        "category": "Women Dresses",
        "sizes": ["S", "M"],
        "classification": [],
        "original_price": 50.0,
        "discount_percentage": 0,
        "promotional_price": 50.0,
        "image_path": "data/products/images/B.jpg",
        "source_url": "u2",
    },
    {
        "sku": "C",
        "name": "Blue Jeans",
        "brand": "Levi's",
        "category": "Jeans",
        "sizes": ["32"],
        "classification": ["DEAL"],
        "original_price": 90.0,
        "discount_percentage": 50,
        "promotional_price": 45.0,
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
    assert len(df) == 3
    assert set(df["sku"]) == {"A", "B", "C"}
    assert df.loc[df["sku"] == "A", "sizes"].iloc[0] == ["40", "41"]


def test_load_products_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_products(tmp_path / "nope.json")


def test_option_helpers(catalog_file):
    df = load_products(catalog_file)
    assert category_options(df) == ["Jeans", "Sportswear", "Women Dresses"]
    assert brand_options(df) == ["Levi's", "Mango", "Nike"]
    assert price_bounds(df) == (45.0, 80.0)


def test_search_by_name(catalog_file):
    df = load_products(catalog_file)
    result = filter_products(df, query="blue")
    assert set(result["sku"]) == {"A", "C"}


def test_category_and_brand_filter(catalog_file):
    df = load_products(catalog_file)
    assert set(filter_products(df, categories=["Jeans"])["sku"]) == {"C"}
    assert set(filter_products(df, brands=["Nike", "Mango"])["sku"]) == {"A", "B"}


def test_price_range_filter(catalog_file):
    df = load_products(catalog_file)
    result = filter_products(df, price_range=(0, 49))
    assert set(result["sku"]) == {"C"}


def test_sort_products(catalog_file):
    df = load_products(catalog_file)
    assert list(sort_products(df, "Price: low to high")["sku"]) == ["C", "B", "A"]
    assert list(sort_products(df, "Price: high to low")["sku"]) == ["A", "B", "C"]
    assert list(sort_products(df, "Biggest discount")["sku"]) == ["C", "A", "B"]
    assert list(sort_products(df, "Name (A-Z)")["sku"]) == ["C", "A", "B"]


def test_paginate(catalog_file):
    df = load_products(catalog_file)
    page_df, page, total_pages, total = paginate(df, page=1, page_size=2)
    assert (page, total_pages, total) == (1, 2, 3)
    assert len(page_df) == 2

    page_df, page, total_pages, total = paginate(df, page=99, page_size=2)
    assert page == 2
    assert len(page_df) == 1
