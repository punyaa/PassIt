import http from "k6/http";
import { check } from "k6";

export const options = { vus: 50, iterations: 50 };

export default function () {
  const baseUrl = __ENV.BASE_URL;
  const listingId = __ENV.LISTING_ID;
  const tokens = (__ENV.TOKENS ?? "").split(",");
  if (!baseUrl || !listingId || tokens.length < 50) {
    throw new Error("BASE_URL, LISTING_ID and 50 comma-separated TOKENS are required");
  }

  const response = http.post(
    `${baseUrl}/v1/bookings`,
    JSON.stringify({
      listing_id: listingId,
      start_date: "2026-11-01",
      end_date: "2026-11-07",
      duration_type: "week",
    }),
    {
      headers: {
        authorization: `Bearer ${tokens[__VU - 1]}`,
        "content-type": "application/json",
      },
    },
  );
  check(response, { "created or conflict": (result) => [201, 409].includes(result.status) });
}
