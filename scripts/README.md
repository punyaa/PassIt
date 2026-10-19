# PassIt scripts

- `loadtest/contention.js` — B1 Booking owns the correctness harness.
- `loadtest/smoke.js` — P1 Platform owns general staging smoke/load checks.
- Future deterministic seed tools belong in `seed/` and are owned by B3 Catalogue.
- Future demo reset tools belong in `demo-reset/` and are owned by P1 Platform.

Scripts must default to non-production targets and require an explicit base URL.
