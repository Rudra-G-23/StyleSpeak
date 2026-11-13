# Testing

Executed on 2026-11-13:

```text
uv run pytest                 5 passed (active backend tests)
uv run ruff check .           passed
uv run ruff format --check .  passed
cd frontend && npm run typecheck && npm run build  passed
cd frontend && npm run test:e2e                    4 passed
```

The Playwright flow uses Chromium against the running Vite client and FastAPI service. It submits a natural-language product query, verifies catalog cards, adds a real result to the session cart, opens the drawer, and covers desktop and mobile projects. Screenshots are stored in `artifacts/screenshots/`.

External Starlette/AnyIO deprecation warnings were emitted by the installed TestClient dependency during backend tests. They do not originate in application code.
