import { apiPost, type Schemas } from "./api-client";

export function logIn(email: string, password: string) {
  return apiPost<Schemas["SessionResponse"]>("/auth/session", { email, password });
}

/**
 * TODO(P1): the sign-up endpoint is not in the OpenAPI contract yet. This assumes
 * `POST /auth/users` that creates the user and sets the session cookie; rename it here
 * once P1 adds the real operation, then regenerate api-types.
 */
export function signUp(displayName: string, email: string, password: string) {
  return apiPost<Schemas["SessionResponse"]>("/auth/users", {
    display_name: displayName,
    email,
    password,
  });
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
