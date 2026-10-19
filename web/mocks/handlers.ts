import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("*/v1/listings", () =>
    HttpResponse.json([
      {
        id: "11111111-1111-4111-8111-111111111111",
        title: "4-person camping tent",
        category: "Outdoor & travel",
        condition: "Good",
        price_day: "12.00",
        price_week: "50.00",
        price_month: "150.00",
        deposit: "80.00",
        mrt_station: "Clementi",
        planning_area: "Clementi",
      },
    ]),
  ),
  http.post("*/v1/auth/session", () =>
    HttpResponse.json({ user_id: "22222222-2222-4222-8222-222222222222", display_name: "Demo user" }),
  ),
];
