# Performance Report

Measured locally on 2026-11-13, not estimates:

| Measurement | Result |
| --- | --- |
| Batch ingest, 500 accepted pants products | 2.30 s |
| Ingest peak RSS, same run | 62,820 KB |
| Final local demo catalog | 2,500 products, 2.4 MB SQLite database |
| Five real `POST /api/search` requests | 17.5-32.6 ms each |
| Production frontend build | 415.59 kB JS, 130.59 kB gzip |

The ingestion benchmark wrote a disposable `/tmp/stylespeak-perf.db`. Search measurements used the running 2,500-product FTS5 catalog and the query `Show black cargo pants under €100`.

The main remaining scaling bottleneck is semantic embedding generation for all 192k source records. It is deliberately excluded from startup and should be batched offline with a bounded worker count.
