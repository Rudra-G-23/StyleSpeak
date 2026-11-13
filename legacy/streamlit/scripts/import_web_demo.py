"""Create the real-image web demo catalog from the public dataset service.

The web app uses only the generated local files. Run this script again to
refresh the curated slice:

    uv run python scripts/import_web_demo.py
"""

from __future__ import annotations

import ast
import json
import math
import re
from collections import Counter, defaultdict, deque
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB = PROJECT_ROOT / "web"
CATALOG = WEB / "products.json"
SEARCH_INDEX = WEB / "search-index.json"
IMAGES = WEB / "images"
DATASET = "thivav/zalando_fashionista_x100"
SAMPLE_OFFSETS = (0, 96_000)
ROWS_PER_OFFSET = 50
TARGET_SIZE = 100
TOKEN = re.compile(r"[a-z0-9]+")

COLORS = {
    "black": ("black", "charcoal", "anthracite"),
    "white": ("white", "ivory", "cream"),
    "grey": ("grey", "gray", "silver"),
    "blue": ("blue", "denim", "indigo"),
    "navy": ("navy", "marine"),
    "green": ("green", "green", "olive", "khaki"),
    "brown": ("brown", "camel", "cognac"),
    "beige": ("beige", "sand", "taupe"),
    "burgundy": ("burgundy", "bordeaux", "wine"),
    "pink": ("pink", "rose"),
    "red": ("red", "scarlet"),
}


def fetch_rows(offset: int) -> list[dict]:
    query = urlencode(
        {
            "dataset": DATASET,
            "config": "default",
            "split": "train",
            "offset": offset,
            "length": ROWS_PER_OFFSET,
        }
    )
    with urlopen(f"https://datasets-server.huggingface.co/rows?{query}", timeout=60) as response:
        payload = json.load(response)
    return [item["row"] for item in payload["rows"]]


def parsed(value: object, fallback: list[str]) -> list[str]:
    try:
        result = ast.literal_eval(str(value))
    except (SyntaxError, ValueError):
        return fallback
    return result if isinstance(result, list) else fallback


def amount(value: object) -> float:
    match = re.search(r"[\d,.]+", str(value or ""))
    return float(match.group(0).replace(",", ".")) if match else 0.0


def discount_amount(value: object) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def color_for(name: str) -> str:
    lowered = name.lower()
    for color, terms in COLORS.items():
        if any(term in lowered for term in terms):
            return color
    return "unknown"


def gender_for(name: str) -> str:
    lowered = name.lower()
    if re.search(r"(^|\s)w($|\s)|women|ladies|female", lowered):
        return "women"
    return "men"


def tokens_for(product: dict) -> list[str]:
    text = " ".join(
        [
            product["name"],
            product["brand"],
            product["category"],
            product["type"],
            product["color"],
            product["gender"],
        ]
    ).lower()
    return TOKEN.findall(text)


def build_search_index(products: list[dict]) -> dict:
    counts = {product["sku"]: Counter(tokens_for(product)) for product in products}
    document_frequency = Counter(term for terms in counts.values() for term in terms)
    total = len(products)
    idf = {
        term: math.log((total + 1) / (frequency + 1)) + 1
        for term, frequency in document_frequency.items()
    }
    documents = []
    for product in products:
        terms = counts[product["sku"]]
        length = sum(terms.values())
        vector = {term: round((count / length) * idf[term], 8) for term, count in terms.items()}
        norm = math.sqrt(sum(weight * weight for weight in vector.values()))
        documents.append(
            {
                "sku": product["sku"],
                "terms": terms,
                "vector": vector,
                "norm": round(norm, 8),
                "length": length,
            }
        )
    return {
        "version": 1,
        "method": "tf-idf-cosine-plus-bm25",
        "average_document_length": sum(doc["length"] for doc in documents) / total,
        "idf": idf,
        "documents": documents,
    }


def record(row: dict) -> dict | None:
    categories = parsed(row.get("category"), ["Sportswear"])
    sizes = [
        item["size"]
        for item in parsed(row.get("sizes"), [])
        if isinstance(item, dict) and isinstance(item.get("size"), str)
    ]
    image = row.get("image")
    if not isinstance(image, dict) or not image.get("src") or not row.get("sku"):
        return None
    original = amount(row.get("original_price"))
    promotional = amount(row.get("promotional_price")) or original
    discount = row.get("discount_percentage")
    name = row.get("name") or "Product"
    product_type = name.split(" - ")[1] if " - " in name else "Product"
    return {
        "sku": row["sku"],
        "name": name,
        "brand": row.get("brand") or "Unknown brand",
        "category": categories[0] if categories else "Sportswear",
        "type": product_type,
        "color": color_for(name),
        "gender": gender_for(name),
        "sizes": sizes or ["One size"],
        "original_price": original,
        "discount_percentage": discount_amount(discount),
        "promotional_price": promotional,
        "currency": "EUR",
        "image_path": f"images/{row['sku']}.jpg",
        "_image_url": image["src"],
    }


def choose_candidates(rows: list[dict]) -> list[dict]:
    grouped: dict[str, deque[dict]] = defaultdict(deque)
    for row in rows:
        item = record(row)
        if item:
            grouped[item["category"]].append(item)
    selected: list[dict] = []
    while len(selected) < TARGET_SIZE and any(grouped.values()):
        for category in sorted(grouped):
            if grouped[category] and len(selected) < TARGET_SIZE:
                selected.append(grouped[category].popleft())
    return selected


def main() -> None:
    rows = [row for offset in SAMPLE_OFFSETS for row in fetch_rows(offset)]
    products = choose_candidates(rows)
    if len(products) < TARGET_SIZE:
        raise RuntimeError(f"Only found {len(products)} usable products")
    IMAGES.mkdir(exist_ok=True)
    for index, product in enumerate(products, start=1):
        destination = IMAGES / f"{product['sku']}.jpg"
        image_url = product.pop("_image_url")
        if not destination.exists():
            with urlopen(image_url, timeout=60) as source:
                destination.write_bytes(source.read())
        print(f"{index}/{len(products)} {destination.name}")
    CATALOG.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SEARCH_INDEX.write_text(
        json.dumps(build_search_index(products), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(products)} products to {CATALOG.relative_to(PROJECT_ROOT)}")
    print(f"Wrote search index to {SEARCH_INDEX.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
