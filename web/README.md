# PassIt Web

Next.js App Router frontend shared by two owners:

- **Front core:** design system, app shell, auth, search, listing creation and details, booking views, borrower dashboard.
- **F2 Front transaction:** handover, return, damage, lender dashboard and reviews.

Front core owns shared components under `components/`. F2 imports those components rather than duplicating them.

```bash
npm ci
npm run generate:api   # after any API contract change
npm run dev            # marketing: localhost:3000; application: app.localhost:3000
```

Native Next.js commands load the repository-root `.env`. The local template uses `/v1` for browser API requests and `PASSIT_API_ORIGIN=http://localhost:8000` for server-side forwarding. Compose forwards to `http://api:8000` instead.

## Marketing and application

One Next.js service serves both surfaces. `app/(marketing)` owns the landing page and public navigation. `app/(application)` owns rental screens, application navigation, and session state. Shared visual components stay in `components/`.

`NEXT_PUBLIC_APP_URL` sets the application origin. Locally it is `http://app.localhost:3000`; `web/proxy.ts` serves search at its root and redirects application paths from the marketing host while preserving queries. Marketing links and its search form point directly at the application. App links remain relative, so the logo and logout stay in the application.

Existing deployments remain single-host when `NEXT_PUBLIC_APP_URL` is unset. A production split requires the app hostname's DNS, HTTPS certificate, and edge routing before setting this build-time value. AWS continues to route `/v1` at the edge; `PASSIT_API_ORIGIN` is only needed when Next.js forwards API requests itself.

## Screens

- Marketing `/`: landing page with search, categories, and live listings.
- App `/` and `/search`: rental search, filters, availability dates, and paging.
- `/login`, `/signup`: email authentication, including seeded accounts.
- `/listings/new`, `/listings/[id]`: listing creation, photos, pricing, availability, and booking.
- `/bookings`, `/bookings/[id]`: renting/lending lists, booking actions, fee-release countdown, and ledger.
- `/dashboard/borrower`, `/dashboard/lender`: savings, earnings, deposits, listings, and pending actions.
- `/handover/[id]`, `/returns/[id]`, `/damage/[id]`: condition evidence, mutual confirmation, and damage settlement.
- `/reviews/new?booking=`: rating and comment, once per booking.

The booking page mirrors the API's state machine. It renders whatever `available_actions` the API returns for the viewer, instead of re-deriving permissions in the browser.

## Structure

- `components/ui.tsx`: design-system primitives (Button, Card, Field, Input, Badge, Alert, Stat…). Colours are Tailwind theme tokens defined in `app/globals.css` (`bg-forest`, `text-muted`, `border-line`…).
- `components/session.tsx`: `SessionProvider`, `useSession`, `RequireAuth`.
- `lib/api-client.ts`: `apiRequest`/`apiPost` with readable `ApiError` messages, using generated types via `Schemas`.
- `lib/use-api.ts`: a small fetch hook (`data`, `error`, `loading`, `reload`).
- `lib/uploads.ts`: presigned direct upload, used by listing photos and condition evidence.

## Sign-in during development

Email login and sign-up call `POST /auth/session` and `POST /auth/signup`, and sign-out calls `DELETE /auth/session`. This is the only sign-in flow, locally and on shared environments.

For seeded demo data (20 users, 40 listings, 15 bookings), run from the repository root:

```bash
docker compose exec api python -m scripts.seed --reset
```

Sign in with `seed-01@passit.demo` … `seed-20@passit.demo`, password `passit-demo-2026`.

## Local integration checks

With the Compose stack running and seeded, run `npm run test:surfaces --prefix web` from the repository root. These checks cover host routing, legacy redirects, same-origin authentication, and local media upload/download.

## Mocks

Set `NEXT_PUBLIC_API_MOCKS=true` to run against the MSW handlers in `mocks/` instead of the API, for frontend-only work. The service worker lives in `public/mockServiceWorker.js`.
