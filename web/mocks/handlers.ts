import { http, HttpResponse } from "msw";

import type { components } from "@/lib/api-types";

type Listing = components["schemas"]["Listing"];
type Booking = components["schemas"]["Booking"];

const listing: Listing = {
  id: "11111111-1111-4111-8111-111111111111",
  owner_id: "33333333-3333-4333-8333-333333333333",
  title: "4-person camping tent",
  description: "Good 4-person camping tent, available for pickup near Clementi MRT.",
  category: "Outdoor",
  condition: "Good",
  price_day: "12.00",
  price_week: "50.00",
  price_month: "150.00",
  deposit: "80.00",
  mrt_station: "Clementi",
  planning_area: "Clementi",
  status: "active",
  photo_urls: [],
};

const booking: Booking = {
  id: "44444444-4444-4444-8444-444444444444",
  listing_id: listing.id,
  listing_title: listing.title,
  lender_id: listing.owner_id,
  borrower_id: "22222222-2222-4222-8222-222222222222",
  start_date: "2026-11-01",
  end_date: "2026-11-03",
  duration_type: "day",
  fee: "36.00",
  deposit: "80.00",
  state: "confirmed",
  created_at: "2026-10-24T08:00:00Z",
  handed_over_at: null,
  returned_at: null,
  fee_release_at: null,
  fee_released: false,
  settled_at: null,
  cancelled_at: null,
  damage_severity: null,
  viewer_role: "borrower",
  available_actions: ["handover", "cancel"],
};

export const handlers = [
  http.get("*/v1/listings", () => HttpResponse.json([listing])),
  http.get("*/v1/listings/:id", () =>
    HttpResponse.json({ ...listing, owner_display_name: "Lena Tan", owner_rating: 4.8, owner_review_count: 12 }),
  ),
  http.get("*/v1/bookings/:id", () => HttpResponse.json(booking)),
  http.post("*/v1/bookings", () => HttpResponse.json(booking, { status: 201 })),
  http.post("*/v1/auth/session", () =>
    HttpResponse.json({ user_id: "22222222-2222-4222-8222-222222222222", display_name: "Demo user" }),
  ),
];
