# Database Schema

`products` is the normalized immutable demo catalog. Its primary key is the original SKU; it stores evidence-derived `gender`, canonical pants `category`, optional subcategory and color, price, local image path, sizes JSON, family key, and search text.

`products_fts` is SQLite FTS5 data for lexical ranking. It is rebuilt after a completed ingestion, not per request.

`carts` maps one opaque browser session ID to a cart. `cart_items` maps a product SKU and optional selected size to a quantity. A unique constraint on `(cart_id, sku, size)` prevents duplicate variant lines. Product and size are validated before a cart write is committed.

The portable SQLAlchemy model can be migrated to PostgreSQL. For a production PostgreSQL deployment, use native `JSONB` sizes, a `tsvector` index, and pgvector embeddings behind the existing retrieval module.
