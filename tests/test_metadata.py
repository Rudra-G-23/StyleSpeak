from src.metadata import (
    clean_row,
    parse_discount,
    parse_price,
    parse_sizes,
    parse_string_list,
    reconcile_pricing,
    sanitize_sku,
)


class TestParsePrice:
    def test_european_format_with_nbsp_and_euro(self):
        assert parse_price("89,99\xa0€") == 89.99

    def test_thousands_separator(self):
        assert parse_price("1.234,56 €") == 1234.56

    def test_plain_integer(self):
        assert parse_price("119 €") == 119.0

    def test_none_and_empty(self):
        assert parse_price(None) is None
        assert parse_price("") is None
        assert parse_price("None") is None

    def test_garbage(self):
        assert parse_price("price on request") is None


class TestParseDiscount:
    def test_simple(self):
        assert parse_discount("-50%") == 50

    def test_up_to_prefix(self):
        assert parse_discount("up to -20%") == 20

    def test_odd_percentage(self):
        assert parse_discount("-31%") == 31

    def test_missing(self):
        assert parse_discount(None) is None
        assert parse_discount("None") is None
        assert parse_discount("") is None


class TestReconcilePricing:
    def test_both_missing_uses_original(self):
        assert reconcile_pricing(100.0, None, None) == (100.0, 0, 100.0)

    def test_discount_only_computes_promo(self):
        original, discount, promo = reconcile_pricing(100.0, 30, None)
        assert (original, discount) == (100.0, 30)
        assert promo == 70.0

    def test_promo_only_computes_discount(self):
        original, discount, promo = reconcile_pricing(100.0, None, 75.0)
        assert (original, promo) == (100.0, 75.0)
        assert discount == 25

    def test_both_present_kept(self):
        assert reconcile_pricing(89.99, 20, 71.99) == (89.99, 20, 71.99)

    def test_negative_discount_clamped(self):
        _, discount, _ = reconcile_pricing(50.0, None, 60.0)
        assert discount == 0

    def test_original_missing_falls_back_to_promo(self):
        original, _, promo = reconcile_pricing(None, None, 40.0)
        assert original == 40.0 and promo == 40.0


class TestParseLists:
    def test_string_list(self):
        assert parse_string_list("['NEW']") == ["NEW"]
        assert parse_string_list("[]") == []
        assert parse_string_list(None) == []

    def test_sizes_extraction_and_dedup(self):
        raw = "[{'size': '36', 'sku': 'a'}, {'size': '38', 'sku': 'b'}, {'size': '36', 'sku': 'c'}]"
        assert parse_sizes(raw) == ["36", "38"]

    def test_sizes_empty(self):
        assert parse_sizes("[]") == []


class TestSanitizeSku:
    def test_keeps_safe_characters(self):
        assert sanitize_sku("00E21A003-Q11") == "00E21A003-Q11"

    def test_replaces_unsafe(self):
        assert sanitize_sku("AB/CD 12:34") == "AB-CD-12-34"

    def test_no_path_traversal(self):
        cleaned = sanitize_sku("../../etc/passwd")
        assert "/" not in cleaned and not cleaned.startswith(".")

    def test_empty_falls_back_to_index(self):
        assert sanitize_sku("", 7) == "row-7"
        assert sanitize_sku(None, 7) == "row-7"


class TestCleanRow:
    def test_full_row(self):
        raw = {
            "sku": "00E21A003-Q11",
            "name": "  NORDIC WIND TIGHTS  ",
            "brand": "Swedemount",
            "category": "['Sportswear']",
            "url": "https://en.zalando.de/x.html",
            "sizes": "[{'size': '36', 'sku': 'a'}, {'size': '38', 'sku': 'b'}]",
            "classification": "['NEW']",
            "original_price": "89,99\xa0€",
            "discount_percentage": None,
            "promotional_price": None,
        }
        record = clean_row(raw, 0, "data/products/images/00E21A003-Q11.jpg")
        assert record["sku"] == "00E21A003-Q11"
        assert record["name"] == "NORDIC WIND TIGHTS"
        assert record["category"] == "Sportswear"
        assert record["categories"] == ["Sportswear"]
        assert record["sizes"] == ["36", "38"]
        assert record["classification"] == ["NEW"]
        assert record["original_price"] == 89.99
        assert record["discount_percentage"] == 0
        assert record["promotional_price"] == 89.99
        assert record["currency"] == "EUR"
        assert record["image_path"] == "data/products/images/00E21A003-Q11.jpg"
        assert record["source_url"] == "https://en.zalando.de/x.html"

    def test_discounted_row(self):
        raw = {
            "sku": "X",
            "name": "Y",
            "brand": "Z",
            "category": "['Jeans']",
            "url": "u",
            "sizes": "[]",
            "classification": "['DEAL']",
            "original_price": "129,00\xa0€",
            "discount_percentage": "-50%",
            "promotional_price": "64,00\xa0€",
        }
        record = clean_row(raw, 1, "p.jpg")
        assert record["original_price"] == 129.0
        assert record["discount_percentage"] == 50
        assert record["promotional_price"] == 64.0

    def test_missing_sku_uses_fallback(self):
        raw = {
            "sku": "",
            "name": "n",
            "brand": "b",
            "category": "[]",
            "url": "",
            "sizes": "[]",
            "classification": "[]",
            "original_price": "10 €",
            "discount_percentage": None,
            "promotional_price": None,
        }
        record = clean_row(raw, 42, "p.jpg")
        assert record["sku"] == "row-42"
        assert record["category"] == "Uncategorized"
