"""Curate a tiny demo catalog for the voice assistant from the full dataset.

The full ``data/products/products.json`` has ~192k rows and no colour/gender
fields. This script picks a small, deterministic, category-balanced slice with a
colour and coarse gender derived from each product name, and writes it to
``data/products/catalog_demo.json``. It then precomputes MiniLM embeddings via
Ollama so the app never has to embed on startup.

    uv run python scripts/build_demo_catalog.py
    uv run python scripts/build_demo_catalog.py --size 160 --max-price 250

Re-running is idempotent: same input -> byte-identical output.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEMO_CATALOG_PATH  # noqa: E402
from src.demo_catalog import detect_color, detect_gender, product_type  # noqa: E402

FULL_CATALOG = PROJECT_ROOT / "data" / "products" / "products.json"

# Keep these keys from each raw record; add color / color_raw / gender / type.
_KEEP = (
    "sku",
    "name",
    "brand",
    "category",
    "sizes",
    "original_price",
    "discount_percentage",
    "promotional_price",
    "currency",
    "image_path",
    "source_url",
)

# Colours we want to be sure are represented (so the "add the yellow one" and
# ambiguity demos always have something to hit).
_MUST_HAVE_COLORS = ("black", "white", "blue", "navy", "grey", "yellow", "red", "green")
_MIN_PER_MUST_HAVE = 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--size", type=int, default=128, help="target number of products (default 128)")
    p.add_argument("--min-price", type=float, default=5.0)
    p.add_argument("--max-price", type=float, default=300.0)
    p.add_argument("--no-embed", action="store_true", help="skip precomputing embeddings")
    return p.parse_args(argv)


def _candidate(raw: dict, min_price: float, max_price: float) -> dict | None:
    price = raw.get("promotional_price") or raw.get("original_price") or 0.0
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if not (min_price <= price <= max_price):
        return None

    image_rel = raw.get("image_path") or ""
    if not image_rel or not (PROJECT_ROOT / image_rel).is_file():
        return None

    name = raw.get("name") or ""
    color = detect_color(name)
    if color is None:
        return None

    record = {key: raw.get(key) for key in _KEEP}
    record["color"] = color
    record["color_raw"] = name.rsplit(" - ", 1)[-1].strip() if " - " in name else color
    record["gender"] = detect_gender(name, raw.get("category") or "")
    record["type"] = product_type(name)
    return record


def _pick_balanced(by_category: dict[str, list[dict]], target: int) -> list[dict]:
    """Round-robin across categories, preferring unseen colours within each."""
    categories = sorted(by_category)
    per_category = max(1, target // max(1, len(categories)))
    chosen: list[dict] = []

    for category in categories:
        pool = sorted(by_category[category], key=lambda r: r["sku"])
        seen_colors: set[str] = set()
        picked: list[dict] = []
        # first pass: maximise colour variety
        for record in pool:
            if len(picked) >= per_category:
                break
            if record["color"] not in seen_colors:
                seen_colors.add(record["color"])
                picked.append(record)
        # second pass: top up to the quota in sku order
        for record in pool:
            if len(picked) >= per_category:
                break
            if record not in picked:
                picked.append(record)
        chosen.extend(picked)

    # ensure the demo-critical colours clear a floor, pulling extras in sku order
    chosen_skus = {r["sku"] for r in chosen}
    all_records = sorted(
        (r for records in by_category.values() for r in records), key=lambda r: r["sku"]
    )
    for color in _MUST_HAVE_COLORS:
        have = sum(1 for r in chosen if r["color"] == color)
        if have >= _MIN_PER_MUST_HAVE:
            continue
        for record in all_records:
            if have >= _MIN_PER_MUST_HAVE:
                break
            if record["color"] == color and record["sku"] not in chosen_skus:
                chosen.append(record)
                chosen_skus.add(record["sku"])
                have += 1

    chosen.sort(key=lambda r: (r["category"], r["sku"]))
    return chosen


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not FULL_CATALOG.exists():
        print(f"{FULL_CATALOG} not found - run scripts/download_dataset.py first.")
        return 1

    with FULL_CATALOG.open(encoding="utf-8") as handle:
        raw_records = json.load(handle)
    print(f"Loaded {len(raw_records):,} products from the full catalog.")

    by_category: dict[str, list[dict]] = defaultdict(list)
    for raw in raw_records:
        record = _candidate(raw, args.min_price, args.max_price)
        if record is not None:
            by_category[record["category"]].append(record)

    usable = sum(len(v) for v in by_category.values())
    print(f"{usable:,} products have a local image, an in-range price and a detectable colour.")
    for category in sorted(by_category):
        print(f"  {category:<24} {len(by_category[category]):>6}")

    selection = _pick_balanced(by_category, args.size)

    DEMO_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEMO_CATALOG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(selection, handle, ensure_ascii=False, indent=2)

    colors = defaultdict(int)
    genders = defaultdict(int)
    cats = defaultdict(int)
    for record in selection:
        colors[record["color"]] += 1
        genders[record["gender"]] += 1
        cats[record["category"]] += 1

    print(f"\nWrote {len(selection)} products -> {DEMO_CATALOG_PATH.relative_to(PROJECT_ROOT)}")
    print("  by category:", dict(sorted(cats.items())))
    print("  by colour  :", dict(sorted(colors.items(), key=lambda kv: -kv[1])))
    print("  by gender  :", dict(genders))

    if not args.no_embed:
        try:
            from src.demo_catalog import build_embeddings, load_demo_catalog

            load_demo_catalog.cache_clear()
            matrix = build_embeddings()
            print(
                f"\nPrecomputed embeddings: {matrix.shape} -> "
                f"{Path('data/products/catalog_demo_embeddings.npy')}"
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"\nSkipped embeddings ({exc}). The app will build them on first run "
                f"once `ollama pull all-minilm` is done."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
