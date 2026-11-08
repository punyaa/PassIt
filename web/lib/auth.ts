import { apiPost, apiRequest, type Schemas } from "./api-client";

export function logIn(email: string, password: string) {
  return apiPost<Schemas["SessionResponse"]>("/auth/session", { email, password });
}

export type PlusPlan = "saver" | "eco-saver" | "mega-saver";

// Display labels by plan slug. Slugs are stable identifiers (URLs, API, DB); only labels rename.
export const PLUS_PLAN_NAMES: Record<PlusPlan, string> = {
  saver: "Eco Saver",
  "eco-saver": "Prime Saver",
  "mega-saver": "Mega Saver",
};

export function isPlusPlan(value: string | null): value is PlusPlan {
  return value === "saver" || value === "eco-saver" || value === "mega-saver";
}

export function signUp(displayName: string, email: string, password: string, plan?: PlusPlan) {
  return apiPost<Schemas["SessionResponse"]>("/auth/signup", {
    display_name: displayName,
    email,
    password,
    ...(plan ? { plan } : {}),
  });
}

/** Ends the API session (clears the httpOnly cookie, which only the API can do). */
export function logOut() {
  return apiRequest<void>("/auth/session", { method: "DELETE" });
}

/** Choose a Plus plan. Simulated: no charge, the new period starts immediately. */
export function setMyPlan(plan: PlusPlan) {
  return apiPost<Schemas["MembershipResponse"]>("/memberships/me", { plan });
}
