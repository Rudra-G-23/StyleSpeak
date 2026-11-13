# Frontend Design

## Objective

Provide a premium responsive shopping interface rather than a dashboard or chat-only UI.

## Architecture

React uses TanStack Query for server state and Motion for reduced-motion-safe transitions.

## Implementation

The client includes hero search, assistant panel, responsive product grid, detail modal, filters, voice file selection, cart drawer, and image-to-cart motion.

## Files Changed

`frontend/src/` and `frontend/e2e/`.

## Dependencies

React, Vite, Motion, Lucide, TanStack Query.

## Testing

TypeScript build and desktop/mobile Playwright passed. Screenshots are in `artifacts/screenshots/`.

## Bugs Found

Initial browser QA exposed CORS configuration and product-type ingestion errors.

## Fixes Applied

CORS now includes local development ports, and ingestion checks the product-type title segment.

## Limitations

The UI uses purpose-built primitives rather than a generated shadcn source set.

## Future Improvements

Add a native microphone recording control with an audio fixture test.

## Completion Status

Implemented / Tested / Verified
