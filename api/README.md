# PassIt API

FastAPI backend owned across four streams:

- `app/auth/` — Platform
- `app/catalogue/` and `app/media/` — B3 Catalogue
- `app/bookings/` and `app/reviews/` — B1 Booking
- `app/transactions/` — B2 Transactions
- `app/integrations/` — external services (S3, EventBridge, Bedrock/LLM, OneMap); AWS parts handed to Platform

`app/models.py` mirrors the Alembic schema for queries; migrations remain the source of truth.

## Development

```bash
uv sync --project api --dev
uv run --directory api alembic upgrade head
uv run --directory api python -m scripts.seed --reset     # 22 users, 43 listings, 17 bookings
uv run --directory api uvicorn app.main:app --reload --port 8000
```

The seed prints session tokens. Paste one into **Authorize** at <http://localhost:8000/docs> to call authenticated endpoints.

The seed includes bundled listing photos, distinct descriptions and lender bios, saved items, paused listings and rental history dated relative to the reset day. `seed-01@passit.demo` demonstrates both borrowing and lending, including upcoming pickups and a return due. See [demo content](scripts/demo/README.md) for photo provenance and scenario details. Resetting does not download external images.

### Tests

Database tests need PostgreSQL 16 because double-booking prevention lives in an exclusion constraint. The suite creates and migrates its own `passit_test` database:

```bash
docker compose up -d postgres
uv run --directory api pytest
# Different host or port:
PASSIT_TEST_DATABASE_URL=postgresql+psycopg://passit:passit@localhost:55432/passit_test uv run --directory api pytest
```

Without PostgreSQL, the database tests are skipped locally. CI sets `PASSIT_REQUIRE_DB_TESTS=1`, so they fail instead.

| Test file | Covers |
| --- | --- |
| `test_contention.py` | 20 and 50 concurrent bookings for the same dates give exactly one 201; duplicate fee-release deliveries release once |
| `test_ledger.py` | Hypothesis property test over random action sequences: every event balances, the platform never pays out money it doesn't hold, and holds net to zero at the end |
| `test_booking_journey.py` | The full journey through HTTP: list, book, handover, return, settle or damage, release, review, dashboards |
| `test_catalogue.py` | Search filters, three-listing limit, location fallback, LLM output validation and heuristic fallback |
| `test_rules.py` | Pricing, inclusive date ranges, state-machine permissions |

### Contract

After changing routes or schemas:

```bash
uv run --directory api python -m scripts.export_openapi
npm run generate:api --prefix web
```

## What each stream has

**B1 Booking.** Instant booking guarded only by the `no_overlap` exclusion constraint, with no check-then-insert. The booking insert and the ledger hold share one transaction. Availability windows (`PUT/GET /listings/{id}/availability`) and the lifecycle `confirmed → handed_over → returned → settled`, plus `cancelled` before handover, are covered. Every lifecycle change takes a row lock, and handover and return require a checklist with at least one condition photo. Booking responses include `available_actions` for the viewer, so the frontend can mirror the state machine. Reviews are two-sided, once per booking per author.

**B2 Transactions.** Pure double-entry builders in `ledger.py` are persisted by `service.py`. `hold_funds(db, booking)` is the agreed Day 2 signature. Release is scheduled at handover, and the release handler (`release.py`) is idempotent under row locks. Cancelling reverses both holds. The damage tiers are minor 20%, moderate 40%, severe 70% and total 100%. `GET /dashboard` reports earnings and pending fees for lenders, and spending, deposits held and estimated savings for borrowers.

**B3 Catalogue.** Listings are created, updated, paused and archived. Search supports full text, category, MRT station, planning area, price range and free dates. Lenders get three free listings (`PASSIT_FREE_LISTING_LIMIT`). Media upload uses signed direct-upload URLs and is write-once. Location comes from OneMap geocoding to the nearest MRT station, cached, with a fallback to a chosen station. Price suggestions come from the LLM with validated JSON, are cached, and always fall back to a median-based heuristic. The seed script is `scripts/seed.py`.

Prototype simplifications to revisit:

- Damage tiers are applied directly by the lender because there is no admin role. The `disputed` state is reserved, and fee release already refuses to pay out while a booking is in it.
- Borrower "savings" treats the listing deposit as the item's replacement value.
- `app/catalogue/mrt_stations.py` is a curated subset of about 70 stations with approximate coordinates.

## Authentication

Accounts use an email and password, stored as argon2id hashes (`app/auth/passwords.py`).

| Endpoint | Purpose |
| --- | --- |
| `POST /auth/signup` | Create an account (`email`, `password` of 8 to 128 characters, `display_name`) and start a session. `409` if the email is taken, ignoring case. |
| `POST /auth/session` | Log in. The same `401` for a wrong password and an unknown email. |
| `DELETE /auth/session` | Log out (clears the cookie). |
| `GET /auth/me` | The signed-in user (`user_id`, `display_name`, private `email`, `bio`, `avatar_url`); `401` when signed out. |

A session is an HS256 JWT signed with `PASSIT_JWT_SECRET`, valid for 12 hours, delivered as the `passit_session` **httpOnly** cookie (`Secure` when `PASSIT_SESSION_COOKIE_SECURE=true`, which staging and demo set because CloudFront serves HTTPS). Domain routers only depend on `CurrentUser`, which also accepts `Authorization: Bearer <jwt>` for scripts and load tests. Outside `PASSIT_ENVIRONMENT=development` the API refuses to start with the default secret. Note the variable is `PASSIT_ENVIRONMENT`, not `PASSIT_ENV`.

Seed accounts sign in as `seed-01@passit.demo` to `seed-22@passit.demo` with password `passit-demo-2026`.

## AWS hand-off

Everything runs locally with no AWS account. Each AWS integration has a working local backend plus an AWS implementation, selected by environment variables. `boto3` is a dependency. Staging runs the S3 and EventBridge implementations; the status of each is listed below the table.

| Integration | Local (default) | AWS switch | Owner checklist |
| --- | --- | --- | --- |
| Media storage, `integrations/storage.py` | API stores uploads in `PASSIT_LOCAL_MEDIA_DIR` through a signed, expiring, write-once PUT | `PASSIT_STORAGE_BACKEND=s3`, `PASSIT_S3_BUCKET`, optional `PASSIT_CLOUDFRONT_DOMAIN` | Bucket with public access blocked and CORS allowing PUT from the web origin; task role with `s3:PutObject` and `s3:GetObject` on the prefix; switch evidence URLs to CloudFront signed URLs if CloudFront serves media |
| Fee release, `integrations/scheduler.py` | In-process sweep every `PASSIT_LOCAL_RELEASE_SWEEP_SECONDS`; `python -m scripts.release_due_fees` | `PASSIT_SCHEDULER_BACKEND=eventbridge`, `PASSIT_RELEASE_LAMBDA_ARN`, `PASSIT_SCHEDULER_ROLE_ARN` | Lambda with handler `app.transactions.lambda_handler.handler` and RDS access; Scheduler role with `lambda:InvokeFunction`; task role with `scheduler:CreateSchedule` and `iam:PassRole`. Keep the sweep on as a safety net |
| Price model, `integrations/llm.py` | Heuristic only | `PASSIT_BEDROCK_MODEL_ID` (IAM), or `PASSIT_LLM_API_URL` + `PASSIT_LLM_API_KEY` + `PASSIT_LLM_MODEL` for an OpenAI-compatible service | Enable the model in ap-southeast-1; task role with `bedrock:InvokeModel` |
| Photo thumbnails, `integrations/storage.py` + `infra/lambdas/thumbnailer` | None: cards show the original photo | A Lambda, triggered by S3 when a listing photo is uploaded, writes `thumbs/listing/<user>/<id>.jpg` (longest side 640 px, no metadata). Listings return `thumbnail_urls` beside `photo_urls`; the website uses them for cards and falls back to the original if one is missing. Handover and return photos are never thumbnailed. | Terraform module `thumbnailer`, CloudFront route `/thumbs/*`, and an image pushed by CI. `scripts/thumbnails/backfill.sh` covers photos uploaded earlier. |
| Email events, `integrations/notifications.py` + `infra/lambdas/mailer` | `PASSIT_NOTIFICATIONS_BACKEND=log`: one log line per event | `PASSIT_NOTIFICATIONS_BACKEND=sns` and `PASSIT_EVENTS_TOPIC_ARN` (Terraform sets both when `notifications_enabled` is true; off by default). Booking confirmed, handed over, returned, settled (with or without damage) and cancelled, and fee released, each go to the borrower and lender. | Terraform module `notifications`: SNS topic, mailer Lambda, SES identities. SES starts in sandbox mode, so each recipient must be verified once. The sender must be on a domain you control: a university or free-mail sender fails the receiver's DMARC check. Events are described in `app/notifications/events.py`. |
| Geocoding, `integrations/onemap.py` | Public OneMap search (rate-limited without a token) | `PASSIT_ONEMAP_TOKEN` | Register for a OneMap token so planning-area lookups work and rate limits are higher |

Set `PASSIT_FEE_HOLD_MINUTES=1` in staging so demos show a real release instead of a mocked one.

**Status on staging (checked end to end on 2026-10-24):**

- **Storage:** works. A presigned `PUT` (SigV4, regional endpoint, CORS limited to the CloudFront origin) stores the object and `/media/*` through CloudFront returns identical bytes; direct bucket access is denied. A presigned URL can be reused until it expires, so a second `PUT` overwrites. Bucket versioning keeps the earlier copy and the API attaches each key only once.
- **Fee release:** works. A one-off EventBridge schedule invokes `passit-staging-release`, which reaches RDS. The scheduler can deliver more than once (two runs 2 seconds apart were seen), and the handler is idempotent.
- **Bedrock:** not enabled. `PASSIT_BEDROCK_MODEL_ID` is unset, so price suggestions use the heuristic. The task role already allows `bedrock:InvokeModel`.
- **OneMap:** not exercised from AWS. Set `PASSIT_ONEMAP_TOKEN` for planning-area lookups.
- **Evidence URLs** are unsigned CloudFront URLs: anyone holding a media key can read the photo. See the TODO in `integrations/storage.py`.

## Prototype enrichment

Migration `0003` adds nullable profile bio/avatar fields, per-account saved listings and ordered listing photos. `PATCH /v1/auth/me` updates display name, bio and a user-owned avatar upload key; `GET /v1/users/{id}` exposes public identity and ratings without account email. Avatars use the existing upload API with stage `avatar` and JPEG/PNG files.

`GET/PUT/DELETE /v1/saved-listings` (PUT/DELETE use `/{listing_id}`) manage private bookmarks. Search accepts `owner_id` and `sort=newest|price_asc|price_desc`. Owners load archived listings through `GET /v1/listings/{id}/manage`; public listing reads continue to exclude archived items. Listing PATCH supports category/location and ordered `photo_keys`; listing media edits leave booking evidence untouched.
