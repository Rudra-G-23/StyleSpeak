# Architecture

StyleSpeak is now a local-first React and FastAPI application. The React client in `frontend/` talks to `backend/stylespeak_api/` over REST and carries an opaque browser session ID. The backend owns catalog filtering, ranking, conversation context, cart validation, and image delivery.

The local persistence adapter is SQLite plus FTS5. It avoids requiring a resident database service for the interview demo while `Product`, `Cart`, and `CartItem` SQLAlchemy models keep a portable path to PostgreSQL. Catalog search applies hard SQL filters first, then combines FTS ranking and token relevance through reciprocal-rank-style scoring. No ranking path can relax mandatory filters.

The ingestion module streams the JSON array through `JSONDecoder.raw_decode`, rather than loading all 192k rows. It normalizes a real pants subset, verifies local image paths, and builds the lexical index after batch commits.

Conversation context is keyed by the opaque session ID. It tracks the latest result SKUs and filters. Ordinal actions are resolved only against those stored SKUs before the cart repository can mutate data.
