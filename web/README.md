# StyleSpeak storefront (`web/`)

A standalone, framework-free storefront for the StyleSpeak project. Plain
HTML + CSS + one vanilla JS file, no build step, no `node_modules`. It does
**not** reuse the Streamlit look - it is its own editorial "contact sheet"
identity (raw paper + warm ink + a marker yellow that only ever marks what the
stylist understood).

## What's here

| File | Role |
| --- | --- |
| `index.html` | markup + the Google Fonts link |
| `styles.css` | the whole design system (light + dark, both themes designed) |
| `app.js` | catalog load, local hybrid retrieval, voice/text stylist, variants, cart and demo order |
| `products.json`, `images/` | 100-product local catalog and matching real Zalando dataset photos |
| `search-index.json` | generated TF-IDF embedding and BM25 retrieval index |
| `build.py` | builds portable `dist/` pages and copies their image assets |
| `Dockerfile`, `nginx.conf` | hardened static-server image on port 8080 |
| `dist/index.html`, `dist/images/` | portable page bundle with its real-image assets |
| `dist/index.fragment.html` | headless fragment - source for a Claude Artifact |

## Run it

```bash
python3 -m http.server 8000 --directory web
# then open http://localhost:8000/
```

Or run the same storefront in Docker:

```bash
docker build -t stylespeak-web web
docker run --rm -p 8080:8080 stylespeak-web
# then open http://localhost:8080/
```

## Refresh the real-image demo data

The checked-in sample uses 100 products and photos from the public
`thivav/zalando_fashionista_x100` dataset. Refresh it when needed:

```bash
uv run python scripts/import_web_demo.py
python3 web/build.py
```

The importer downloads the photos into `web/images/` and regenerates
`web/products.json`. The storefront never calls Hugging Face at runtime.

`app.js` reads `window.__CATALOG__` and `window.__SEARCH_INDEX__` when the
catalog is inlined (the `dist/` builds), and otherwise fetches `products.json`
and `search-index.json`. The raw folder needs to be served over HTTP - opening
`web/index.html` straight off disk will not load the catalog. `web/dist/index.html`
has no such constraint.

## Rebuild the single-file outputs

```bash
python3 web/build.py
```

Idempotent: same inputs produce byte-identical output. Run it after editing
`index.html`, `styles.css`, `app.js` or `products.json`.

## The stylist

The search bar and multi-turn stylist take a sentence ("a navy jacket under
€150", "something in burgundy", "navy tailoring") and `parseQuery()` turns it
into colour, cut, occasion, gender and budget constraints. Retrieval is hybrid
but local: hard constraints keep gender, colour and price truthful; a generated
TF-IDF embedding scores cosine similarity; BM25 scores keyword relevance; and
the blended score ranks catalog results. The stylist shows its reading back in
yellow, exposes removable chips, and explains when it must widen only a budget
or cut constraint. It never widens a requested gender.

Use **Speak** to dictate a search or chat message when the browser offers the
Web Speech recognition API. Chat replies can be read aloud only after the user
enables that option. No voice or shopping data leaves the browser.

Products require a size before they are added to the persistent local cart. The
order review is deliberately a demo: it confirms locally and never requests
payment or address data.

Vocabulary (colour synonyms, category words, occasion → category sets, stop
words) lives at the top of `app.js`.

## Browser support

The catalog, text stylist, variants and bag work in current evergreen browsers.
Speech input depends on a browser-provided `SpeechRecognition` implementation
(commonly Chromium-based browsers). When unavailable, the voice controls are
disabled while all typed interactions remain available.

## Regenerating the demo catalog

`products.json` is a compact local demonstration slice from the same Hugging
Face dataset as the Streamlit pipeline. It and `images/` are committed so the
storefront works with zero setup and without a runtime network request.
