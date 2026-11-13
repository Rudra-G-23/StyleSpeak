# Dataset Pipeline

Source data remains the existing local Zalando Fashionista export at `data/products/products.json`; its original images stay in place. Run:

```bash
uv run python -m backend.stylespeak_api.ingest --limit 2500
```

The default output is ignored `data/stylespeak-v2.db`. The command streams records, accepts valid local images and prices, extracts actual product-type segments such as `Cargo trousers`, and only retains pants. It does not accept a T-shirt merely because a later color/style label mentions "jeans".

Gender is evidence-conservative: explicit women, unisex, or men signals are retained; absent evidence becomes `unknown`. A gender-filtered search excludes unknowns, while unconstrained browsing may show them as local catalog records. The source data lacks dependable family and color fields, so variants are only offered for conservative same-brand/title-stem families.
