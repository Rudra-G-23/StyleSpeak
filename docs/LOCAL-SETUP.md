# Local Setup

Prerequisites: Python 3.13 with `uv`, Node.js 24 or later, and the existing local dataset.

```bash
uv sync
uv run python -m backend.stylespeak_api.ingest --limit 2500
uv run uvicorn backend.stylespeak_api.main:app --port 8000
cd frontend
npm install
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

Open `http://127.0.0.1:5173`. To regenerate a larger catalog, increase `--limit`. The source JSON and image assets are never copied or deleted by the default ingestion command.

Voice transcription is optional. The UI accepts an audio file and reports a clear error if the local faster-whisper dependency or model cannot load.

For Docker, ingest the local catalog first and run `docker compose up --build`. The compose configuration bind-mounts `data/` so images and the local SQLite catalog are not baked into the container image.
