# Shopping Cart

## Objective

Maintain a validated session cart without a fake client-only checkout.

## Architecture

An opaque session header selects a transactional SQLite cart. Product and size validation happen server-side.

## Implementation

The frontend drawer calls the real cart routes; the backend persists cart lines and totals.

## Files Changed

`backend/stylespeak_api/models.py`, `repository.py`, `main.py`, `frontend/src/App.tsx`.

## Dependencies

FastAPI, SQLAlchemy, React Query.

## Testing

API and Playwright add-to-cart flows passed.

## Bugs Found

None after contract integration.

## Fixes Applied

N/A.

## Limitations

Checkout is intentionally a simulation.

## Future Improvements

Cart merge after authenticated sign-in.

## Completion Status

Implemented / Tested / Verified
