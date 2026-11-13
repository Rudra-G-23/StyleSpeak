# Interview Demo Guide

1. Start the backend and frontend using [Local Setup](LOCAL-SETUP.md).
2. Open the homepage and point out the local-first assistant and real local product images.
3. Enter `Show black cargo pants under €100` to show four validated catalog records. Explain that adding `men's` deliberately returns only the one evidence-supported unisex product.
4. Ask the stylist `show me cheaper ones`, then `show the second product` to demonstrate session context.
5. Ask `add the first one to my cart` or use a product add button. Show the product-to-bag flight, persisted cart drawer, and quantity controls.
6. Choose an audio file with a short recorded fashion query to demonstrate local voice transcription if faster-whisper is available.
7. Explain that hard filters run before FTS ranking, cart SKUs are server-validated, and no LLM can invent a product.

The intended walkthrough is three to five minutes. Do not claim live stock or checkout.
