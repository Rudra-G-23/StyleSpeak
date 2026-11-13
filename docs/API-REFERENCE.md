# API Reference

All cart and chat routes accept `X-StyleSpeak-Session`. The client creates an opaque UUID locally; there is no account or payment identity.

| Route | Purpose |
| --- | --- |
| `GET /api/health` | Service status and catalog count |
| `GET /api/products` | Small catalog listing |
| `GET /api/products/{sku}` | Product detail |
| `GET /api/products/{sku}/image` | Safely resolved local product image |
| `GET /api/products/{sku}/variants` | Conservative same-family color siblings |
| `POST /api/search` | Validated text query plus hard filters |
| `POST /api/chat` | Context-aware search, selection, or cart action |
| `POST /api/voice/transcribe` | Optional local audio transcription |
| `GET /api/cart` | Current session cart |
| `POST /api/cart/items` | Validated product and size add |
| `PATCH /api/cart/items/{sku}` | Quantity update or removal at zero |
| `DELETE /api/cart/items/{sku}` | Remove a product SKU from the session cart |

`POST /api/search` accepts `{query, filters, limit}`. `filters` supports gender, category, subcategory, color, min/max price, size, and brand. Responses include the interpreted filters, matching products, and an exact filtered total.
