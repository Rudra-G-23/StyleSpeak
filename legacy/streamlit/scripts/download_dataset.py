"""Download the complete ``thivav/zalando_fashionista_x100`` dataset and build
the local product catalog under ``data/products/``.

What it does
------------
* Authenticates to Hugging Face with ``HF_TOKEN`` from the environment.
* Loads the dataset via the ``datasets`` library, reusing the local HF cache
  (nothing is re-downloaded unless the cache is cold).
* Saves every product image locally as ``data/products/images/<sku>.jpg`` so the
  app never depends on temporary Hugging Face image URLs.
* Writes cleaned metadata to ``data/products/products.json``.

Resuming
--------
Re-running is cheap: images that already exist and open cleanly are skipped, and
existing ``products.json`` entries are merged with the new run. Use ``--force``
to re-save every image, ``--limit`` / ``--start`` to process a slice, and press
Ctrl-C to stop early - progress so far is still flushed to ``products.json``.

Usage
-----
    uv run python scripts/download_dataset.py
    uv run python scripts/download_dataset.py --limit 500        # quick sample
    uv run python scripts/download_dataset.py --start 100000     # resume slice
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

from datasets import Image as HfImage
from datasets import load_dataset
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_hf_token  # noqa: E402
from src.metadata import clean_row, sanitize_sku  # noqa: E402

DATASET_ID = "thivav/zalando_fashionista_x100"
SPLIT = "train"

DATA_DIR = PROJECT_ROOT / "data" / "products"
IMAGES_DIR = DATA_DIR / "images"
PRODUCTS_JSON = DATA_DIR / "products.json"

PROGRESS_EVERY = 500


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--limit", type=int, default=None, help="process at most N rows")
    parser.add_argument("--start", type=int, default=0, help="skip the first N rows")
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-save images even when a valid file already exists",
    )
    return parser.parse_args(argv)


def load_existing_metadata() -> dict[str, dict]:
    """Load a previous run's products.json keyed by SKU (for resuming)."""
    if not PRODUCTS_JSON.exists():
        return {}
    try:
        with PRODUCTS_JSON.open(encoding="utf-8") as handle:
            records = json.load(handle)
    except (json.JSONDecodeError, OSError):
        print("  existing products.json unreadable - starting fresh")
        return {}
    return {rec["sku"]: rec for rec in records if isinstance(rec, dict) and rec.get("sku")}


def write_metadata(by_sku: dict[str, dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = PRODUCTS_JSON.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(list(by_sku.values()), handle, ensure_ascii=False, indent=2)
    tmp.replace(PRODUCTS_JSON)


def image_is_valid(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except (OSError, SyntaxError, ValueError):
        return False


def save_image(raw_image: object, dest: Path, force: bool) -> str:
    """Persist one image. Returns 'written' or 'skipped'; raises on failure."""
    if dest.exists() and not force:
        if image_is_valid(dest):
            return "skipped"
        dest.unlink(missing_ok=True)

    data: bytes | None = None
    if isinstance(raw_image, dict):
        data = raw_image.get("bytes")
        if data is None and raw_image.get("path"):
            data = Path(raw_image["path"]).read_bytes()
    elif isinstance(raw_image, (bytes, bytearray)):
        data = bytes(raw_image)

    if not data:
        raise ValueError("row has no image bytes")

    with Image.open(io.BytesIO(data)) as img:
        img.convert("RGB").save(dest, format="JPEG", quality=90)
    return "written"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    token = get_hf_token()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading dataset {DATASET_ID} (reusing HF cache when available)...")
    dataset = load_dataset(DATASET_ID, split=SPLIT, token=token)
    # Keep image bytes undecoded so a corrupt image cannot crash iteration.
    dataset = dataset.cast_column("image", HfImage(decode=False))

    total_rows = dataset.num_rows
    start = max(0, args.start)
    stop = total_rows if args.limit is None else min(total_rows, start + args.limit)
    planned = max(0, stop - start)
    print(f"Dataset has {total_rows} rows; processing rows [{start}, {stop}) = {planned}\n")

    by_sku = load_existing_metadata()
    if by_sku:
        print(f"Merging with {len(by_sku)} products from a previous run\n")

    written = skipped = failed = 0
    failed_examples: list[str] = []
    began = time.time()

    try:
        for index in range(start, stop):
            row = dataset[index]
            raw_sku = row.get("sku")
            stem = sanitize_sku(raw_sku, index)
            dest = IMAGES_DIR / f"{stem}.jpg"

            try:
                outcome = save_image(row.get("image"), dest, args.force)
            except (OSError, ValueError, SyntaxError) as exc:
                failed += 1
                if len(failed_examples) < 10:
                    failed_examples.append(f"{raw_sku or f'row-{index}'} ({exc})")
                continue

            if outcome == "written":
                written += 1
            else:
                skipped += 1

            record = clean_row(row, index, str(dest.relative_to(PROJECT_ROOT)))
            by_sku[record["sku"]] = record

            done = index - start + 1
            if done % PROGRESS_EVERY == 0 or done == planned:
                rate = done / max(1e-6, time.time() - began)
                print(
                    f"  {done}/{planned} rows | written={written} "
                    f"cached={skipped} failed={failed} | {rate:.0f} rows/s",
                    flush=True,
                )
    except KeyboardInterrupt:
        print("\nInterrupted - flushing progress so far...")
    finally:
        write_metadata(by_sku)

    elapsed = time.time() - began
    print("\n" + "=" * 60)
    print("Download complete" if planned else "Nothing to do")
    print(f"  products in catalog : {len(by_sku)}")
    print(f"  images written      : {written}")
    print(f"  images reused/cached : {skipped}")
    print(f"  failed images       : {failed}")
    if failed_examples:
        print("  failure examples    :")
        for item in failed_examples:
            print(f"    - {item}")
    print(f"  elapsed             : {elapsed:.1f}s")
    print(f"  metadata            : {PRODUCTS_JSON.relative_to(PROJECT_ROOT)}")
    print(f"  images              : {IMAGES_DIR.relative_to(PROJECT_ROOT)}/")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
