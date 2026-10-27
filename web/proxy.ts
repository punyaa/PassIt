import { type NextRequest, NextResponse } from "next/server";

import { applicationOrigin } from "./lib/application-url";

export function proxy(request: NextRequest): NextResponse {
  if (!applicationOrigin) return NextResponse.next();

  const isApplication = request.headers.get("host") === new URL(applicationOrigin).host;

  if (isApplication) {
    if (request.nextUrl.pathname === "/") {
      const destination = request.nextUrl.clone();
      destination.pathname = "/home";
      return NextResponse.rewrite(destination);
    }
    return NextResponse.next();
  }

  if (request.nextUrl.pathname === "/") return NextResponse.next();

  const destination = new URL(applicationOrigin);
  destination.pathname = request.nextUrl.pathname;
  destination.search = request.nextUrl.search;
  return NextResponse.redirect(destination);
}

export const config = {
  matcher: ["/((?!_next/|v1/|.*\\..*).*)"],
};
