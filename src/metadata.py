"""Pure helpers for cleaning raw ``thivav/zalando_fashionista_x100`` rows.

The raw dataset stores everything as strings, often stringified Python
literals, with European price formatting (``'89,99\\xa0€'``) and frequently
missing discount / promotional price fields. These helpers normalise a raw row
into the flat metadata record persisted in ``data/products/products.json``.
"""

from __future__ import annotations

import ast
import re
from typing import Any

_PRICE_RE = re.compile(r"[0-9][0-9.,]*")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_SKU_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_SKU_LEN = 120


def parse_price(raw: Any) -> float | None:
    """Parse a European-formatted price string into euros as a float.

    ``'89,99\\xa0€'`` -> ``89.99``. Returns ``None`` for empty / unparseable
    values. Handles both ``1.234,56`` (dot thousands, comma decimal) and the
    common ``89,99`` form.
    """
    if raw is None:
        return None
    text = str(raw).replace("\xa0", " ").strip()
    if not text or text.lower() == "none":
        return None
    match = _PRICE_RE.search(text)
    if not match:
        return None
    token = match.group(0)
    if "," in token and "." in token:
        token = token.replace(".", "").replace(",", ".")
    elif "," in token:
        token = token.replace(",", ".")
    try:
        return round(float(token), 2)
    except ValueError:
        return None


def parse_discount(raw: Any) -> int | None:
    """Parse ``'-50%'`` / ``'up to -20%'`` into an integer percentage (``50`` / ``20``).

    Returns ``None`` when no discount is recorded.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() == "none":
        return None
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    try:
        value = float(match.group(0).replace(",", "."))
    except ValueError:
        return None
    return max(0, int(round(value)))


def reconcile_pricing(
    original: float | None,
    discount: int | None,
    promotional: float | None,
) -> tuple[float | None, int, float | None]:
    """Return a consistent ``(original, discount_percentage, promotional)`` triple.

    Rules:
      * both missing        -> discount 0, promotional = original
      * discount only       -> promotional = original * (1 - d/100)
      * promotional only    -> discount = round((1 - promo/original) * 100)
      * both present        -> kept as-is (discount clamped to >= 0)
    """
    if original is None and promotional is not None:
        original = promotional

    if discount is None and promotional is None:
        return original, 0, original

    if promotional is None and discount is not None:
        promo = round(original * (1 - discount / 100), 2) if original is not None else None
        return original, discount, promo

    if discount is None and promotional is not None:
        if original and original > 0:
            discount = max(0, int(round((1 - promotional / original) * 100)))
        else:
            discount = 0
        return original, discount, promotional

    return original, max(0, int(discount)), promotional


def parse_literal_list(raw: Any) -> list[Any]:
    """Safely parse a stringified Python list (``"['NEW']"``) into a list."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    text = str(raw).strip()
    if not text or text in {"[]", "None", "none"}:
        return []
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return [text]
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def parse_string_list(raw: Any) -> list[str]:
    """Parse a stringified list into a list of non-empty stripped strings."""
    out: list[str] = []
    for item in parse_literal_list(raw):
        if item is None:
            continue
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def parse_sizes(raw: Any) -> list[str]:
    """Extract ordered, de-duplicated size labels from the raw ``sizes`` field.

    Raw form: ``"[{'size': '36', 'sku': '...'}, {'size': '38', ...}]"``.
    """
    seen: set[str] = set()
    out: list[str] = []
    for item in parse_literal_list(raw):
        value = item.get("size") if isinstance(item, dict) else item
        if value is None:
            continue
        label = str(value).strip()
        if label and label not in seen:
            seen.add(label)
            out.append(label)
    return out


def sanitize_sku(sku: Any, fallback_index: int | None = None) -> str:
    """Turn a SKU into a filesystem-safe stem.

    Keeps ``[A-Za-z0-9._-]``, collapses everything else to ``-``, strips leading
    dots/dashes (no path traversal), caps length, and falls back to
    ``row-<index>`` when the result would be empty.
    """
    text = "" if sku is None else str(sku).strip()
    text = _SKU_UNSAFE_RE.sub("-", text)
    text = text.strip("-.").replace("..", "-")[:_MAX_SKU_LEN].strip("-.")
    if not text:
        text = f"row-{fallback_index}" if fallback_index is not None else "row-unknown"
    return text


# Column order matches the metadata schema in the task brief; extra derived
# fields (`categories`, `currency`) follow.
METADATA_FIELDS = (
    "sku",
    "name",
    "brand",
    "category",
    "sizes",
    "classification",
    "original_price",
    "discount_percentage",
    "promotional_price",
    "image_path",
    "source_url",
)


def clean_row(row: dict[str, Any], index: int, image_path: str) -> dict[str, Any]:
    """Build the flat, cleaned product record for one raw dataset row."""
    raw_sku = row.get("sku")
    sku = str(raw_sku).strip() if raw_sku not in (None, "") else sanitize_sku(raw_sku, index)

    original = parse_price(row.get("original_price"))
    discount = parse_discount(row.get("discount_percentage"))
    promotional = parse_price(row.get("promotional_price"))
    original, discount, promotional = reconcile_pricing(original, discount, promotional)

    categories = parse_string_list(row.get("category"))

    return {
        "sku": sku,
        "name": (row.get("name") or "").strip(),
        "brand": (row.get("brand") or "").strip(),
        "category": categories[0] if categories else "Uncategorized",
        "categories": categories,
        "sizes": parse_sizes(row.get("sizes")),
        "classification": parse_string_list(row.get("classification")),
        "original_price": original,
        "discount_percentage": discount,
        "promotional_price": promotional,
        "currency": "EUR",
        "image_path": image_path,
        "source_url": row.get("url") or "",
    }
