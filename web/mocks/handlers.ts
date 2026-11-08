import { http, HttpResponse } from "msw";

import type { components } from "@/lib/api-types";

type Schemas = components["schemas"];
type Listing = Schemas["Listing"];
type Booking = Schemas["Booking"];

const listing: Listing = {
  id: "11111111-1111-4111-8111-111111111111",
  owner_id: "33333333-3333-4333-8333-333333333333",
  title: "4-person camping tent",
  description:
    "Good 4-person camping tent, available for pickup near Clementi MRT.",
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
  thumbnail_urls: [],
};
const user: Schemas["CurrentUserResponse"] = {
  user_id: listing.owner_id,
  display_name: "Lena Tan",
  email: "lena@example.test",
  plan: "saver",
  bio: null,
  avatar_url: null,
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
  viewer_role: "lender",
  available_actions: ["handover", "cancel"],
};
let signedIn = false;
let photoKeys: string[] = [];
let windows: Schemas["DateWindow"][] = [
  { start_date: "2026-01-01", end_date: "2027-12-31" },
];
const saved = new Set<string>();
const borrower = { id: booking.borrower_id, name: "Ben Lim" };
let meetups: Schemas["Meetup"][] = [];
function meetupEvent(
  author: { id: string; name: string },
  kind: Schemas["MeetupEvent"]["kind"],
  terms?: Schemas["MeetupTerms"],
  message?: string | null,
): Schemas["MeetupEvent"] {
  return {
    id: crypto.randomUUID(),
    author_id: author.id,
    author_display_name: author.name,
    kind,
    meet_at: terms?.meet_at ?? null,
    location: terms?.location ?? null,
    price: terms ? Number(terms.price).toFixed(2) : null,
    message: message ?? terms?.message ?? null,
    created_at: new Date().toISOString(),
  };
}
/** The mock user owns the only listing, so they always act as the lender. */
function updateMeetup(
  id: string,
  change: (meetup: Schemas["Meetup"]) => void,
): Schemas["Meetup"] | undefined {
  const meetup = meetups.find((m) => m.id === id);
  if (meetup) {
    change(meetup);
    meetup.updated_at = new Date().toISOString();
    const pending = meetup.status === "pending";
    const myTurn = pending && meetup.proposed_by !== user.user_id;
    meetup.awaiting_role = pending ? (myTurn ? "lender" : "borrower") : null;
    meetup.available_actions = myTurn
      ? ["accept", "counter", "decline"]
      : pending || meetup.status === "accepted"
        ? ["cancel"]
        : [];
  }
  return meetup;
}
const uploads = new Map<string, string>();
const unauthorized = () =>
  HttpResponse.json({ detail: "Sign in required" }, { status: 401 });
const detail = (): Schemas["ListingDetail"] => ({
  ...listing,
  photo_keys: photoKeys,
  owner_display_name: user.display_name,
  owner_rating: null,
  owner_review_count: 0,
});

export const handlers = [
  http.get("*/v1/auth/me", () =>
    signedIn ? HttpResponse.json(user) : unauthorized(),
  ),
  http.post("*/v1/auth/session", () => {
    signedIn = true;
    return HttpResponse.json({
      user_id: user.user_id,
      display_name: user.display_name,
    });
  }),
  http.delete("*/v1/auth/session", () => {
    signedIn = false;
    return new HttpResponse(null, { status: 204 });
  }),
  http.patch("*/v1/auth/me", async ({ request }) => {
    if (!signedIn) return unauthorized();
    const body = (await request.json()) as Schemas["ProfileUpdate"];
    user.display_name = body.display_name;
    user.bio = body.bio ?? null;
    if (body.avatar_key !== undefined)
      user.avatar_url = body.avatar_key
        ? (uploads.get(body.avatar_key) ?? null)
        : null;
    return HttpResponse.json(user);
  }),
  http.get("*/v1/auth/me/deletion", () => {
    if (!signedIn) return unauthorized();
    const preview: Schemas["AccountDeletionPreview"] = {
      allowed: true,
      open_rentals: 0,
      listings_deleted: 0,
      listings_archived: 1,
    };
    return HttpResponse.json(preview);
  }),
  http.post("*/v1/auth/me/delete", () => {
    if (!signedIn) return unauthorized();
    signedIn = false;
    return new HttpResponse(null, { status: 204 });
  }),
  http.get("*/v1/users/:id", ({ params }) =>
    HttpResponse.json({
      user_id: String(params.id),
      display_name: user.display_name,
      bio: user.bio,
      avatar_url: user.avatar_url,
      member_since: "2026-10-01T00:00:00Z",
      rating: null,
      review_count: 0,
    } satisfies Schemas["PublicProfile"]),
  ),
  http.get("*/v1/reviews", () => HttpResponse.json([])),
  http.get("*/v1/saved-listings", () =>
    signedIn
      ? HttpResponse.json(saved.has(listing.id) ? [listing] : [])
      : unauthorized(),
  ),
  http.put("*/v1/saved-listings/:id", ({ params }) => {
    if (!signedIn) return unauthorized();
    saved.add(String(params.id));
    return new HttpResponse(null, { status: 204 });
  }),
  http.delete("*/v1/saved-listings/:id", ({ params }) => {
    if (!signedIn) return unauthorized();
    saved.delete(String(params.id));
    return new HttpResponse(null, { status: 204 });
  }),
  http.get("*/v1/listings/mine", () =>
    signedIn ? HttpResponse.json([listing]) : unauthorized(),
  ),
  http.get("*/v1/listings/mrt-stations", () =>
    HttpResponse.json([
      { name: "Clementi", planning_area: "Clementi" },
      { name: "Bugis", planning_area: "Downtown Core" },
    ]),
  ),
  http.get("*/v1/listings", ({ request }) => {
    const owner = new URL(request.url).searchParams.get("owner_id");
    return HttpResponse.json(
      listing.status === "active" && (!owner || owner === listing.owner_id)
        ? [listing]
        : [],
    );
  }),
  http.get("*/v1/listings/:id/manage", () =>
    signedIn ? HttpResponse.json(detail()) : unauthorized(),
  ),
  http.get("*/v1/listings/:id/availability", () =>
    HttpResponse.json({
      listing_id: listing.id,
      from_date: windows[0].start_date,
      to_date: windows.at(-1)!.end_date,
      available: true,
      windows,
      booked: [],
    }),
  ),
  http.put("*/v1/listings/:id/availability", async ({ request }) => {
    if (!signedIn) return unauthorized();
    windows = ((await request.json()) as Schemas["AvailabilityUpdate"]).windows;
    return HttpResponse.json({
      listing_id: listing.id,
      from_date: windows[0].start_date,
      to_date: windows.at(-1)!.end_date,
      available: true,
      windows,
      booked: [],
    });
  }),
  http.patch("*/v1/listings/:id", async ({ request }) => {
    if (!signedIn) return unauthorized();
    const body = (await request.json()) as Schemas["ListingUpdate"];
    const { photo_keys, postal_code, mrt_station, ...fields } = body;
    Object.assign(listing, fields);
    if (mrt_station) listing.mrt_station = mrt_station;
    if (photo_keys) {
      photoKeys = photo_keys;
      listing.photo_urls = photoKeys.map((key) => uploads.get(key) ?? "");
    }
    void postal_code;
    return HttpResponse.json(detail());
  }),
  http.get("*/v1/listings/:id", () => HttpResponse.json(detail())),
  http.post("*/v1/media/presign", async ({ request }) => {
    const { stage } = (await request.json()) as Schemas["PresignRequest"];
    const key = `media/${stage}/${user.user_id}/${crypto.randomUUID()}.png`;
    return HttpResponse.json({
      key,
      upload_url: `/v1/mock-upload?key=${encodeURIComponent(key)}`,
      expires_in_seconds: 900,
      headers: { "content-type": "image/png" },
    });
  }),
  http.put("*/v1/mock-upload", async ({ request }) => {
    const key = new URL(request.url).searchParams.get("key")!;
    uploads.set(key, URL.createObjectURL(await request.blob()));
    return new HttpResponse(null, { status: 200 });
  }),
  http.get("*/v1/bookings", () =>
    signedIn ? HttpResponse.json([booking]) : unauthorized(),
  ),
  http.get("*/v1/bookings/:id", () => HttpResponse.json(booking)),
  http.post("*/v1/bookings", async ({ request }) => {
    const body = (await request.json()) as { payment_method_token?: string };
    const failures: Record<string, { code: string; message: string; retryable: boolean }> = {
      pm_mock_declined: { code: "card_declined", message: "The mock payment was declined.", retryable: false },
      pm_mock_insufficient_funds: {
        code: "insufficient_funds",
        message: "The mock payment method has insufficient funds.",
        retryable: false,
      },
      pm_mock_expired: {
        code: "expired_payment_method",
        message: "The mock payment method has expired.",
        retryable: false,
      },
      pm_mock_processing_error: {
        code: "processing_error",
        message: "The mock gateway had a temporary processing error. Please retry.",
        retryable: true,
      },
    };
    const failure = body.payment_method_token && failures[body.payment_method_token];
    if (failure) return HttpResponse.json({ detail: failure }, { status: 402 });
    return HttpResponse.json(booking, { status: 201 });
  }),
  http.get("*/v1/meetups", () =>
    signedIn ? HttpResponse.json(meetups) : unauthorized(),
  ),
  http.post("*/v1/meetups", async ({ request }) => {
    if (!signedIn) return unauthorized();
    // Mock mode has one account, so a proposal arrives as if from a borrower.
    const terms = (await request.json()) as Schemas["MeetupCreate"];
    const now = new Date().toISOString();
    const meetup: Schemas["Meetup"] = {
      id: crypto.randomUUID(),
      listing_id: listing.id,
      listing_title: listing.title,
      borrower_id: borrower.id,
      borrower_display_name: borrower.name,
      lender_id: user.user_id,
      lender_display_name: user.display_name,
      status: "pending",
      meet_at: terms.meet_at,
      location: terms.location,
      price: Number(terms.price).toFixed(2),
      proposed_by: borrower.id,
      awaiting_role: "lender",
      viewer_role: "lender",
      available_actions: ["accept", "counter", "decline"],
      events: [meetupEvent(borrower, "propose", terms)],
      created_at: now,
      updated_at: now,
    };
    meetups = [meetup, ...meetups];
    return HttpResponse.json(meetup, { status: 201 });
  }),
  http.post("*/v1/meetups/:id/counter", async ({ params, request }) => {
    if (!signedIn) return unauthorized();
    const terms = (await request.json()) as Schemas["MeetupTerms"];
    const me = { id: user.user_id, name: user.display_name };
    const meetup = updateMeetup(String(params.id), (m) => {
      Object.assign(m, {
        meet_at: terms.meet_at,
        location: terms.location,
        price: Number(terms.price).toFixed(2),
        proposed_by: me.id,
      });
      m.events.push(meetupEvent(me, "counter", terms));
    });
    return HttpResponse.json(meetup);
  }),
  http.post("*/v1/meetups/:id/:action", async ({ params, request }) => {
    if (!signedIn) return unauthorized();
    const action = params.action as "accept" | "decline" | "cancel";
    const note = (await request.json().catch(() => null)) as
      Schemas["MeetupNote"] | null;
    const status = {
      accept: "accepted",
      decline: "declined",
      cancel: "cancelled",
    }[action] as Schemas["Meetup"]["status"];
    const meetup = updateMeetup(String(params.id), (m) => {
      m.status = status;
      m.events.push(
        meetupEvent(
          { id: user.user_id, name: user.display_name },
          action,
          undefined,
          note?.message,
        ),
      );
    });
    return HttpResponse.json(meetup);
  }),
];
