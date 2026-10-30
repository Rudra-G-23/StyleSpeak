from __future__ import annotations

import importlib.util
from pathlib import Path


def _importer():
    path = Path("scripts/import_web_demo.py")
    spec = importlib.util.spec_from_file_location("import_web_demo", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gender_inference_keeps_womens_products_out_of_mens_results() -> None:
    importer = _importer()

    assert importer.gender_for("CERVINIA BIB PANTS W - Ski pants") == "women"
    assert importer.gender_for("PACE BREAKER - Sports shorts") == "men"


def test_search_index_has_cosine_and_bm25_inputs() -> None:
    importer = _importer()
    products = [
        {
            "sku": "MEN-1",
            "name": "Black running shorts",
            "brand": "Brand",
            "category": "Sportswear",
            "type": "Shorts",
            "color": "black",
            "gender": "men",
        },
        {
            "sku": "WOMEN-1",
            "name": "Pink running tights W",
            "brand": "Brand",
            "category": "Sportswear",
            "type": "Tights",
            "color": "pink",
            "gender": "women",
        },
    ]

    index = importer.build_search_index(products)

    assert index["method"] == "tf-idf-cosine-plus-bm25"
    assert len(index["documents"]) == 2
    assert index["idf"]["black"] > 0
    assert index["documents"][0]["vector"]
