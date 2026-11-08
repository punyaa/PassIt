# PassIt scripts

- `loadtest/contention.js`: B1 Booking's correctness harness (k6).
- `loadtest/smoke.js`: Platform's quick `/health` check.
- `loadtest/search.js`, `loadtest/booking.js` and `loadtest/evaluate.sh`: Platform's evaluation suite (search ramp, booking load, elasticity spike, fault recovery, cost). Run `AWS_PROFILE=nus-sso scripts/loadtest/evaluate.sh all pilot` for a quick pass or `full` for the report numbers. Results go to `loadtest/results/` (git-ignored).
- Python tools that need the app's code live in `api/scripts/` and run with `uv run --directory api python -m scripts.<name>`:
  - `seed`: deterministic demo data (B3), with bundled photos, lender bios, saved items and coherent rental history. `--reset` wipes the database first. Content and photo sources live in `api/scripts/demo/`; `seed-01@passit.demo` demonstrates both rental roles.
  - `contention_setup`: creates a listing plus N borrowers with tokens, as inputs for `contention.js` (B1).
  - `release_due_fees`: releases every fee whose hold period has ended; idempotent (B2).
- `demo-reset/reset.sh <staging|demo>`: Platform's one-command reset. Runs the migration and seed as a one-off ECS task, then checks the site. Seed users sign in as `seed-01@passit.demo` to `seed-20@passit.demo` with password `passit-demo-2026`.

Scripts must default to non-production targets and require an explicit base URL.

## Contention run

```bash
uv run --directory api python -m scripts.contention_setup --borrowers 50 > /tmp/k6.env
set -a; . /tmp/k6.env; set +a
k6 run -e BASE_URL=http://localhost:8000 scripts/loadtest/contention.js
```

The run passes when its thresholds hold: exactly one `201`, and every other response a `409`. For the Week 4 100-repeat evaluation, either run `contention_setup` again before each run, or pass a different `-e START_OFFSET_DAYS=<n>` each time so the runs book disjoint dates. Default listing availability covers 365 days.

## Cloud evaluation runs

`loadtest/evaluate.sh <search|booking|elasticity|fault|cost|all> [pilot|full]` runs against **staging** (it refuses any other environment) and writes k6 summaries plus an ECS task-count timeline to `loadtest/results/<timestamp>/`. Reset the data first with `demo-reset/reset.sh staging`, because the booking run needs the fresh seed.

- `pilot` is quick (about 12 minutes for everything) and checks the scripts. `full` is the report run: search 10 to 200 VUs over 10 minutes, 20 bookings/s for 5 minutes, a 20 to 200 VU spike, and fault injection mid-run.
- **Hold the spike for at least 5 minutes.** ECS target tracking scales out only after CPU stays above 60% for 3 consecutive minutes. A 2-minute spike saturates the tasks (p95 near 900 ms) without adding one. `HOLD_MIN=6 scripts/loadtest/evaluate.sh elasticity pilot` shows the scale-out.
- **Scale-out is slow by design.** Target tracking needs 3 consecutive 1-minute datapoints above the target plus CloudWatch lag, so the third task took about 5 minutes after CPU crossed 60%. Under that load p95 stayed near 950 ms. A reaction time of about 2 minutes needs step scaling with a 1-minute alarm instead.
- The fault run stops one of the two API tasks mid-load and records the error rate and how long the replacement takes.

Pilot numbers from 2026-10-24 (2 API tasks, 0.25 vCPU each, through CloudFront):

| Run | Result |
| --- | --- |
| Search ramp to 40 VUs, 1 minute | 2,151 requests, 0 failures, p95 30 ms |
| Booking load, 5/s for 30 s | 149 created and 2 conflicts with seeded dates, 0 rejected, p95 745 ms |
| Spike 20 to 150 VUs, 2-minute hold | 16,072 requests, 0.02% failed, p95 912 ms, max 2.8 s; no scale-out (CPU above target for only 2 minutes) |
| Spike 20 to 150 VUs, 6-minute hold | 39,774 requests, 0.04% failed, p95 953 ms, max 3.5 s. CPU passed the 60% target at minute 3; a third task was requested 401 s into the run and was serving at 447 s |
| Fault: stop 1 of 2 tasks mid-load | 0 failures in 2,617 requests; replacement running after 77 s |
| Cost | Cost Explorer returned USD 0.00 for the last 7 days (billing data lags, and the account is linked), so cost per rental is still to be measured |

These are pilot-scale numbers, not the report figures. Rerun with `full` after feature freeze.

## Thumbnails

`thumbnails/backfill.sh <staging|demo>` thumbnails listing photos uploaded before the thumbnailer existed, by invoking it once per photo. New uploads need nothing.
