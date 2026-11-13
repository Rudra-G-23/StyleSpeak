# StyleSpeak

StyleSpeak is a local-first AI fashion-shopping demo built for an 8 GB development machine. It pairs a premium React storefront with a FastAPI catalog service, a validated SQLite/FTS5 product subset, conversational reference resolution, session carts, real local dataset images, and optional local speech transcription.

The active application lives in `frontend/` and `backend/`. Prior Streamlit and framework-free experiments were preserved under `legacy/` after a recovery branch was created; they are not runtime dependencies.

## Run locally

```bash
uv sync
uv run python -m backend.stylespeak_api.ingest --limit 2500
uv run uvicorn backend.stylespeak_api.main:app --port 8000
```

In another terminal:

```bash
cd frontend
npm install
VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

Open `http://127.0.0.1:5173`.

## Quality checks

```bash
uv run pytest tests_backend -q
uv run ruff check backend tests_backend
cd frontend && npm run typecheck && npm run build
cd frontend && npm run test:e2e
```

Read [the local setup guide](docs/LOCAL-SETUP.md), [architecture](docs/ARCHITECTURE.md), [known limitations](docs/KNOWN-ISSUES.md), and [interview demo](docs/INTERVIEW-DEMO-GUIDE.md) before presenting the project.
