// Platform evaluation: booking load at a fixed arrival rate, every request on a distinct
// (listing, day) slot so it measures throughput, not contention. B1's contention.js covers
// the same-slot case.
//
//   k6 run -e BASE_URL=https://<cloudfront> scripts/loadtest/booking.js
//
// Needs the seeded demo data (22 users, 43 listings). RATE bookings/s for DURATION
// (default 20/s for 5m = 6,000 slots). Slots fall on START_OFFSET_DAYS and onward, one day per
// 40 bookings, so re-running needs a fresh seed or a different START_OFFSET_DAYS.
import http from "k6/http";
import exec from "k6/execution";
import { check } from "k6";
import { Counter } from "k6/metrics";

const created = new Counter("bookings_created");
const conflicts = new Counter("bookings_conflicted");
const rejected = new Counter("bookings_rejected");

// A 409 is a correct answer when a slot is taken (e.g. by seed data), not a failed request.
http.setResponseCallback(http.expectedStatuses(201, 409));

const rate = Number(__ENV.RATE ?? 20);
const offset = Number(__ENV.START_OFFSET_DAYS ?? 30);
const password = __ENV.DEMO_PASSWORD ?? "passit-demo-2026";

export const options = {
  scenarios: {
    bookings: {
      executor: "constant-arrival-rate",
      rate,
      timeUnit: "1s",
      duration: __ENV.DURATION ?? "5m",
      preAllocatedVUs: 50,
      maxVUs: 300,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
    bookings_rejected: ["count==0"],
  },
};

function isoDate(daysFromToday) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + daysFromToday);
  return date.toISOString().slice(0, 10);
}

// Sign the seed accounts in once; the session JWT is in the httpOnly cookie, which k6 can read.
export function setup() {
  const baseUrl = __ENV.BASE_URL;
  if (!baseUrl) throw new Error("BASE_URL is required");
  const users = [];
  for (let i = 1; i <= 20; i++) {
    const email = `seed-${String(i).padStart(2, "0")}@passit.demo`;
    const response = http.post(
      `${baseUrl}/v1/auth/session`,
      JSON.stringify({ email, password }),
      { headers: { "content-type": "application/json" } },
    );
    if (response.status !== 200) throw new Error(`login ${email} failed: ${response.status}`);
    users.push({ id: response.json("user_id"), token: response.cookies.passit_session[0].value });
  }
  const listings = http.get(`${baseUrl}/v1/listings?limit=50`).json();
  if (listings.length === 0) throw new Error("No listings: run the seed first");
  return { users, listings: listings.map((l) => ({ id: l.id, owner: l.owner_id })) };
}

export default function (data) {
  const index = exec.scenario.iterationInTest;
  const listing = data.listings[index % data.listings.length];
  const day = offset + Math.floor(index / data.listings.length);
  let borrower = data.users[index % data.users.length];
  if (borrower.id === listing.owner) borrower = data.users[(index + 1) % data.users.length];

  const response = http.post(
    `${__ENV.BASE_URL}/v1/bookings`,
    JSON.stringify({
      listing_id: listing.id,
      start_date: isoDate(day),
      end_date: isoDate(day),
      duration_type: "day",
    }),
    {
      headers: { authorization: `Bearer ${borrower.token}`, "content-type": "application/json" },
      tags: { name: "create_booking" },
    },
  );
  if (response.status === 201) created.add(1);
  else if (response.status === 409) conflicts.add(1);
  else rejected.add(1);
  check(response, { "booking created": (result) => result.status === 201 });
}
