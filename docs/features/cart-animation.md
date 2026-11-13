# Cart Animation

## Objective

Give successful cart additions visible continuity with the shopping bag.

## Architecture

The client starts the visual transition only while the validated cart mutation is in flight. Motion animates the selected image from its card to the bag icon; the cart opens after the backend accepts the line.

## Implementation

`App.tsx` uses image and bag bounding rectangles with Motion and honors `prefers-reduced-motion`.

## Files Changed

`frontend/src/App.tsx`, `styles.css`.

## Dependencies

Motion for React.

## Testing

The browser workflow verifies real add-to-cart and drawer updates. Visual screenshots were inspected.

## Bugs Found

None.

## Fixes Applied

N/A.

## Limitations

Visual-frame assertions are not yet pixel-diffed.

## Future Improvements

Add deterministic visual regression snapshots.

## Completion Status

Implemented / Tested / Verified
