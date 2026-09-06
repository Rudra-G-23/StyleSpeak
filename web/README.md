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
| `app.js` | catalog load, the **AI stylist** query parser, grid, cart |
| `products.json` | 44-item curated demo catalog (same record shape as the full pipeline, plus `color` / `gender` / `type`) |
| `build.py` | inlines the four files into `dist/` single-file builds |
| `dist/index.html` | complete self-contained page - open via `file://` or host anywhere |
| `dist/index.fragment.html` | headless fragment - source for a Claude Artifact |

## Run it

```bash
python3 -m http.server 8000 --directory web
# then open http://localhost:8000/
```

`app.js` reads `window.__CATALOG__` when the catalog is inlined (the `dist/`
builds) and otherwise `fetch`es `./products.json`, so the raw folder needs to be
served over HTTP - opening `web/index.html` straight off disk won't load the
catalog. `web/dist/index.html` has no such constraint.

## Rebuild the single-file outputs

```bash
python3 web/build.py
```

Idempotent: same inputs produce byte-identical output. Run it after editing
`index.html`, `styles.css`, `app.js` or `products.json`.

## The stylist (the "something")

The search bar takes a sentence ("a navy jacket under €150", "something in
burgundy", "navy tailoring") and `parseQuery()` in `app.js` turns it into
colour / cut / occasion / gender / budget constraints, entirely client-side -
no model, no network. It then shows its reading back: your sentence re-rendered
with the words it used marked in yellow, plus removable constraint chips. If a
literal keyword matches nothing it relaxes the query step by step rather than
returning an empty rack.

Vocabulary (colour synonyms, category words, occasion → category sets, stop
words) lives at the top of `app.js`.

## Regenerating the demo catalog

`products.json` is hand-curated for a believable, category-balanced grid. It is
independent of `scripts/download_dataset.py` / the Hugging Face dataset, so the
storefront works with zero setup.
