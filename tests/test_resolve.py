from src.assistant.resolve import resolve_reference
from src.assistant.schemas import CartReference

RESULTS = [
    {"position": 1, "sku": "S1", "name": "Slim fit jeans - black", "color": "black"},
    {"position": 2, "sku": "S2", "name": "Linen shirt - yellow", "color": "yellow"},
    {"position": 3, "sku": "S3", "name": "Rain jacket - yellow", "color": "yellow"},
    {"position": 4, "sku": "S4", "name": "Wool coat - navy", "color": "navy"},
]


def test_position_reference():
    res = resolve_reference(CartReference(position=2), RESULTS)
    assert res.ok and res.sku == "S2"


def test_position_out_of_range():
    res = resolve_reference(CartReference(position=9), RESULTS)
    assert not res.ok and "9" in res.error


def test_unique_colour_reference():
    res = resolve_reference(CartReference(color="navy"), RESULTS)
    assert res.ok and res.sku == "S4"


def test_ambiguous_colour_is_not_guessed():
    res = resolve_reference(CartReference(color="yellow"), RESULTS)
    assert not res.ok
    assert "2" in res.error and "which" in res.error.lower()


def test_name_reference():
    res = resolve_reference(CartReference(product_name="wool coat"), RESULTS)
    assert res.ok and res.sku == "S4"


def test_name_token_fallback():
    res = resolve_reference(CartReference(product_name="slim jeans"), RESULTS)
    assert res.ok and res.sku == "S1"


def test_no_results_on_screen():
    res = resolve_reference(CartReference(position=1), [])
    assert not res.ok and "no results" in res.error.lower()


def test_bare_reference_single_result_ok():
    res = resolve_reference(CartReference(), RESULTS[:1])
    assert res.ok and res.sku == "S1"


def test_bare_reference_many_results_asks():
    res = resolve_reference(CartReference(), RESULTS)
    assert not res.ok and "which one" in res.error.lower()
