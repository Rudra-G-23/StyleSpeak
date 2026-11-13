# Conversational Memory

## Objective

Resolve follow-up shopping requests without inventing products.

## Architecture

Session-keyed state holds only interpreted filters and the SKUs from the last visible result list.

## Implementation

`conversation.py` handles cheaper refinements, ordinals, selected products, and cart commands.

## Files Changed

`backend/stylespeak_api/conversation.py`, `main.py`.

## Dependencies

FastAPI and SQLAlchemy.

## Testing

The API test covers `add the first one to my cart` after a chat search.

## Bugs Found

None.

## Fixes Applied

N/A.

## Limitations

Context resets when the backend restarts.

## Future Improvements

Persist short-lived conversation state in the database.

## Completion Status

Implemented / Tested / Verified
