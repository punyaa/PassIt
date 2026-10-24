// B1 contention harness: N borrowers request the same dates at once.
// Prepare inputs with `uv run --directory api python -m scripts.contention_setup`.
// Pass: exactly one 201 and N-1 409s. Run 100 times for the Week 4 evaluation.
import http from "k6/http";
import { check } from "k6";
import { Counter } from "k6/metrics";

const created = new Counter("bookings_created");
const conflicts = new Counter("bookings_conflicted");
const tokens = (__ENV.TOKENS ?? "").split(",").filter(Boolean);

export const options = {
  scenarios: {
    contention: {
      executor: "per-vu-iterations",
      vus: tokens.length || 1,
      iterations: 1,
    },
  },
  thresholds: {
    bookings_created: ["count==1"],
    checks: ["rate==1"],
  },
};

function isoDate(daysFromToday) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + daysFromToday);
  return date.toISOString().slice(0, 10);
}

export default function () {
  const baseUrl = __ENV.BASE_URL;
  const listingId = __ENV.LISTING_ID;
  if (!baseUrl || !listingId || tokens.length === 0) {
    throw new Error("BASE_URL, LISTING_ID and comma-separated TOKENS are required");
  }
  // Each run picks fresh dates so repeated runs against one listing stay independent.
  const offset = Number(__ENV.START_OFFSET_DAYS ?? 30);

  const response = http.post(
    `${baseUrl}/v1/bookings`,
    JSON.stringify({
      listing_id: listingId,
      start_date: isoDate(offset),
      end_date: isoDate(offset + 6),
      duration_type: "week",
    }),
    {
      headers: {
        authorization: `Bearer ${tokens[__VU - 1]}`,
        "content-type": "application/json",
      },
    },
  );
  if (response.status === 201) created.add(1);
  if (response.status === 409) conflicts.add(1);
  check(response, { "created or conflict": (result) => [201, 409].includes(result.status) });
}
