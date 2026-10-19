# PassIt API

FastAPI backend owned across four streams:

- `app/auth/` — P1 Platform
- `app/catalogue/` and `app/media/` — B3 Catalogue
- `app/bookings/` and `app/reviews/` — B1 Booking
- `app/transactions/` — B2 Transactions

The routes are intentionally contract-first stubs. Endpoints that would mutate state return HTTP 501 until their database invariants are implemented. Frontend development uses the matching MSW handlers in `web/mocks/`.

## Development

```bash
uv sync --project api --dev
uv run --directory api uvicorn app.main:app --reload --port 8000
uv run --directory api pytest
```

Export the committed OpenAPI contract after changing routes or schemas:

```bash
uv run --directory api python -m scripts.export_openapi
```

Review the resulting `api/openapi.json` in the same pull request as the API change.
