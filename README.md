# StyleSpeak

![img](/assets/logo_wide.png)

Local, **voice-powered** fashion shopping assistant with a Streamlit UI, built on
the Hugging Face dataset [`thivav/zalando_fashionista_x100`](https://huggingface.co/datasets/thivav/zalando_fashionista_x100)
(~192k Zalando fashion products).

Everything runs on your machine and is free: a small [Ollama](https://ollama.com)
model parses shopping requests, `faster-whisper` does speech-to-text, and
`all-MiniLM` embeddings power semantic search. No OpenAI / Anthropic / Gemini /
ElevenLabs / Pinecone or any other paid or cloud API.

The dataset pipeline downloads the **complete** dataset once, saves every product
image locally, and stores cleaned metadata as JSON. The app then runs fully
offline from those local files plus the local Ollama server - it never calls
Hugging Face at runtime (except a one-time `faster-whisper` model download) and
never depends on the original Zalando product URLs (kept only as `source_url`).

## Project layout

```
StyleSpeak/
├── app.py                       # entrypoint: page config, logo, st.navigation
├── views/
│   ├── assistant.py             # voice + text shopping assistant (default page)
│   ├── catalog.py               # manual catalog page (filter form + product grid)
│   └── cart.py                  # cart page (full-size review with images)
├── assets/                      # logo.png (favicon/icon), logo_wide.png (wordmark)
├── .env                         # HF_TOKEN (git-ignored, create from .env.example)
├── .env.example
├── scripts/
│   ├── download_dataset.py      # full dataset -> local images + products.json
│   ├── build_demo_catalog.py    # full catalog -> curated data/products/catalog_demo.json
│   └── make_logo.py             # regenerates assets/logo*.png
├── src/
│   ├── config.py                # HF_TOKEN + all assistant config (Ollama, Whisper, paths)
│   ├── metadata.py              # raw-row cleaning (prices, sizes, discounts, ...)
│   ├── catalog.py               # Polars: load / filter / sort / paginate (full catalog)
│   ├── demo_catalog.py          # curated slice: colour/gender extraction, embeddings, search
│   ├── cart.py                  # framework-free shopping-cart logic
│   ├── ui.py                    # shared Streamlit helpers (formatting, state)
│   └── assistant/
│       ├── ollama_client.py     # local Ollama HTTP (chat JSON + embeddings)
│       ├── schemas.py           # Pydantic intent schema (validates LLM output)
│       ├── intent.py            # prompt + parse + validate -> Intent
│       ├── resolve.py           # "the second one" / "the yellow one" -> a product
│       ├── voice.py             # faster-whisper speech-to-text
│       └── handler.py           # handle_user_message() - the one path text + voice share
├── tests/                       # pytest unit tests for the pure logic
└── data/                        # generated, git-ignored
    └── products/
        ├── products.json               # full ~192k catalog
        ├── catalog_demo.json           # curated ~200-product assistant catalog
        ├── catalog_demo_embeddings.npy # precomputed MiniLM vectors
        └── images/<sku>.jpg
```

The full-catalog data layer (`src/catalog.py`) uses **Polars**; the assistant
works over the small `catalog_demo.json` slice with plain Python + NumPy.

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

## Voice assistant setup

The assistant needs a local **Ollama** server and two small models.

```bash
# 1. Install Ollama (once). https://ollama.com/download
curl -fsSL https://ollama.com/install.sh | sh
ollama serve            # or: systemctl start ollama   (already a service on most installs)

# 2. Pull the models (once): ~1 GB LLM + 46 MB embeddings
ollama pull qwen2.5:1.5b-instruct-q4_K_M
ollama pull all-minilm

# 3. Build the curated demo catalog + precompute embeddings (once)
uv run python scripts/build_demo_catalog.py
```

**Models and why**

| Role | Model | Size | Notes |
| --- | --- | --- | --- |
| Intent parsing | `qwen2.5:1.5b-instruct-q4_K_M` (Ollama) | ~1 GB disk / ~2 GB RAM | No "thinking" mode to suppress; strong JSON + instruction following on CPU. |
| Semantic search | `all-minilm` (Ollama) | 46 MB | MiniLM-L6-v2, served by the same runtime so no extra PyTorch stack. |
| Speech-to-text | `faster-whisper tiny.en`, int8 | ~75 MB | English-only, CPU, ~0.5x real time. Downloaded from HF on first use. |

Everything is overridable via env vars (see `src/config.py`): `OLLAMA_HOST`,
`OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL`, `WHISPER_MODEL`, ... On an 8 GB machine the
whole app (Ollama models + Streamlit + Whisper + the full catalog cached for the
cart page) sits around 3.5-4.5 GB resident and stays out of swap.

`HF_TOKEN` is still required - the dataset pipeline uses it, and `faster-whisper`
uses the Hugging Face cache for its one-time model download.

## Run the app

```bash
# make sure Ollama is running first (ollama serve / systemctl start ollama)
streamlit run app.py
```

Three pages sharing one `{sku: quantity}` cart in `st.session_state`:

* **Assistant** (default) - speak or type. `st.audio_input` records in the
  browser; `faster-whisper` transcribes locally; the transcript then goes through
  the *same* `handle_user_message()` as typed text. Try:
  * `show me black jackets under 120`
  * `I'm going to a friend's birthday dinner, something casual under 80`
  * `show me something cheaper` / `similar options in blue` (refines the last search)
  * `add the second one` / `add the yellow one` (resolved against the shown results;
    genuinely ambiguous references are refused, not guessed)

  The LLM only ever emits a validated intent (`search_products` / `add_to_cart` /
  `respond`); Python does the filtering, ranking and every cart mutation.
* **Catalog** - the original manual grid over the full ~192k catalog: name
  search, category / brand / size facets, price range, "only discounted",
  applied on **Apply**, with pagination.
* **Cart** - full-size review with images, per-line quantity steppers, line
  totals and the subtotal. No checkout (out of scope for V1).

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest          # 90 tests, all pure logic - no Ollama / network needed
```

The assistant tests stub the LLM call (`tests/test_handler.py`) and cover
colour/gender extraction, hard filtering, intent-schema validation and reference
resolution. End-to-end behaviour with the real model is exercised by running the
app.
