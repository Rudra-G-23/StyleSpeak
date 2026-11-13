# Hybrid Search

## Objective

Return real local products while preserving mandatory shopper constraints.

## Architecture

The retrieval module deterministically extracts filters, applies them in SQL, gets FTS5 lexical ranks, and blends lexical rank with token relevance.

## Implementation

`backend/stylespeak_api/retrieval.py` and `repository.py` implement parsing, hard filters, FTS5, and ranking.

## Files Changed

`backend/stylespeak_api/retrieval.py`, `repository.py`, `schemas.py`.

## Dependencies

FastAPI, SQLAlchemy, SQLite FTS5.

## Testing

Backend API tests and live search measurements passed.

## Bugs Found

The count query initially omitted its `FROM` clause.

## Fixes Applied

Counts now run over the filtered query subquery.

## Limitations

Semantic MiniLM vectors are not yet enabled.

## Future Improvements

Add offline embeddings and pgvector adapter.

## Completion Status

Implemented / Tested / Verified
