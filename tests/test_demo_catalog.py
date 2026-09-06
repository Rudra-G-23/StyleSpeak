from src.demo_catalog import (
    apply_filters,
    detect_color,
    detect_gender,
    embedding_text,
    product_type,
)


class TestDetectColor:
    def test_colour_from_last_segment(self):
        assert detect_color("LOFOTEN STRETCH - Outdoor trousers - dk navy") == "navy"

    def test_synonym_maps_to_canonical(self):
        assert detect_color("Basic T-shirt - mustard") == "yellow"
        assert detect_color("Winter coat - charcoal melange") == "grey"
        assert detect_color("Day dress - bordeaux") == "burgundy"

    def test_multiword_token_wins_over_substring(self):
        assert detect_color("Shirt - off-white cotton") == "white"

    def test_no_colour(self):
        assert detect_color("CERVINIA - Ski pants") is None
        assert detect_color("") is None

    def test_word_boundary_not_substring(self):
        # "read" must not match "red"
        assert detect_color("READY SET - Sweatshirt - stone") == "beige"


class TestDetectGender:
    def test_category_override(self):
        assert detect_gender("AVIANA - Day dress - white", "Women Dresses") == "women"
        assert detect_gender("Polo shirt - blue", "Men T-Shirts & Polos") == "men"

    def test_w_suffix_is_women(self):
        name = "NORDIC WIND TIGHTS W - Outdoor trousers - black"
        assert detect_gender(name, "Sportswear") == "women"
        # lower-case 'w' as a stray token must NOT trigger women
        assert detect_gender("w - Shirt - navy", "Shirts") == "unisex"

    def test_women_cut_words(self):
        assert detect_gender("COMPRESSION CROP - Top - black", "Shirts") == "women"
        assert detect_gender("SUMMER - Maxi dress - red", "Shirts") == "women"

    def test_explicit_unisex_wins(self):
        assert detect_gender("PANTS UNISEX - Tracksuit bottoms - navy", "Streetwear") == "unisex"

    def test_men_token(self):
        assert detect_gender("CLASSIC MEN - Shirt - navy", "Shirts") == "men"

    def test_default_unisex(self):
        assert detect_gender("LEATHER - Jacket - brown", "Jackets") == "unisex"


def test_product_type_is_middle_segment():
    assert product_type("LOFOTEN - Outdoor jacket - black") == "Outdoor jacket"
    assert product_type("No dashes here") == ""


def test_embedding_text_includes_key_fields():
    text = embedding_text(
        {
            "name": "AVIANA - Day dress - white",
            "category": "Women Dresses",
            "color": "white",
            "gender": "women",
            "brand": "Vera Mont",
        }
    )
    assert "Day dress" in text and "white" in text and "Women Dresses" in text
    assert "Vera Mont" in text


PRODUCTS = [
    {
        "sku": "A",
        "name": "Slim fit jeans - black",
        "category": "Jeans",
        "color": "black",
        "gender": "unisex",
        "promotional_price": 40.0,
    },
    {
        "sku": "B",
        "name": "Day dress - yellow",
        "category": "Women Dresses",
        "color": "yellow",
        "gender": "women",
        "promotional_price": 90.0,
    },
    {
        "sku": "C",
        "name": "Cargo trousers - green",
        "category": "Sportswear",
        "color": "green",
        "gender": "men",
        "promotional_price": 120.0,
    },
    {
        "sku": "D",
        "name": "Waterproof jacket - black",
        "category": "Jackets",
        "color": "black",
        "gender": "unisex",
        "promotional_price": 70.0,
    },
    {
        "sku": "E",
        "name": "COMPRESSION CROP - Top - black",
        "category": "Shirts",
        "color": "black",
        "gender": "unisex",  # tagged unisex, but the name says "crop"
        "promotional_price": 30.0,
    },
]


class TestApplyFilters:
    def test_colour_filter(self):
        out = apply_filters(PRODUCTS, color="black")
        assert {p["sku"] for p in out} == {"A", "D", "E"}

    def test_price_bounds(self):
        out = apply_filters(PRODUCTS, min_price=50, max_price=100)
        assert {p["sku"] for p in out} == {"B", "D"}

    def test_category_slug_maps_to_data(self):
        out = apply_filters(PRODUCTS, category="trousers")
        assert {p["sku"] for p in out} == {"A", "C"}  # jeans + cargo trousers

    def test_gender_keeps_matching_and_cue_free_unisex(self):
        # Requested gender: keep that gender + genuinely unisex items, drop the
        # other explicit gender AND unisex items whose name carries an
        # opposite-gender cue ("crop" -> not men's wear).
        men = {p["sku"] for p in apply_filters(PRODUCTS, gender="men")}
        assert men == {"A", "C", "D"}  # C men + plain-unisex A/D; B women, E "crop" dropped
        women = {p["sku"] for p in apply_filters(PRODUCTS, gender="women")}
        assert women == {"A", "B", "D", "E"}  # B women + unisex A/D/E; C (men) dropped

    def test_generic_keyword_not_required(self):
        # keywords that do not appear anywhere collapse the set - caller must
        # pre-strip generic words (schema does). Here an unmatched word => empty.
        assert apply_filters(PRODUCTS, keywords=["tuxedo"]) == []

    def test_no_filters_returns_all(self):
        assert len(apply_filters(PRODUCTS)) == 5
