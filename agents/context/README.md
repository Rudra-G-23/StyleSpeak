# StyleSpeak web storefront - delivery context

## Goal

Turn `web/` into a self-contained fashion-shopping demonstration that can be
served locally or in Docker. It must support catalog discovery by text and
voice, transparent shopping assistance, product variants, cart management and
a safe demo order flow.

## Existing system

- `app.py` and `views/` are the established Streamlit catalog and cart.
- `web/` is a dependency-free vanilla JavaScript storefront backed by a local
  100-product catalog and matching photos imported from the public dataset.
- The full Hugging Face pipeline writes a separate generated data set under
  `data/`; the web demo intentionally remains runnable without downloading it.

## Delivery plan

1. Keep the local catalog as the zero-setup demo data source and normalise
   access to its `colour`, category, price, brand, type and sizes fields.
2. Add a local hybrid retriever: explicit fashion constraints first, then
   lexical scoring across product fields, with a small deterministic semantic
   vocabulary for colour, occasion and garment intent. Expose the applied
   constraints so recommendations are explainable.
3. Add a multi-turn stylist panel that accepts typed messages and browser
   speech recognition when available. Use browser speech synthesis only after
   an explicit user action, never autoplay.
4. Add variant selection before adding an item, a persistent cart keyed by
   SKU and size, and a demo checkout confirmation. No payment data is collected
   or sent anywhere.
5. Add a production-oriented static Docker image, caching and security headers.
6. Remove the catalog's unnecessary outside edge borders, add mobile and
   keyboard behavior, then run static, unit and browser-level checks.

## Model decision

No Hugging Face model is downloaded for this showcase. A model would add a
large runtime and server requirement without improving the constrained 44-item
catalog demo. The hybrid retriever is intentionally local, inspectable and
fast: rule-based intent extraction supplies the semantic signal and token
overlap/field weighting supplies lexical retrieval. Voice is provided by the
browser's Web Speech APIs and degrades cleanly when the browser does not offer
them.

## Delivered architecture

- `web/app.js` is the single client-side application boundary. It reads the
  local JSON catalog, parses fashion intent, ranks products, manages cart
  variants, and drives the text/voice stylist.
- Retrieval is a local hybrid: hard intent constraints first narrow the catalog,
  then a generated TF-IDF embedding provides cosine similarity and BM25 provides
  lexical relevance. The blended rank is explainable. Gender is never relaxed;
  only price and cut constraints may widen with a visible explanation.
- The cart persists in browser local storage as `SKU::size` entries. A size is
  mandatory before a product can be added.
- Voice recognition is opt-in through `SpeechRecognition`; speech output is
  opt-in through a visible "Read replies aloud" control. Typed flows work when
  either API is absent.
- Catalog cards and stylist recommendations use locally bundled real product
  photos and show prices with their recommended products.
- On desktop, the stylist opens as a right-hand sidebar rather than a centered
  dialog. It locks storefront scrolling while open and keeps its chat history
  independently scrollable. A visible "Back to shop" action closes it. On
  smaller screens it remains a focused modal conversation.
- `web/Dockerfile` packages the site in Nginx on port 8080. `nginx.conf` adds
  static caching, basic response hardening and a microphone permission policy.

## Validation completed

```bash
python3 web/build.py
node --check web/app.js
git diff --check
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

- The rebuilt self-contained documents are in `web/dist/`.
- All 47 project tests pass; Ruff lint and formatting checks pass.
- A temporary HTTP server was smoke-tested at `/`, `/products.json`, and
  `/app.js`; the real product-image response was also checked, then the server
  stopped cleanly.
- Docker image execution could not be tested in this WSL environment because
  Docker Desktop WSL integration is disabled. The documented build command is
  ready to run once that integration is enabled.
