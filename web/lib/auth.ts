import { apiPost, apiRequest, type Schemas } from "./api-client";

export function logIn(email: string, password: string) {
  return apiPost<Schemas["SessionResponse"]>("/auth/session", { email, password });
}

export function signUp(displayName: string, email: string, password: string) {
  return apiPost<Schemas["SessionResponse"]>("/auth/signup", {
    display_name: displayName,
    email,
    password,
  });
}

/** Ends the API session (clears the httpOnly cookie, which only the API can do). */
export function logOut() {
  return apiRequest<void>("/auth/session", { method: "DELETE" });
}

export async function devSignIn(token: string): Promise<void> {
  const response = await fetch("/api/dev-session", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Could not start a session with that token.");
  }
}
