# PassIt Web

Next.js App Router frontend shared by two owners:

- **Front core:** design system, app shell, auth, search, listing creation and details, booking views, borrower dashboard.
- **F2 Front transaction:** handover, return, damage, lender dashboard and reviews.

Front core owns shared components under `components/`. F2 imports those components rather than duplicating them.

```bash
npm ci
npm run generate:api   # after any API contract change
npm run dev            # http://localhost:3000, expects the API at NEXT_PUBLIC_API_URL
```

## Screens

| Route | Owner | What it does |
| --- | --- | --- |
| `/` | Front core | Landing page with search, categories and live listings |
| `/login`, `/signup` | Front core | Auth forms; development sign-in with a seed token (see below) |
| `/search` | Front core | Filters (text, category, MRT, price, free dates) synced to the URL, paging; filters collapse on mobile |
| `/listings/new` | Front core | Listing form with photo upload, AI price suggestion, postal code or MRT, availability window |
| `/listings/[id]` | Front core | Details, lender rating and reviews, booking panel with live availability, price preview and conflict handling; owners can pause or reactivate |
| `/bookings`, `/bookings/[id]` | Front core | Renting and lending lists; booking page that shows the action for the current state, fee-release countdown, ledger |
| `/dashboard/borrower` | Front core | Savings, spending, deposits held, bookings needing action |
| `/handover/[id]`, `/returns/[id]` | F2 | Camera capture, condition checklist, mutual confirmation; return shows handover evidence alongside |
| `/damage/[id]` | F2 | Evidence comparison, fixed damage tiers with a live deposit split, outcome screen |
| `/dashboard/lender` | F2 | Earnings, pending release, listings and slots used, bookings needing action |
| `/reviews/new?booking=` | F2 | Star rating and comment, once per booking |

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

## Mocks

Set `NEXT_PUBLIC_API_MOCKS=true` to run against the MSW handlers in `mocks/` instead of the API, for frontend-only work. The service worker lives in `public/mockServiceWorker.js`.
