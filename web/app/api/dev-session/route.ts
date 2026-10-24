/**
 * Development sign-in: stores a session token (printed by `scripts.seed`) in the
 * httpOnly `passit_session` cookie that the API reads. The browser sends cookies by
 * host, not port, so the API on localhost:8000 receives a cookie set by :3000.
 *
 * POST /auth/session now sets the cookie itself, so this route only serves local seed tokens.
 * Keep it disabled in shared environments.
 */
import { NextResponse } from "next/server";

import { devLoginEnabled, SESSION_COOKIE } from "@/lib/dev-login";

export async function POST(request: Request) {
  if (!devLoginEnabled()) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  const body = (await request.json().catch(() => ({}))) as { token?: string };
  const token = body.token?.replace(/^Bearer\s+/i, "").trim();
  if (!token || token.split(".").length !== 3) {
    return NextResponse.json({ detail: "Paste the full session token." }, { status: 400 });
  }
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.PASSIT_SESSION_COOKIE_SECURE === "true",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
