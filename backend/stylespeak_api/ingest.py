"""Batch ingest a real, normalized pants catalog without retaining all rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from .database import make_engine
from .models import Base
from .normalizers import normalize_product
from .repository import create_schema, rebuild_fts, upsert_products


def iter_json_array(path: Path, chunk_size: int = 1024 * 1024):
    decoder = json.JSONDecoder()
    with path.open(encoding="utf-8") as handle:
        buffer = ""
        started = False
        while True:
            chunk = handle.read(chunk_size)
            if not chunk and not buffer:
                break
            buffer += chunk
            position = 0
            while True:
                while position < len(buffer) and buffer[position] in " \n\r\t,[]":
                    if buffer[position] == "[":
                        started = True
                    position += 1
                if position >= len(buffer):
                    break
                try:
                    row, end = decoder.raw_decode(buffer, position)
                except json.JSONDecodeError:
                    break
                if started:
                    yield row
                position = end
            buffer = buffer[position:]
            if not chunk:
                break


def row_to_product(row: dict) -> dict | None:
    name = str(row.get("name") or "").strip()
    source_url = str(row.get("source_url") or "")
    original = row.get("original_price")
    price = row.get("promotional_price") or original
    image_path = str(row.get("image_path") or "")
    if (
        not name
        or not row.get("sku")
        or not isinstance(price, (float, int))
        or price <= 0
        or not Path(image_path).is_file()
    ):
        return None
    normalized = normalize_product(
        name, source_url, str(row.get("category") or ""), str(row.get("brand") or "")
    )
    if normalized is None or normalized.gender == "women":
        return None
    sizes = [str(size) for size in row.get("sizes") or [] if str(size).strip()]
    return {
        "sku": str(row["sku"]),
        "family_key": normalized.family_key,
        "name": name,
        "brand": str(row.get("brand") or "Unknown brand"),
        "category": normalized.category,
        "subcategory": normalized.subcategory,
        "gender": normalized.gender,
        "color": normalized.color,
        "sizes_json": json.dumps(sizes),
        "price": round(float(price), 2),
        "original_price": round(float(original), 2) if isinstance(original, (float, int)) else None,
        "currency": str(row.get("currency") or "EUR"),
        "image_path": image_path,
        "source_url": source_url,
        "searchable_text": " ".join(
            [
                name,
                str(row.get("brand") or ""),
                normalized.category,
                normalized.subcategory or "",
                normalized.color or "",
                normalized.gender,
            ]
        ),
    }


def ingest(
    source: Path, database_url: str, limit: int | None = None, batch_size: int = 500
) -> tuple[int, int]:
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    accepted = rejected = 0
    batch: list[dict] = []
    with Session(engine) as session:
        create_schema(session)
        for row in iter_json_array(source):
            product = row_to_product(row)
            if product is None:
                rejected += 1
                continue
            batch.append(product)
            accepted += 1
            if len(batch) >= batch_size:
                upsert_products(session, batch, refresh_index=False)
                batch.clear()
            if limit is not None and accepted >= limit:
                break
        if batch:
            upsert_products(session, batch, refresh_index=False)
        rebuild_fts(session)
        session.commit()
    return accepted, rejected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/products/products.json"))
    parser.add_argument("--database-url", default="sqlite:///data/stylespeak-v2.db")
    parser.add_argument("--limit", type=int, default=2500)
    args = parser.parse_args()
    accepted, rejected = ingest(args.source, args.database_url, args.limit)
    print(f"ingested={accepted} rejected={rejected}")


if __name__ == "__main__":
    main()
