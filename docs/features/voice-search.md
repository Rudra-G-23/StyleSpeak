# Voice Search

## Objective

Allow an audio request to enter the same validated shopping flow as text.

## Architecture

The client uploads selected audio without blocking the UI. The backend lazily loads local faster-whisper tiny English with CPU int8, returns a transcript, and the user can edit it before search.

## Implementation

`voice.py`, `/api/voice/transcribe`, and the client audio chooser implement the flow.

## Files Changed

`backend/stylespeak_api/voice.py`, `main.py`, `frontend/src/App.tsx`, `api.ts`.

## Dependencies

faster-whisper and cached `tiny.en` model.

## Testing

Error behavior is implemented; a reproducible spoken-audio fixture was not available for automated transcription verification.

## Bugs Found

None.

## Fixes Applied

N/A.

## Limitations

The UI currently selects an audio file rather than recording directly from the microphone.

## Future Improvements

Add MediaRecorder controls and a deterministic audio fixture.

## Completion Status

Implemented / Partially tested / Not audio-fixture verified
