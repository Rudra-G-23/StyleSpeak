# Existing Project Audit

## Scope and method

This audit was completed before modifying the application. It inspected the working branch, every accessible local and remote branch, the implementation rather than only the README, the checked-in catalog, cached local models, and the existing automated checks.

## Repository and history

The active branch is `feat/cool-ui-v2` at `d279da0`. Accessible branches are `main` / `feat/streamlit-version`, `feature/catalog-filters-cart-polars`, `feat/cool-ui` / active branch, and the unmerged `feat/model` local-model experiment.

The project currently contains three competing implementations:

1. `app.py`, `views/`, and `src/ui.py` - Streamlit catalog and cart.
2. `web/` - a self-contained vanilla JavaScript storefront.
3. `feat/model` history - an unmerged Streamlit assistant experiment using Ollama and faster-whisper.

## Existing architecture

`src/metadata.py` safely cleans raw rows and normalizes prices, lists, sizes, and SKU file names. `scripts/download_dataset.py` downloads the Hugging Face dataset and images into `data/products/`. `src/catalog.py` loads all `products.json` rows into Polars and applies filters in memory. `src/cart.py` supplies small, well-tested cart functions. Streamlit pages render the catalog and cart from that state.

`web/` contains plain HTML, CSS, and one JavaScript file. It includes a committed 100-product local demonstration catalog, local images, a generated TF-IDF plus BM25 index, client-side query parsing, browser Web Speech API integration, local browser cart persistence, and a static Nginx image. It has no backend.

The `feat/model` branch has Pydantic intent schemas, validated result-reference resolution, optional Ollama JSON intent parsing, Ollama embeddings, and `faster-whisper` tiny English transcription. It was not merged and depends on Streamlit plus a local Ollama service.

## Data and models verified

`data/products/products.json` contains 191,938 records, all in EUR. Its fields are `sku`, `name`, `brand`, `category`, `categories`, `classification`, `sizes`, original and promotional pricing, image path, and source URL. The dataset has eight top-level categories, including 19,161 `Jeans` records but no normalized men's-trousers category.

All 191,938 records reference a local image path, and the first 50 image files passed Pillow verification. The source dataset cache reports 192,126 raw rows, with embedded image bytes and stringified categories and size-SKU entries. The downloaded app catalog loses per-size SKU relationships. The checked-in web slice is a separate 100-product demo catalog.

Available cached local models are `sentence-transformers/all-MiniLM-L6-v2` and `Systran/faster-whisper-tiny.en`. Ollama is installed with `all-minilm` and several 0.4-1.9 GB language models. The project has no configured model dependency or evidence that an Ollama server is active, so an LLM cannot be a critical path.

## Working functionality

- Metadata parsing and pricing reconciliation are robust and unit-tested.
- Polars filtering, sorting, pagination, and pure cart calculations are unit-tested.
- Dataset ingestion has already produced a complete local catalog and image set.
- The static storefront runs without a package install and demonstrates client-side cart, filters, simple retrieval, and browser speech recognition.
- Baseline verification passed: `uv run pytest` collected 47 tests, all passed; Ruff lint and format checks also passed.

## Broken or incomplete functionality

- There is no FastAPI server, database schema, migration, REST contract, or persistent server-side cart.
- Streamlit and the static app are competing user interfaces rather than one integrated product.
- `src/catalog.py` reads the full 192k JSON catalog into memory for each process, unsuitable as the production query path on 8 GB RAM.
- The static app only searches a 100-product demo slice. Its vectors are sparse TF-IDF weights, not semantic embeddings.
- There is no verified product-family variant model. The dataset only exposes individual SKUs and sizes; color is inferred from names in the demo.
- The model branch relies on an optional Ollama server and has no deterministic parser fallback.
- Browser speech recognition is not local transcription and varies by browser.
- No database/API integration tests, browser end-to-end tests, React/Vite application, TypeScript checks, or performance measurements exist.

## Technical debt and performance concerns

- `web/dist/` duplicates source assets and is a generated artifact maintained alongside source.
- The Streamlit helper uses a remote placeholder image, violating otherwise offline behavior.
- Runtime JSON loading is not scalable.
- Category and gender assumptions are scattered and string-based. Product type, color, gender, and families need one normalized representation.
- A complete embedding matrix must not be loaded eagerly. The initial catalog must be a validated men's-pants subset, with batched optional embedding generation.
- Dataset source URLs and imagery have reuse constraints that must be respected. The app must describe its catalog as a static local demo and must not claim stock or checkout.

## Reusable pieces

- Preserve `src/metadata.py` parsing principles and the data directory.
- Preserve pure cart calculation semantics as migration test cases.
- Preserve the dataset downloader only as a source reference. Replace its target format with batch ingestion.
- Preserve validated conversational product-reference resolution from `feat/model`. Do not preserve its Streamlit or Ollama coupling.
- Preserve the real local images and selected curated data, not the old UI architecture.

## Recommended replacement

Build a Vite React TypeScript client and FastAPI backend. Use SQLite with FTS5 for the local demo because it requires no resident service and fits the 8 GB constraint. Retain a SQLAlchemy seam and PostgreSQL/pgvector-ready schema for deployment. The backend persists a validated subset from the actual catalog, serves local image files, applies hard filters before retrieval, and stores carts by opaque browser session ID. Deterministic parsing is the reliability baseline. A lazy MiniLM semantic reranker and cached `faster-whisper-tiny.en` voice adapter are optional runtime enhancements.

## Migration risks

- Deleting the old UI before proving the new user workflow would lose a runnable fallback. Create a Git checkpoint before removal.
- Dataset category labels are coarse, so gender, type, color, and family fields must be evidence-derived and `unknown` when uncertain.
- Bulk embeddings for 192k records are outside the first release scope.
- Browser automation tooling may not be installed. Browser verification must be reported accurately if unavailable.
- PostgreSQL with pgvector may not be locally installed. The local SQLite adapter must remain fully functional.
