// Platform evaluation: search load and elasticity spike. Public endpoint, no sign-in needed.
//
//   k6 run -e BASE_URL=https://<cloudfront> scripts/loadtest/search.js
//   k6 run -e BASE_URL=... -e PROFILE=spike scripts/loadtest/search.js
//
// PROFILE=ramp   10 -> MAX_VUS over RAMP_MIN minutes, then 1 minute of ramp-down (default 200 / 10).
// PROFILE=spike  20 VUs for 1 minute, jump to MAX_VUS in 30 s, hold for HOLD_MIN minutes (default 3).
import http from "k6/http";
import { check, sleep } from "k6";

const maxVus = Number(__ENV.MAX_VUS ?? 200);
const rampMin = Number(__ENV.RAMP_MIN ?? 10);
const holdMin = Number(__ENV.HOLD_MIN ?? 3);

const stages =
  (__ENV.PROFILE ?? "ramp") === "spike"
    ? [
        { duration: "1m", target: 20 },
        { duration: "30s", target: maxVus },
        { duration: `${holdMin}m`, target: maxVus },
        { duration: "30s", target: 0 },
      ]
    : [
        { duration: `${rampMin}m`, target: maxVus },
        { duration: "1m", target: 0 },
      ];

export const options = {
  stages: [{ duration: "10s", target: 10 }, ...stages],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

const queries = [
  "",
  "?q=tent",
  "?q=speaker",
  "?category=Outdoor",
  "?category=Events&max_price=30",
  "?mrt=Clementi",
  "?q=camera&min_price=5",
  "?from=2026-12-01&to=2026-12-05",
];

export default function () {
  const baseUrl = __ENV.BASE_URL;
  if (!baseUrl) throw new Error("BASE_URL is required");
  const query = queries[Math.floor(Math.random() * queries.length)];
  const response = http.get(`${baseUrl}/v1/listings${query}`, { tags: { name: "search" } });
  check(response, { "search is 200": (result) => result.status === 200 });
  sleep(Math.random() * 1.5 + 0.5);
}
