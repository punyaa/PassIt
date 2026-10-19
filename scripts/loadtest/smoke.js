import http from "k6/http";
import { check } from "k6";

export const options = { vus: 2, duration: "10s" };

export default function () {
  const baseUrl = __ENV.BASE_URL;
  if (!baseUrl) throw new Error("BASE_URL is required");
  const response = http.get(`${baseUrl}/health`);
  check(response, { "health is OK": (result) => result.status === 200 });
}
