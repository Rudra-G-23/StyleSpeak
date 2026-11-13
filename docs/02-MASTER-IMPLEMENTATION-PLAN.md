# Master Implementation Plan

## Target architecture

```text
React + TypeScript + Vite client
  | REST, opaque session id
FastAPI application
  |-- Catalog module: filtering, ranking, variants, local images
  |-- Conversation module: deterministic intent parsing and contextual references
  |-- Cart module: validated transactional cart operations
  |-- Voice module: lazy local faster-whisper adapter
  |-- Repository adapter: SQLite/FTS5 locally, PostgreSQL/pgvector-ready later
  `-- Batch ingestion command: source JSON -> normalized product catalog
```

The key deep modules are the repository module, which hides SQL and index mechanics; catalog search, which hides filters and ranking; and conversation, which hides parsing and contextual reference resolution. The client calls small, stable HTTP interfaces rather than knowing storage or model details.

## Key decisions

- Use React, TypeScript, Vite, Tailwind, TanStack Query, Motion, and Lucide for the new client.
- Use FastAPI, Pydantic, SQLAlchemy, and Alembic-ready metadata for the backend.
- Use SQLite and FTS5 locally as the default adapter. It is simpler and more reliable on the specified hardware than requiring a PostgreSQL server. The schema keeps a migration path to PostgreSQL and pgvector.
- Begin with a real, normalized men's-pants subset from the existing catalog. Ingestion remains batch-oriented and configurable for expansion.
- Parse explicit price, color, gender, type, size, and ordinal constraints deterministically. The optional local LLM cannot mutate data or invent SKUs.
- Use lexical FTS plus token relevance and reciprocal-rank fusion first. Add a lazy MiniLM semantic reranker behind the retrieval module when enabled, using the cached model and offline batched embeddings.
- Use cached `faster-whisper-tiny.en` only when the voice endpoint receives audio. The site remains usable without it.

## Data model

- `products`: immutable normalized catalog fields, searchable text, gender, category, subcategory, color, price, image path, and source URL.
- `product_variants`: verified color sibling links only, created from conservative normalized family keys.
- `carts` and `cart_items`: opaque session-scoped carts, SKU identity, selected size, selected SKU variant, quantity, and timestamps.
- `ingestion_runs`: catalog provenance, source record count, accepted/rejected count, and timestamps.

Mandatory filters are applied in SQL before lexical or semantic ordering. A result cannot bypass gender, category, color, price, brand, or size constraints.

## HTTP interface

- `GET /api/health`
- `GET /api/products`, `GET /api/products/{sku}`, `GET /api/products/{sku}/variants`
- `POST /api/search`
- `POST /api/chat`
- `POST /api/voice/transcribe`
- `GET /api/categories`, `GET /api/filters`
- `GET /api/cart`, `POST /api/cart/items`, `PATCH /api/cart/items/{sku}`, `DELETE /api/cart/items/{sku}`

All mutations use an opaque session header, validated request schemas, and transactional repository operations. Error responses use a consistent Pydantic problem shape.

## Milestones and acceptance checks

### v0.1 - Data foundation

1. Create normalized SQLite schema and batch ingestion command.
2. Classify actual catalog records into men's pants types using auditable rules.
3. Validate prices and image paths; preserve only usable first-release entries.
4. Verify catalog counts, image serving, and filters with integration tests.

### v0.2 - Retrieval

1. Implement deterministic query understanding and schemas.
2. Implement filtered lexical retrieval and reciprocal-rank fusion.
3. Add optional lazy MiniLM semantic embedding adapter and offline batch command.
4. Test constraints, relevance examples, references, and latency.

### v0.3 - Shopping application

1. Build a responsive React client against the backend contract.
2. Implement discovery, details, filters, assistant results, loading and error states.
3. Verify desktop, tablet, and mobile browser behavior.

### v0.4 - Conversation and voice

1. Maintain session context.
2. Support refinements, product selection, and cart references deterministically.
3. Add lazy server-side transcription with a reproducible test adapter.

### v0.5 - Cart and polish

1. Persist and validate cart operations.
2. Support verified variants and sizes.
3. Add reduced-motion-safe product-to-cart animation and cart drawer.

### v1.0 - Demo release

1. Run lint, type, unit, integration, and browser tests.
2. Document performance, setup, deployment readiness, and the demo script.
3. Remove obsolete UI only after the new workflow passes.

## Dependency graph

```text
Audit -> contracts/schema -> ingestion -> backend retrieval -> API tests
                   |                             |              |
                   v                             v              v
            client scaffolding ------------> real client ----> E2E QA
                   |
                   v
          voice adapter + chat context ------> assistant UI
```

After shared contracts exist, ingestion/backend, client, and test/documentation work can proceed independently. Integration occurs through OpenAPI and contract tests.

## Testing and operations

- Backend: pytest, Ruff, HTTP integration tests against temporary SQLite.
- Client: TypeScript checking, Vitest/Testing Library, and Playwright browser flows.
- Performance: measure catalog ingest, database query, search latency, model load, and peak RSS where available. Never label estimates as measurements.
- Containerization: separate client and backend Dockerfiles, Compose for local orchestration, environment-based configuration, health checks, no cloud provisioning.
- AWS readiness: Docker services can run on EC2; PostgreSQL may move to RDS, and authorized product assets to S3/CloudFront. Documentation only.

## File ownership

- `backend/` - data, retrieval, HTTP, and backend tests.
- `frontend/` - client, styles, and browser tests.
- `docs/` - architecture and release documentation.

No legacy Streamlit or `web/` file will be altered until the replacement runs end to end and a recoverable Git checkpoint exists.
