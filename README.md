# StyleSpeak

Local product-dataset pipeline and Streamlit e-commerce catalog built on the
Hugging Face dataset [`thivav/zalando_fashionista_x100`](https://huggingface.co/datasets/thivav/zalando_fashionista_x100)
(~192k Zalando fashion products).

The pipeline downloads the **complete** dataset once, saves every product image
locally, and stores cleaned metadata as JSON. The Streamlit app then runs fully
offline from those local files - it never calls Hugging Face at runtime and never
depends on the original Zalando product URLs (kept only as `source_url`).

## Project layout

```
StyleSpeak/
├── app.py                     # entrypoint: page config, logo, st.navigation
├── views/
│   ├── catalog.py             # catalog page (filter form + product grid)
│   └── cart.py                # cart page (full-size review with images)
├── assets/
│   ├── logo.png               # monogram, used as favicon + st.logo icon
│   └── logo_wide.png          # sidebar wordmark
├── .env                       # HF_TOKEN (git-ignored, create from .env.example)
├── .env.example
├── scripts/
│   ├── download_dataset.py    # dataset -> local images + products.json
│   └── make_logo.py           # regenerates assets/logo*.png
├── src/
│   ├── config.py              # loads HF_TOKEN, fails loudly if missing
│   ├── metadata.py            # raw-row cleaning (prices, sizes, discounts, ...)
│   ├── catalog.py             # Polars: load / filter / sort / paginate
│   ├── cart.py                # framework-free shopping-cart logic
│   └── ui.py                  # shared Streamlit helpers (formatting, state)
├── tests/                     # pytest unit tests for the pure logic
└── data/                      # generated, git-ignored
    └── products/
        ├── products.json
        └── images/<sku>.jpg
```

The catalog data layer (`src/catalog.py`) uses **Polars**.

## Setup (WSL / Linux, uv)

```bash
# 1. Install dependencies into a local virtual environment
uv sync

# 2. Configure Hugging Face auth
cp .env.example .env
# edit .env and set your token:  HF_TOKEN=hf_xxx
# create one at https://huggingface.co/settings/tokens
```

`HF_TOKEN` is read only from the environment (via `.env` for local dev). It is
never hardcoded and `.env` is git-ignored.

## Build the catalog

```bash
uv run python scripts/download_dataset.py
```

* Reuses the Hugging Face dataset cache - re-runs do not re-download it.
* Skips images that already exist and open cleanly (use `--force` to rewrite).
* Missing/corrupt images are counted and reported, never fatal.
* Prints progress and a final summary (products, images written, failures).
* `--limit N` / `--start N` process a slice; Ctrl-C flushes progress so far.

Output: `data/products/images/<sku>.jpg` and `data/products/products.json` with
fields `sku, name, brand, category, categories, sizes, classification,
original_price, discount_percentage, promotional_price, currency, image_path,
source_url`.

## Run the app

```bash
streamlit run app.py
```

Two pages sharing one cart in `st.session_state`:

* **Catalog** - product grid showing only image, name, price and any offer.
  Sidebar carries a cart pointer above the filters, then a filter form
  (name search, category, brand, size, promotional-price range, "only
  discounted") that applies only when you press **Apply** (Reset clears it).
  Sort and page size are outside the form and update immediately. Pagination
  keeps thousands of products from rendering at once.
* **Cart** - full-size review of selected products with their local images,
  per-line quantity steppers, line totals and the subtotal.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
