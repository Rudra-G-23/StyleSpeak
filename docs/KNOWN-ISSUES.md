# Known Issues

- The source catalog does not provide authoritative gender, color, description, stock, or family fields. Unknown gender is intentionally not guessed as men.
- The exact phrase `black men's cargo pants under €100` has one conservatively valid unisex result in the initial 2,500-product demo catalog. The broader `black cargo pants under €100` query has four actual records. The demo must state this rather than fabricate men's products.
- Voice transcription is implemented but not automated with an audio fixture in this environment.
- The current retrieval release is FTS/token hybrid. Offline MiniLM vector indexing and PostgreSQL pgvector are future work.
- Checkout is a simulation only. No payments, addresses, availability, or live inventory are claimed.
