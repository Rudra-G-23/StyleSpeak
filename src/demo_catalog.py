"""Small curated demo catalog for the voice shopping assistant.

The full catalog (``data/products/products.json``, ~192k rows) powers the manual
filter grid in ``views/catalog.py``. The assistant works instead over a tiny
curated slice - ``data/products/catalog_demo.json`` - built once by
``scripts/build_demo_catalog.py``. Keeping it small (~200 products) means:

* MiniLM embeddings fit in a few hundred KB and are precomputed to ``.npy``.
* The LLM only ever reasons about a handful of results at a time.
* Cosine similarity over the whole slice is instant, so no vector database.

Every product keeps its original ``sku`` so the assistant adds the *same*
identifier the manual catalog and ``src/cart.py`` already use.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from src.config import (
    DEMO_CATALOG_PATH,
    DEMO_EMBEDDINGS_PATH,
)

# --------------------------------------------------------------------------- #
# Colour + gender extraction (the raw data has neither as a field)
# --------------------------------------------------------------------------- #
# Canonical colour -> the raw tokens (word-boundary matched) that map to it.
_COLOR_SYNONYMS: dict[str, tuple[str, ...]] = {
    "black": ("black", "jet"),
    "white": ("white", "offwhite", "off-white", "ecru", "ivory", "chalk", "snow"),
    "grey": ("grey", "gray", "charcoal", "anthracite", "graphite", "melange", "silver"),
    "blue": ("blue", "denim", "indigo", "cobalt", "petrol", "aqua"),
    "navy": ("navy", "marine"),
    "red": ("red", "scarlet", "cherry"),
    "green": ("green", "khaki", "olive", "mint", "sage", "forest", "emerald"),
    "yellow": ("yellow", "mustard", "ochre", "lemon"),
    "orange": ("orange", "coral", "rust", "terracotta", "apricot", "amber"),
    "pink": ("pink", "rose", "fuchsia", "magenta", "blush"),
    "purple": ("purple", "lilac", "lavender", "mauve", "violet", "plum"),
    "brown": ("brown", "chocolate", "mocha", "coffee", "tan", "cognac"),
    "beige": ("beige", "camel", "sand", "stone", "taupe", "nude", "cream", "oat"),
    "burgundy": ("burgundy", "bordeaux", "wine", "maroon", "berry"),
    "teal": ("teal", "turquoise"),
    "gold": ("gold",),
}

_TOKEN_TO_COLOR: dict[str, str] = {
    token: canonical for canonical, tokens in _COLOR_SYNONYMS.items() for token in tokens
}

# Longest tokens first so "off-white" wins over "white".
_COLOR_TOKENS_BY_LEN: tuple[str, ...] = tuple(sorted(_TOKEN_TO_COLOR, key=len, reverse=True))

CANONICAL_COLORS: tuple[str, ...] = tuple(_COLOR_SYNONYMS)

# Gender cues. The scraped data has no gender field, so we lean on:
#  * the two gendered categories (fully reliable),
#  * an explicit "UNISEX" in the name,
#  * Zalando's standalone uppercase "W" women marker (e.g. "NORDKAP SOFTSHELL W"),
#  * women-only garment words and explicit men/women words.
_UNISEX_RE = re.compile(r"\bunisex\b", re.IGNORECASE)
_W_TOKEN_RE = re.compile(r"(?<![A-Za-z])W(?![A-Za-z])")  # uppercase only
_WOMEN_WORD_RE = re.compile(r"\b(women|womens|woman|ladies|female|damen)\b", re.IGNORECASE)
_WOMEN_CUT_RE = re.compile(
    r"\b(dress|dresses|skirt|blouse|gown|jumpsuit|playsuit|smock|peplum|"
    r"crop|cropped|racerback|bodycon|bralette|camisole|cami)\b",
    re.IGNORECASE,
)
_MEN_WORD_RE = re.compile(r"\b(men|mens|man|male|herren|boyfriend)\b", re.IGNORECASE)


def _name_gender_cue(name: str) -> str | None:
    """A gender hint from the product name alone, or ``None`` when it says nothing."""
    text = name or ""
    if _UNISEX_RE.search(text):
        return "unisex"
    if _W_TOKEN_RE.search(text) or _WOMEN_WORD_RE.search(text) or _WOMEN_CUT_RE.search(text):
        return "women"
    if _MEN_WORD_RE.search(text):
        return "men"
    return None


def detect_color(name: str) -> str | None:
    """Return a canonical colour for a product name, or ``None``.

    Zalando names look like ``"LOFOTEN STRETCH - Outdoor trousers - dk navy"``:
    the colour lives in the last ``" - "`` segment. We scan that segment first,
    then fall back to the whole name.
    """
    text = (name or "").lower()
    if not text:
        return None
    tail = text.rsplit(" - ", 1)[-1]
    for scope in (tail, text):
        for token in _COLOR_TOKENS_BY_LEN:
            if re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", scope):
                return _TOKEN_TO_COLOR[token]
    return None


def detect_gender(name: str, category: str) -> str:
    """Best-effort ``men`` / ``women`` / ``unisex`` from the name and category."""
    if category == "Women Dresses":
        return "women"
    if category == "Men T-Shirts & Polos":
        return "men"
    return _name_gender_cue(name) or "unisex"


def product_type(name: str) -> str:
    """The middle ``" - "`` segment, e.g. ``"Outdoor trousers"`` - a free label."""
    parts = [p.strip() for p in (name or "").split(" - ")]
    return parts[1] if len(parts) >= 3 else ""


def embedding_text(product: dict) -> str:
    """Compact natural-language string fed to the embedding model."""
    bits = [
        product.get("name", ""),
        product.get("category", ""),
        product_type(product.get("name", "")),
        product.get("color") or "",
        product.get("gender") or "",
        f"by {product.get('brand', '')}" if product.get("brand") else "",
    ]
    return ". ".join(b for b in bits if b)


# --------------------------------------------------------------------------- #
# Loading the curated slice
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def load_demo_catalog(path: str | Path = DEMO_CATALOG_PATH) -> list[dict]:
    """Load the curated demo products. Raises ``FileNotFoundError`` if unbuilt."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found.\nBuild it first:\n    uv run python scripts/build_demo_catalog.py"
        )
    with path.open(encoding="utf-8") as handle:
        products = json.load(handle)
    for index, product in enumerate(products):
        product["position"] = index + 1
    return products


def products_by_sku(products: list[dict] | None = None) -> dict[str, dict]:
    products = products if products is not None else load_demo_catalog()
    return {p["sku"]: p for p in products}


# --------------------------------------------------------------------------- #
# Embeddings (precomputed; cosine similarity, no vector DB for ~200 rows)
# --------------------------------------------------------------------------- #
def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def build_embeddings(
    products: list[dict] | None = None,
    out_path: str | Path = DEMO_EMBEDDINGS_PATH,
) -> np.ndarray:
    """Embed every demo product once and cache the matrix to ``out_path``."""
    from src.assistant.ollama_client import embed_texts

    products = products if products is not None else load_demo_catalog()
    vectors = embed_texts([embedding_text(p) for p in products])
    matrix = _l2_normalize(np.asarray(vectors, dtype=np.float32))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    np.save(out_path, matrix)
    return matrix


@lru_cache(maxsize=1)
def load_embeddings(path: str | Path = DEMO_EMBEDDINGS_PATH) -> np.ndarray:
    """Return the cached embedding matrix, building it on first use if missing."""
    path = Path(path)
    products = load_demo_catalog()
    if path.exists():
        matrix = np.load(path)
        if matrix.shape[0] == len(products):
            return matrix
    return build_embeddings(products, path)


# --------------------------------------------------------------------------- #
# Search: deterministic hard filters, then optional semantic ranking
# --------------------------------------------------------------------------- #
# LLM category slug -> substrings that may appear in the real ``category`` /
# product name. A slug matches if any substring is found in either.
_CATEGORY_MATCHERS: dict[str, tuple[str, ...]] = {
    "shirt": ("shirt",),
    "t-shirt": ("t-shirt", "t-shirts", "polo", "tee"),
    "jacket": ("jacket",),
    "coat": ("coat", "parka"),
    "dress": ("dress",),
    "jeans": ("jeans", "denim"),
    "trousers": ("jeans", "trouser", "pant", "chino", "legging", "short"),
    "sportswear": ("sportswear", "outdoor", "ski", "running", "training", "track"),
    "streetwear": ("streetwear", "hoodie", "sweat"),
}


def _matches_category(product: dict, slug: str | None) -> bool:
    if not slug:
        return True
    needles = _CATEGORY_MATCHERS.get(slug.lower().strip())
    if not needles:
        needles = (slug.lower().strip(),)
    haystack = f"{product.get('category', '')} {product.get('name', '')}".lower()
    return any(needle in haystack for needle in needles)


def _matches_keywords(product: dict, keywords: list[str] | None) -> bool:
    if not keywords:
        return True
    haystack = f"{product.get('name', '')} {product.get('category', '')}".lower()
    return all(str(kw).lower().strip() in haystack for kw in keywords if str(kw).strip())


def _matches_gender(product: dict, gender: str | None) -> bool:
    """Strict-ish gender match.

    The data barely tags gender, so a requested gender:
      * keeps items explicitly tagged that gender,
      * keeps genuinely unisex items *unless* their name carries an
        opposite-gender cue (a "crop top" is not men's wear),
      * drops items explicitly tagged the opposite gender.
    """
    if not gender or gender == "unisex":
        return True
    tagged = product.get("gender", "unisex")
    if tagged == gender:
        return True
    if tagged != "unisex":  # explicitly the other gender
        return False
    cue = _name_gender_cue(product.get("name", ""))
    return cue in (None, "unisex", gender)


def apply_filters(
    products: list[dict],
    *,
    category: str | None = None,
    color: str | None = None,
    gender: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    keywords: list[str] | None = None,
) -> list[dict]:
    """Deterministic hard filtering - no model involved."""
    color = (color or "").lower().strip() or None
    gender = (gender or "").lower().strip() or None
    out = []
    for product in products:
        if not _matches_category(product, category):
            continue
        if color and product.get("color") != color and color not in product.get("name", "").lower():
            continue
        if not _matches_gender(product, gender):
            continue
        price = float(product.get("promotional_price") or 0.0)
        if min_price is not None and price < float(min_price):
            continue
        if max_price is not None and price > float(max_price):
            continue
        if not _matches_keywords(product, keywords):
            continue
        out.append(product)
    return out


def search(
    *,
    category: str | None = None,
    color: str | None = None,
    gender: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    keywords: list[str] | None = None,
    semantic_query: str | None = None,
    top_k: int = 6,
) -> list[dict]:
    """Filter, then rank. Returns up to ``top_k`` demo products with positions."""
    products = load_demo_catalog()
    matched = apply_filters(
        products,
        category=category,
        color=color,
        gender=gender,
        min_price=min_price,
        max_price=max_price,
        keywords=keywords,
    )
    if not matched:
        return []

    # If a gender was asked for and at least a couple of matches are explicitly
    # that gender, drop the merely-plausible unisex ones so the result reads as
    # truly gendered. Fall back to the wider set only when the data is too thin.
    wanted = (gender or "").lower().strip()
    if wanted in ("men", "women"):
        tagged = [p for p in matched if p.get("gender") == wanted]
        if len(tagged) >= 2:
            matched = tagged

    query = (semantic_query or "").strip()
    if query and len(query) >= 3:
        from src.assistant.ollama_client import embed_texts

        matrix = load_embeddings()
        indices = [p["position"] - 1 for p in matched]
        query_vec = _l2_normalize(np.asarray(embed_texts([query]), dtype=np.float32))
        scores = matrix[indices] @ query_vec[0]
        order = np.argsort(-scores)
        ranked = [matched[i] for i in order]
    else:
        ranked = sorted(matched, key=lambda p: float(p.get("promotional_price") or 0.0))

    results = [dict(p) for p in ranked[:top_k]]
    for display_position, product in enumerate(results, start=1):
        product["position"] = display_position
    return results
