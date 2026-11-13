# AWS Deployment

Do not provision AWS resources from this repository automatically.

For a small deployment, run the FastAPI container and React static build on one EC2 instance behind a reverse proxy. Keep SQLite only for demos. For multi-instance deployment, migrate the SQLAlchemy schema to RDS PostgreSQL, use pgvector for precomputed embeddings, and move authorized image assets to S3 behind CloudFront.

Use environment variables for `DATABASE_URL`, `CORS_ORIGINS`, model paths, and asset storage. A CPU-only instance is sufficient for lexical search; voice transcription and optional embeddings need careful concurrency limits. Dataset image licensing and redistribution rights must be verified before placing product assets in public object storage.
