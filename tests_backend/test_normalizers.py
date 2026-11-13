from backend.stylespeak_api.normalizers import normalize_product
from backend.stylespeak_api.retrieval import parse_query


def test_normalizes_black_mens_cargo_query() -> None:
    filters = parse_query("Show me black cargo pants for men under €100")
    assert filters.gender == "men"
    assert filters.category == "pants"
    assert filters.subcategory == "cargo"
    assert filters.color == "black"
    assert filters.max_price == 100


def test_excludes_non_pants_and_keeps_unisex_explicit() -> None:
    assert normalize_product("CARGO TEE - T-shirt - black", "", "Shirts", "Brand") is None
    assert normalize_product("Graphic logo - Print T-shirt - jeans", "", "Shirts", "Brand") is None
    normalized = normalize_product(
        "TAB UNISEX - Cargo trousers - black", "", "Streetwear", "Santa Cruz"
    )
    assert normalized is not None
    assert normalized.gender == "unisex"
    assert normalized.subcategory == "cargo"
    assert normalized.color == "black"


def test_does_not_invent_a_mens_label_without_evidence() -> None:
    normalized = normalize_product(
        "Everyday fit - Cargo trousers - black", "", "Streetwear", "Brand"
    )
    assert normalized is not None
    assert normalized.gender == "unknown"
