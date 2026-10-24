# PassIt scripts

- `loadtest/contention.js`: B1 Booking's correctness harness (k6).
- `loadtest/smoke.js`: P1 Platform's general staging smoke and load checks.
- Python tools that need the app's code live in `api/scripts/` and run with `uv run --directory api python -m scripts.<name>`:
  - `seed`: deterministic demo data (B3). `--reset` wipes the database first.
  - `contention_setup`: creates a listing plus N borrowers with tokens, as inputs for `contention.js` (B1).
  - `release_due_fees`: releases every fee whose hold period has ended; idempotent (B2).
- Future demo-reset tools belong in `demo-reset/` and are owned by P1 Platform.

Scripts must default to non-production targets and require an explicit base URL.

## Contention run

```bash
uv run --directory api python -m scripts.contention_setup --borrowers 50 > /tmp/k6.env
set -a; . /tmp/k6.env; set +a
k6 run -e BASE_URL=http://localhost:8000 scripts/loadtest/contention.js
```

The run passes when its thresholds hold: exactly one `201`, and every other response a `409`. For the Week 4 100-repeat evaluation, either run `contention_setup` again before each run, or pass a different `-e START_OFFSET_DAYS=<n>` each time so the runs book disjoint dates. Default listing availability covers 365 days.
